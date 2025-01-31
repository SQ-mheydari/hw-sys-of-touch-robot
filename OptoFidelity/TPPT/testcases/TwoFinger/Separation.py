from math import radians, cos, sin

from TPPTcommon.Node import *
from TPPTcommon.grid import create_separation, parse_angles
from TPPTcommon.visualization import GridVisContainer
from MeasurementDB import *
from TPPTcommon.script_config import get_continuous_measurement_timeout
# Logging module is needed if script wants to send logging
# information to the debug window.
import logging
import time
import os

logger = logging.getLogger(__name__)

# Database table name for the test case.
DB_TEST_TABLE_NAME = 'separation_test'

# Database table name for the test results.
DB_RESULTS_TABLE_NAME = 'separation_results'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TEST_TABLE_NAME, 'test_id'], [DB_RESULTS_TABLE_NAME, 'point_id']]


class SeparationTest(Base):
    # Separation test parameters are defined here
    __tablename__ = DB_TEST_TABLE_NAME

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False)
    test = relation(TestItem, backref=backref(DB_TEST_TABLE_NAME, order_by=id))

    # Is measurement 2-, 3-, 4-, or 5-finger
    number_of_fingers = Column(Integer)

    robot_x = Column(Float)
    robot_y = Column(Float)
    robot_z = Column(Float)
    separation_distance = Column(Float)
    separation_angle = Column(Float)
    first_finger_offset = Column(Float)
    tool_separation = Column(Float)
    finger1_diameter = Column(Float)
    finger2_diameter = Column(Float)

