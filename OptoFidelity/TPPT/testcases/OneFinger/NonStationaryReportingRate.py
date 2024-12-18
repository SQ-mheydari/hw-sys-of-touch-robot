from TPPTcommon.Node import *
from TPPTcommon.grid import create_non_stationary_reporting_rate_lines, parse_numbers
from TPPTcommon.visualization import GridVisContainer
from MeasurementDB import *
from TPPTcommon.script_config import *
# Logging module is needed if script wants to send logging
# information to the debug window.
import logging

logger = logging.getLogger(__name__)

# Database table name for the test case.
DB_TEST_TABLE_NAME = 'one_finger_non_stationary_reporting_rate_test'

# Database table name for the test results.
DB_RESULTS_TABLE_NAME = 'one_finger_non_stationary_reporting_rate_results'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TEST_TABLE_NAME, 'test_id'], [DB_RESULTS_TABLE_NAME, 'swipe_id']]


class OneFingerNonStationaryReportingRateTest(Base):
    # One Finger Non Stationary Reporting Rate Test is defined here
    __tablename__ = DB_TEST_TABLE_NAME

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False)
    test = relation(TestItem, backref=backref(DB_TEST_TABLE_NAME, order_by=id))

    # For straight lines, start and stop positions are defined
    start_x = Column(Float)
    start_y = Column(Float)
    end_x = Column(Float)
    end_y = Column(Float)


class OneFingerNonStationaryReportingRateResults(Base):
    # One Finger Non Stationary Reporting Rate results are defined here
    __tablename__ = DB_RESULTS_TABLE_NAME

    id = Column(Integer, primary_key=True)
    swipe_id = Column(Integer, ForeignKey(DB_TEST_TABLE_NAME + '.id', ondelete='CASCADE'), nullable=False)
    swipe = relation(OneFingerNonStationaryReportingRateTest, backref=backref(DB_RESULTS_TABLE_NAME, order_by=id))

    panel_x = Column(Float)
    panel_y = Column(Float)
    sensitivity = Column(Float)
    delay = Column(Float)
    finger_id = Column(Integer)
    time = Column(Float)
    event = Column(Integer)


