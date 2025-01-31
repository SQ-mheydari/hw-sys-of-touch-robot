import datetime
from math import radians, cos, sin

from TPPTcommon.Node import *
from TPPTcommon.grid import create_multifinger_swipe, parse_numbers
from TPPTcommon.visualization import GridVisContainer
from TPPTcommon.script_config import *
from MeasurementDB import *
# Logging module is needed if script wants to send logging
# information to the debug window.
import logging
import time
import os

logger = logging.getLogger(__name__)

# Database table name for the test case.
DB_TEST_TABLE_NAME = 'multi_finger_swipe_test'

# Database table name for the test results.
DB_RESULTS_TABLE_NAME = 'multi_finger_swipe_results'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TEST_TABLE_NAME, 'test_id'], [DB_RESULTS_TABLE_NAME, 'swipe_id']]


class MultifingerSwipeTest(Base):
    # Multifinger swipe results are defined here
    __tablename__ = DB_TEST_TABLE_NAME

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey('test_item.id'), nullable=False)
    test = relation(TestItem, backref=backref(DB_TEST_TABLE_NAME, order_by=id))

    # Is measurement 2-, 3-, 4-, or 5-finger
    number_of_fingers = Column(Integer)

    # For straight lines, start and stop positions are defined
    start_x = Column(Float)
    start_y = Column(Float)
    end_x = Column(Float)
    end_y = Column(Float)
    separation_distance = Column(Float)
    separation_angle = Column(Float)
    first_finger_offset = Column(Float)

    # Is test zoom, pinch or swipe
    test_type = Column(String)


class MultifingerSwipeResults(Base):
    # Multifinger swipe results are defined here
    __tablename__ = DB_RESULTS_TABLE_NAME

    id = Column(Integer, primary_key=True)
    swipe_id = Column(Integer, ForeignKey(DB_TEST_TABLE_NAME + '.id', ondelete='CASCADE'), nullable=False)
    swipe = relation(MultifingerSwipeTest, backref=backref(DB_RESULTS_TABLE_NAME, order_by=id))

    panel_x = Column(Float)
    panel_y = Column(Float)
    sensitivity = Column(Float)
    delay = Column(Float)
    finger_id = Column(Integer)
    time = Column(Float)
    event = Column(Integer)