class SeparationResults( Base ):

    # Separation results are defined here
    __tablename__ = DB_RESULTS_TABLE_NAME

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey(DB_TEST_TABLE_NAME + '.id', ondelete='CASCADE'), nullable=False )
    point = relation( SeparationTest, backref = backref(DB_RESULTS_TABLE_NAME, order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )


class Separation(TestStep):
    """
    In separation test robot taps DUT surface at a regular grid of points and touch event for each tap is recorded.
    Robot uses two-finger tool where each finger has specific tip attached.
    Finger separation used during tap is specified.
    """

    def __init__(self, context):
        super().__init__('Separation')

        self.context = context

        self.loop_tips = False

        # Tips for the two fingers are defined in test properties.
        tip_names = [node.name for node in context.tips_node.children]

        if tip_names:
            self.controls.tip1 = tip_names[0]
            self.controls.info['tip1'] = {'label': 'Finger 1 tip', 'items': tip_names,
                                          'tooltip': self.context.tooltips['Tip 1']}

            self.controls.tip2 = tip_names[0]
            self.controls.info['tip2'] = {'label': 'Finger 2 tip', 'items': tip_names,
                                          'tooltip': self.context.tooltips['Tip 2']}

        # It is possible that separation test is loaded with robot that doesn't support it (e.g. 3axis simulator).
        try:
            separation_limits = self.context.robot.finger_separation_limits()
        except:
            separation_limits = [10.0, 140.0]
            self.context.html_warning("Could not fetch separation limits from robot, using values {}"
                                      .format(str(separation_limits)))

        # Default separation is maximum robot's minimum separation and 10 mm which is the typical tip hull diameter.
        self.controls.start_separation = max(separation_limits[0], 10.0)
        self.controls.info['start_separation'] = {'label': 'Starting finger separation [mm]'}

        self.controls.number_of_steps = 13
        self.controls.info['number_of_steps'] = {'label': 'Number of separation steps'}

        self.controls.step_size = 1.0
        self.controls.info['step_size'] = {'label': 'Separation step size [mm]'}

        self.controls.azimuth_angles = "0, -90, diagonal"
        self.controls.info['azimuth_angles '] = {'label': 'Azimuth angles [deg]'}

    def execute(self):
        """
        The 'execute' method contains the actual work that the
        test step is doing.
        """

        # Main sequence contains common resources and state.
        dut = self.context.get_active_dut()
        robot = self.context.robot

        if self.controls.tip1 == self.controls.tip2:
            raise Exception("Tip for primary and secondary finger cannot be same!")

        # Change tips to both fingers.
        self.context.html("Changing tip %s to axial finger and tip %s to separated finger" % (self.controls.tip1, self.controls.tip2))

        self.context.indicators.set_status("Changing two-finger tips to %s and %s" % (self.controls.tip1, self.controls.tip2))

        robot.change_tip(self.controls.tip1, 0)
        robot.change_tip(self.controls.tip2, 1)

        # Get tip client objects.
        tip1 = self.context.tips_node.get_child(self.controls.tip1).tnt_tip
        tip2 = self.context.tips_node.get_child(self.controls.tip2).tnt_tip

        tip1_diameter = tip1.diameter
        tip2_diameter = tip2.diameter
        sum_of_radii = tip1_diameter / 2.0 + tip2_diameter / 2.0

        self.context.indicators.set_tip_name(self.controls.tip1 + ", " + self.controls.tip2)

        base_distance = dut.base_distance

        self.context.html("Running Separation test for DUT: %s" % (dut))
        self.context.indicators.set_status("Executing two-finger separation test")

        # Create database entry for the test case.
        test_item = self.context.create_db_test_item("Separation Test")

        # Get grid of points to tap.
        measurement_points = self.create_grid(dut, sum_of_radii)

        # Move over first tap location. This might be far away from current location.
        # This makes sure that measurement timeout appropriately describes the tap gesture.
        point = measurement_points[0]
        dut.move(point.x, point.y, base_distance, azimuth=point.angle)

        for index, point in enumerate(measurement_points):
            point_number = index + 1

            # Update indicators in GUI.
            self.context.indicators.set_test_details([
                ('Point', str(point_number) + ' / ' + str(len(measurement_points))),
                ('Finger gap size', str(point.finger_distance - sum_of_radii)),
                ('Finger axial separation', str(point.finger_distance)),
                ('Angle', str(point.angle))
            ])

            # Create database entry for the events to be measured.
            point_id = self.create_point_id(point, test_item, tip1_diameter, tip2_diameter)

            # Start capturing a continuous stream of touch events.
            continuous_measurement = self.context.create_continuous_measurement(None)
            continuous_measurement.point = point
            continuous_measurement.start(timeout=get_continuous_measurement_timeout())

            # Draw expected points to the UI.
            self.context.add_dut_point(point.x, point.y, True, True)
            separated_x, separated_y = self.calculate_expected_point(point)
            self.context.add_dut_point(separated_x, separated_y, True, True)

            # Perform tap gesture.
            dut.tap(point.x, point.y, clearance=-1, azimuth=point.angle, separation=point.finger_distance,
                    tool_name="both", kinematic_name="tool1")

            # End tap measurement.
            continuous_measurement.end()

            # Parse touch event data.
            touchlist = continuous_measurement.parse_data()

            # Save results to database.
            self.save_measurement_data(point_id, touchlist)

            # Check if test should pause or stop.
            self.context.breakpoint()

        test_item.finger_type = self.controls.tip1 + ", " + self.controls.tip2
        self.context.close_db_test_item(test_item)

    def create_grid(self, dut, min_separation):
        """
        Create grid of points that define the geometry of the test case.
        :param dut: DUT where the grid is evaluated on.
        :param min_separation: Minimum separation to use.
        """

        angles = parse_angles(self.controls.azimuth_angles, dut)

        if len(angles) == 0:
            raise Exception("At least one angle must be specified for separation test.")

        if self.controls.start_separation < min_separation:
            logger.warning("Start separation {} is smaller than smallest possible separation {}. "
                           "Using the smallest separation".format(self.controls.start_separation, min_separation))

        # Start separation is limited by min_separation which is determined by the diameters of attached tips.
        start_separation = max(min_separation, self.controls.start_separation)

        points = create_separation(dut, start_separation, self.controls.number_of_steps, self.controls.step_size, angles)

        separation_limits = self.context.robot.finger_separation_limits()

        # Validate separations.
        for point in points:
            if point.finger_distance < separation_limits[0]:
                raise Exception("Separation {} is less than robot minimum separation {}."
                                .format(point.finger_distance, separation_limits[0]))
            elif point.finger_distance > separation_limits[1]:
                raise Exception("Separation {} is greater than robot maximum separation {}."
                                .format(point.finger_distance, separation_limits[1]))

        return points

    def visualize_grid(self, dut):
        """
        Construct a visualization of the test case grid.
        :param dut: DUT where the grid is evaluated on.
        """

        tip1 = self.context.tips_node.get_child(self.controls.tip1).tnt_tip
        tip2 = self.context.tips_node.get_child(self.controls.tip2).tnt_tip

        tip1_diameter = tip1.diameter
        tip2_diameter = tip2.diameter

        return GridVisContainer(self.__class__.__name__, (dut.width, dut.height), self.create_grid(dut, tip1_diameter / 2.0 + tip2_diameter / 2.0), dut.name)

    def create_point_id(self, point, test_item, finger1_diameter, finger2_diameter):

        separation_test = SeparationTest()

        separation_test.number_of_fingers = point.fingers
        separation_test.separation_distance = point.finger_distance - finger1_diameter / 2 - finger2_diameter / 2
        separation_test.separation_angle = point.angle
        separation_test.first_finger_offset = point.first_finger_offset
        separation_test.tool_separation = point.finger_distance
        separation_test.finger1_diameter = finger1_diameter
        separation_test.finger2_diameter = finger2_diameter
        separation_test.robot_x = point.x
        separation_test.robot_y = point.y
        separation_test.test_id = test_item.id

        self.context.db.add(separation_test)

        return separation_test.id

    def save_measurement_data(self, point_id, touchlist):
        """
        Save stationary jitter measurement to database.
        """
        dblist = []
        for testresult in touchlist:
            test_results = SeparationResults()
            test_results.panel_x = float(testresult[0])
            test_results.panel_y = float(testresult[1])
            test_results.sensitivity = float(testresult[2])
            test_results.finger_id = int(testresult[3])
            test_results.delay = testresult[4]
            test_results.time = testresult[5]
            test_results.event = testresult[6]
            test_results.point_id = point_id
            dblist.append(test_results)

            self.context.add_dut_point(float(testresult[0]), float(testresult[1]), True, False)

        self.context.db.addAll(dblist)

    def calculate_expected_point(self, point):
        """
        Calculates expected points for touches made by separated finger.
        :param point: current measured point.
        :return: Expected x and y coordinate for separated finger.
        """
        expected_x = point.x + (point.finger_distance * cos(-radians(point.angle)))
        expected_y = point.y + (point.finger_distance * sin(-radians(point.angle)))
        return expected_x, expected_y