class NonStationaryReportingRate(TestStep):
    """
    In non-stationary reporting rate DUT is swiped along a few prescribed lines
    and touch data is collected. Touch event timestamps are used in analysis to calculate reporting rate.
    """

    def __init__(self, context):
        """
        The 'init' method mainly defines the test case controls for GUI and is executed when script is loaded.
        """

        super().__init__('Non-Stationary Reporting Rate')

        self.context = context

        self.controls.swipe_type = 'swipe'
        self.controls.info['swipe_type'] = {'label': 'Swipe type', 'items': {'swipe', 'drag'},
                                            'tooltip': self.context.tooltips['Swipe type']}

        self.controls.edge_offset = 0.0
        self.controls.info['edge_offset'] = {'label': 'Edge offset [mm]', "validate": (
            '(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
            'tooltip': self.context.tooltips['Edge offset']}

        self.controls.swipe_radius = 6.0
        self.controls.info['swipe_radius'] = {'label': 'Swipe radius [mm]', 'min': get_min_swipe_radius(),
                                              'max': get_max_swipe_radius(),
                                              'tooltip': self.context.tooltips['Swipe radius']}

        self.controls.clearance = -0.1
        self.controls.info['clearance'] = {'label': 'Clearance [mm]', 'min': get_min_swipe_clearance(),
                                           'max': get_max_swipe_clearance(),
                                            'tooltip': self.context.tooltips['Clearance']}

    def execute(self):
        """
        The 'execute' method contains the actual work that the
        test step is doing.
        """

        dut = self.context.get_active_dut()
        tip = self.context.get_active_tip()

        speeds = parse_numbers(self.context.settings_node.controls.line_drawing_speed)
        base_distance = dut.base_distance
        clearance = float(self.controls.clearance)
        swipe_radius = float(self.controls.swipe_radius)

        # Sanity checks for swipe parameters.
        check_swipe_parameters(clearance, swipe_radius)

        for speed in speeds:
            self.context.html("Running One Finger Non Stationary Reporting Rate test for dut: %s, "
                              "tip: %s, drawing speed: %s" % (dut, tip, speed))
            test_item = self.context.create_db_test_item("One Finger Non Stationary Reporting Rate Test", speed=speed)

            # Create lines to swipe.
            measurement_lines = self.create_grid(dut)

            settings = self.context.settings_node.controls

            for index, line in enumerate(measurement_lines):
                # Update indicators in GUI.
                self.context.indicators.set_test_detail('Line', str(index + 1) + ' / ' + str(len(measurement_lines)))

                # Create database entry for line.
                line_id = self.create_line_id(line, test_item)

                # Jump with default speed to line start point.
                self.context.set_robot_default_speed()
                dut.jump(line.start_x, line.start_y, base_distance, base_distance)

                # Use specific speed to swipe.
                self.context.set_robot_speed(speed)

                # Start measuring DUT events.
                # Timeout is used to stop event stream after swipe is complete and tip is off DUT surface.
                continuous_measurement = self.context.create_continuous_measurement(line)
                continuous_measurement.start(timeout=get_continuous_measurement_timeout())

                # Draw expected line to UI
                self.context.draw_dut_expected_line(line.start_x, line.start_y, line.end_x, line.end_y)

                if get_config_value('enable_force') and settings.force_application == 'Force gesture':
                    dut.drag_force(line.start_x, line.start_y, line.end_x, line.end_y, force=settings.default_force)
                else:
                    # Perform swipe or drag gesture based on user preference
                    if self.controls.swipe_type == 'drag':
                        dut.drag(line.start_x, line.start_y, line.end_x, line.end_y, clearance=clearance)
                    else:  # normal swipe
                        dut.swipe(line.start_x, line.start_y, line.end_x, line.end_y, clearance=clearance, radius=swipe_radius)

                # End measurement.
                continuous_measurement.end()

                # Parse measured data and save to database.
                touchlist = continuous_measurement.parse_data()
                self.save_measurement_data(line_id, touchlist)

                # self.check_reporting_rates(reporting_rate_results)

                # Check if test should pause or stop.
                self.context.breakpoint()

            self.context.close_db_test_item(test_item)

    def create_grid(self, dut):
        """
        Create grid of lines that define the geometry of the test case.
        :param dut: DUT where the grid is evaluated on.
        """

        return create_non_stationary_reporting_rate_lines(dut, self.controls.edge_offset)

    def visualize_grid(self, dut):
        """
        Construct a visualization of the test case grid.
        :param dut: DUT where the grid is evaluated on.
        """

        return GridVisContainer("Non stationary reporting rate", (dut.width, dut.height), self.create_grid(dut),
                                dut.name)

    def create_line_id(self, line, test_item):

        non_stationary_reporting_rate_test = OneFingerNonStationaryReportingRateTest()

        non_stationary_reporting_rate_test.start_x = line.start_x
        non_stationary_reporting_rate_test.start_y = line.start_y
        non_stationary_reporting_rate_test.end_x = line.end_x
        non_stationary_reporting_rate_test.end_y = line.end_y
        non_stationary_reporting_rate_test.test_id = test_item.id
        self.context.db.add(non_stationary_reporting_rate_test)

        return non_stationary_reporting_rate_test.id

    def save_measurement_data(self, line_id, touchlist):
        """
        Save non-stationary reporting rate measurement to database.
        """

        dblist = []
        for testresult in touchlist:
            test_results_nsrr = OneFingerNonStationaryReportingRateResults()

            test_results_nsrr.panel_x = float(testresult[0])
            test_results_nsrr.panel_y = float(testresult[1])
            test_results_nsrr.sensitivity = float(testresult[2])
            test_results_nsrr.finger_id = int(testresult[3])
            test_results_nsrr.delay = testresult[4]
            test_results_nsrr.time = testresult[5]
            test_results_nsrr.event = testresult[6]
            test_results_nsrr.swipe_id = line_id
            dblist.append(test_results_nsrr)

            self.context.add_dut_point(float(testresult[0]), float(testresult[1]), False, False)

        self.context.db.addAll(dblist)

    def check_reporting_rates(self, reporting_rate_results):
        min_reporting_rate = 0.0
        previous_timestamp = 0.0
        max_delay = 0.0
        min_delay = 0.0

        for result in reporting_rate_results[1:]:
            delay = float(result[5]) - previous_timestamp
            if delay != 0.0:
                if delay >= max_delay and previous_timestamp != 0.0:
                    max_delay = delay
                if min_delay == 0.0 or delay < min_delay:
                    min_delay = delay
                previous_timestamp = result[5]
        try:
            min_reporting_rate = round(1.0 / (max_delay / 1000.0), 2)
            max_reporting_rate = round(1.0 / (min_delay / 1000.0), 2)
            color = "red"
            if min_reporting_rate >= 100.0:
                color = "green"
            self.context.html_color("Minimum reporting rate: " + str(min_reporting_rate) + " Hz", color)
            self.context.html_color("Maximum reporting rate: " + str(max_reporting_rate) + " Hz", color)
        except Exception as e:
            self.context.html("Not enough data for analysis " + str(e))