class MultiFingerSwipe(TestStep):
    """
    In multi finger swipe test robot swipes DUT surface over a regular grid of lines and touch event for each line is recorded.
    A multifinger is attached to two-finger tool during this test.
    """

    def __init__(self, context):
        super().__init__('MultiFinger Swipe')

        self.context = context

        self.loop_tips = False

        self.controls.swipe_radius = 6.0
        self.controls.info['swipe_radius'] = {'label': 'Swipe radius [mm]', 'min': get_min_swipe_radius(),
                                              'max': get_max_swipe_radius(),
                                              'tooltip': self.context.tooltips['Swipe radius']}

        self.controls.clearance = -0.5
        self.controls.info['clearance'] = {'label': 'Clearance [mm]', 'min': get_min_swipe_clearance(),
                                           'max': get_max_swipe_clearance(),
                                           'tooltip': self.context.tooltips['Clearance']}

    def execute(self):
        """
        The 'execute' method contains the actual work that the
        test step is doing.
        """

        # Main sequence contains common resources and state.
        dut = self.context.get_active_dut()
        robot = self.context.robot

        speeds = parse_numbers(self.context.settings_node.controls.line_drawing_speed)
        base_distance = dut.base_distance
        clearance = float(self.controls.clearance)
        swipe_radius = float(self.controls.swipe_radius)

        # Sanity checks for swipe parameters.
        check_swipe_parameters(clearance, swipe_radius)

        for speed in speeds:
            self.context.html("Running MultiFinger Swipe test for DUT: %s, drawing speed: %s" % (dut, speed))

            # Create database entry for the test case.
            swipe_test_item = self.context.create_db_test_item("MultiFinger Swipe Test", speed=speed)

            # Collect tip names that were used during the test.
            used_tips = ""

            # Loop through enabled tips.
            for tip_node in self.context.tips_node.children:
                if not tip_node.enabled:
                    continue

                tip = tip_node.tnt_tip

                if not tip.is_multifinger:
                    continue

                used_tips += tip_node.name + ", "

                self.context.indicators.set_status("Changing tip to " + tip_node.name)
                self.context.indicators.set_tip_name(tip_node.name)

                self.context.tips_node.set_active_tip(tip_node)

                self.context.indicators.set_tip_name(tip_node.name)

                self.context.indicators.set_status("Executing multifinger swipe test")

                self.context.set_robot_dut_change_speed()
                dut.jump(0.0, 0.0, dut.base_distance)

                self.context.set_robot_default_speed()
                self.context.clear_dut_points()

                # Get grid of lines to swipe.
                measurement_lines = self.create_grid(dut, tip.num_tips, tip.tip_distance)

                for index, line in enumerate(measurement_lines):
                    # Update indicators in GUI.
                    self.context.indicators.set_test_detail('Swipe', str(index) + ' / ' + str(len(measurement_lines)))

                    line_id = self.create_line_id(line, swipe_test_item)

                    # Jump with default speed over the start point of the line to swipe.
                    self.context.set_robot_default_speed()
                    dut.jump(line.start_x, line.start_y, base_distance, base_distance)

                    # Swipe with specific speed.
                    self.context.set_robot_speed(speed)

                    # Get expected lines and draw them to UI
                    expected_lines = self.calculate_expected_lines(line)
                    for el in expected_lines:
                        # Lines are only drawn to the UI at this point. Writing is done later
                        self.context.draw_dut_expected_line(el[0], el[1], el[2], el[3])

                    # The azimuth needs to be rotated before starting the measurement to avoid
                    # timeout issues.
                    dut.move(line.start_x, line.start_y, base_distance, azimuth=line.angle)

                    # Start capturing a continuous stream of touch events.
                    continuous_measurement = self.context.create_continuous_measurement(line)
                    continuous_measurement.start(timeout=get_continuous_measurement_timeout())

                    # Perform swipe gesture.
                    dut.swipe(line.start_x, line.start_y, line.end_x, line.end_y, clearance=clearance, radius=swipe_radius,
                              azimuth1=line.angle, azimuth2=line.angle)

                    # End measuring touch events.
                    continuous_measurement.end()

                    # Parse touch event data.
                    touchlist = continuous_measurement.parse_data()

                    # Save results to database.
                    self.save_measurement_data(line_id, touchlist)

                    # Check if test should pause or stop.
                    self.context.breakpoint()

            if used_tips != "":
                swipe_test_item.finger_type = used_tips[:-2]  # Remove ", "?
            else:
                swipe_test_item.finger_type = used_tips

            self.context.close_db_test_item(swipe_test_item)

    def create_grid(self, dut, num_tips, tip_distance):
        """
        Create grid of points that define the geometry of the test case.
        :param dut: DUT where the grid is evaluated on.
        """

        return create_multifinger_swipe(dut, num_tips, tip_distance)

    def visualize_grid(self, dut):
        """
        Construct a visualization of the test case grid.
        :param dut: DUT where the grid is evaluated on.
        """

        grids = []

        # Loop through enabled tips.
        for tip_node in self.context.tips_node.children:
            if not tip_node.enabled:
                continue

            tip = tip_node.tnt_tip

            if not tip.is_multifinger:
                continue

            grids += self.create_grid(dut, tip.num_tips, tip.tip_distance)

        return GridVisContainer(self.__class__.__name__, (dut.width, dut.height), grids, dut.name)

    def create_line_id(self, line, test_item):

        test = MultifingerSwipeTest()

        test.start_x = line.start_x
        test.start_y = line.start_y
        test.end_x = line.end_x
        test.end_y = line.end_y
        test.test_id = test_item.id
        test.number_of_fingers = line.fingers
        test.separation_distance = line.finger_distance
        test.separation_angle = line.angle
        test.first_finger_offset = line.first_finger_offset

        self.context.db.add(test)

        return test.id

    def save_measurement_data(self, line_id, touchlist):
        """
        Save swipe test measurement to database.
        """

        dblist = []


        for testresult in touchlist:
            results = MultifingerSwipeResults()
            results.panel_x = float(testresult[0])
            results.panel_y = float(testresult[1])
            results.sensitivity = float(testresult[2])
            results.finger_id = int(testresult[3])
            results.delay = testresult[4]
            results.time = testresult[5]
            results.event = testresult[6]
            results.swipe_id = line_id

            dblist.append(results)

            # Add measured touch points for the swipes.
            self.context.add_dut_point(float(testresult[0]), float(testresult[1]), False, False)

        self.context.db.addAll(dblist)

    def calculate_expected_lines(self, line):
        """
        Calculates expected points for multifinger swipe test.
        :param line: line of which expected start and end will be calculated
        :return: a list that contains list which contains the points.
        """

        expected_line_list = []

        # Go through all fingers and calculate star and end points
        finger = 0
        while finger < line.fingers:
            # Calculate start and end point for the line
            start_x = line.start_x + ((finger * line.finger_distance) * cos(-radians(line.angle)))
            start_y = line.start_y + ((finger * line.finger_distance) * sin(-radians(line.angle)))
            end_x = line.end_x + ((finger * line.finger_distance) * cos(-radians(line.angle)))
            end_y = line.end_y + ((finger * line.finger_distance) * sin(-radians(line.angle)))
            expected_line_list.append([start_x, start_y, end_x, end_y])
            finger += 1

        return expected_line_list


