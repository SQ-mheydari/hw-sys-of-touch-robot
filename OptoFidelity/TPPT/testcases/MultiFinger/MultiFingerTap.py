from math import cos, radians, sin

from TPPTcommon.Node import *
from TPPTcommon.grid import create_multifinger_tap
from TPPTcommon.visualization import GridVisContainer
from MeasurementDB import *
from TPPTcommon.script_config import get_tap_measurement_timeout
# Logging module is needed if script wants to send logging
# information to the debug window.
import logging
import time
import os

logger = logging.getLogger(__name__)

# Database table name for the test case.
DB_TEST_TABLE_NAME = 'multi_finger_tap_test'

# Database table name for the test results.
DB_RESULTS_TABLE_NAME = 'multi_finger_tap_results'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TEST_TABLE_NAME, 'test_id'], [DB_RESULTS_TABLE_NAME, 'point_id']]


class MultifingerTapTest(Base):
    # Multifinger tap results are defined here
    __tablename__ = DB_TEST_TABLE_NAME

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey('test_item.id'), nullable=False)
    test = relation(TestItem, backref=backref(DB_TEST_TABLE_NAME, order_by=id))

    # Is measurement 2-, 3-, 4-, or 5-finger
    number_of_fingers = Column(Integer)

    robot_x = Column(Float)
    robot_y = Column(Float)
    robot_z = Column(Float)
    separation_distance = Column(Float)
    separation_angle = Column(Float)
    first_finger_offset = Column(Float)


class MultifingerTapResults(Base):
    # Multifinger Tap results are defined here
    __tablename__ = DB_RESULTS_TABLE_NAME

    id = Column(Integer, primary_key=True)
    point_id = Column(Integer, ForeignKey(DB_TEST_TABLE_NAME + '.id', ondelete='CASCADE'), nullable=False)
    point = relation(MultifingerTapTest, backref=backref(DB_RESULTS_TABLE_NAME, order_by=id))

    panel_x = Column(Float)
    panel_y = Column(Float)
    sensitivity = Column(Float)
    delay = Column(Float)
    finger_id = Column(Integer)
    time = Column(Float)
    event = Column(Integer)


class MultiFingerTap(TestStep):
    """
    In multi finger tap test robot taps DUT surface at a regular grid of points and touch event for each tap is recorded.
    A multifinger is attached to two-finger tool during this test.
    """

    def __init__(self, context):
        super().__init__('MultiFinger Tap')

        self.context = context

        self.loop_tips = False

    def execute(self):
        """
        The 'execute' method contains the actual work that the
        test step is doing.
        """

        # Main sequence contains common resources and state.
        dut = self.context.get_active_dut()
        robot = self.context.robot

        base_distance = dut.base_distance

        self.context.html("Running MultiFinger Tap test for DUT: %s" % (dut))

        # Create database entry for the test case.
        tap_test_item = self.context.create_db_test_item("MultiFinger Tap Test")

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

            self.context.indicators.set_status("Executing multifinger tap test")

            self.context.set_robot_dut_change_speed()
            dut.jump(0.0, 0.0, dut.base_distance)

            self.context.set_robot_default_speed()
            self.context.clear_dut_points()

            # Get grid of points to tap.
            measurement_points = self.create_grid(dut, tip.num_tips, tip.tip_distance)

            for index, point in enumerate(measurement_points):
                point_number = index + 1

                # Update indicators in GUI.
                self.context.indicators.set_test_detail('Point',
                                                        str(point_number) + ' / ' + str(len(measurement_points)))

                point_id = self.create_point_id(point, tap_test_item)

                # Move over tap location. This might be far away from current location.
                # This makes sure that measurement timeout appropriately describes the tap gesture.
                dut.move(point.x, point.y, base_distance, azimuth=point.angle)

                # Draw expected points to ui
                expected_points = self.calculate_expected_points(point)
                for ep in expected_points:
                    self.context.add_dut_point(ep[0], ep[1], True, True)

                # Start capturing a continuous stream of touch events.
                continuous_measurement = self.context.create_continuous_measurement(None)
                continuous_measurement.point = point
                continuous_measurement.start(timeout=get_tap_measurement_timeout())

                # Perform tap gesture.
                dut.tap(point.x, point.y, clearance=-1, azimuth=point.angle)

                # End measuring touch events.
                continuous_measurement.end()

                # Parse touch event data.
                touchlist = continuous_measurement.parse_data()

                # Save results to database.
                self.save_measurement_data(point_id, touchlist, expected_points)

                # Check if test should pause or stop.
                self.context.breakpoint()

        if used_tips != "":
            tap_test_item.finger_type = used_tips[:-2]  # Remove ", "?
        else:
            tap_test_item.finger_type = used_tips

        self.context.close_db_test_item(tap_test_item)

    def create_grid(self, dut, num_tips, tip_distance):
        """
        Create grid of points that define the geometry of the test case.
        :param dut: DUT where the grid is evaluated on.
        """

        return create_multifinger_tap(dut, num_tips, tip_distance)

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

    def create_point_id(self, point, test_item):

        test = MultifingerTapTest()

        test.number_of_fingers = point.fingers
        test.separation_distance = point.finger_distance
        test.separation_angle = point.angle
        test.first_finger_offset = point.first_finger_offset
        test.robot_x = point.x
        test.robot_y = point.y
        test.test_id = test_item.id

        self.context.db.add(test)

        return test.id

    def save_measurement_data(self, point_id, touchlist, expected_points):
        """
        Save tap test measurement to database.
        """

        dblist = []

        for index, testresult in enumerate(touchlist):
            results = MultifingerTapResults()
            # Write expected point to UI

            # Write expected points only for existing fingers
            if index < len(expected_points):
                # Points are already drawn to the UI no need to draw them again.
                self.context.add_dut_point(expected_points[index][0], expected_points[index][1], True, True)

            results.panel_x = float(testresult[0])
            results.panel_y = float(testresult[1])
            results.sensitivity = float(testresult[2])
            results.finger_id = int(testresult[3])
            results.delay = testresult[4]
            results.time = testresult[5]
            results.event = testresult[6]
            results.point_id = point_id

            dblist.append(results)
            self.context.add_dut_point(float(testresult[0]), float(testresult[1]), True, False)

        self.context.db.addAll(dblist)

    def calculate_expected_points(self, point):
        """
        Calculates expected points for multifinger tap.
        :param point: Current point that is being tapped (by first tip).
        :return: A list of expected point coordinates.
        """

        expected_point_list = []

        # If there seems to be more fingers than defined (this can happen at least with dummy). Id for fingers that
        # should be there is < point.finger (number of fingers defined for the current multifinger tool). Fingers in
        # with id that is greater or equal to point.finger are extra fingers and expected points are not calculated for
        # those.
        finger = 0
        while finger < point.fingers:
            expected_x = point.x + ((finger * point.finger_distance) * cos(-radians(point.angle)))
            expected_y = point.y + ((finger * point.finger_distance) * sin(-radians(point.angle)))
            expected_point_list.append((expected_x, expected_y))
            finger = finger + 1

        return expected_point_list
