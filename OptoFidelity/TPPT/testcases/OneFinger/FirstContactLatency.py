from TPPTcommon.Measurement.Dummy import LatencyMeasurement as DummyLatencyMeasurement
from TPPTcommon.Node import *
from TPPTcommon.grid import create_random_points, add_grid_file_controls, GRID_FILE_DIR, create_grid_from_file
from TPPTcommon.visualization import GridVisContainer
from TPPTcommon.script_config import get_config_value, get_tap_measurement_timeout
import numpy
from MeasurementDB import *
# Logging module is needed if script wants to send logging
# information to the debug window.
import logging
import os

logger = logging.getLogger(__name__)

try:
    from TPPTcommon.Measurement.PIT import LatencyMeasurement
except ImportError:
    logger.warning("PIT driver not installed as required by First contact latency test.")

# Database table name for the test case.
DB_TABLE_NAME = 'one_finger_first_contact_latency_test'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TABLE_NAME, 'test_id']]


class OneFingerFirstContactLatencyTest(Base):
    # One-finger latency test is defined here

    __tablename__ = DB_TABLE_NAME

    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False)
    test = relation(TestItem, backref=backref(DB_TABLE_NAME, order_by=id))

    # One-finger Latency test results
    powerstate = Column(Integer)
    system_latency = Column(Float)
    delay = Column(Float)
    time = Column(Float)
    robot_x = Column(Float)
    robot_y = Column(Float)
    robot_z = Column(Float)


class FirstContactLatency(TestStep):
    """
    First contact latency taps DUT surface and measures latency from first physical contact
    to the reported touch event. Uses PIT to get accurate touch timing.
    """

    def __init__(self, context):
        """
        The 'init' method mainly defines the test case controls for GUI and is executed when script is loaded.
        """

        super().__init__('First Contact Latency')

        self.context = context

        self.controls.clearance = -0.1
        self.controls.info['clearance'] = {'label': 'Clearance [mm]', 'min': -2.0, 'max': 10.0,
                                           'tooltip': self.context.tooltips['Clearance']}

        add_grid_file_controls(self)

        self.controls.AmountOfPoints = 5
        self.controls.info['AmountOfPoints'] = {'label': 'Amount of points per test', "min": 1,
                                                'visibility_control': 'usegridfile',
                                                'visibility_value': False,
                                                'tooltip': self.context.tooltips['Amount of points']}

        self.controls.edge_offset = 0.0
        self.controls.info['edge_offset'] = {'label': 'Edge offset [mm]', "validate": (
            '(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                                             'visibility_control': 'usegridfile',
                                             'visibility_value': False,
            'tooltip': self.context.tooltips['Edge offset']}

        if get_config_value("enable_pit_system_latency_calibration"):
            self.controls.calibrateSystemLatency = False
            self.controls.info['calibrateSystemLatency'] = {'label': 'Calibrate system latency',
                                                            'tooltip': self.context.tooltips['Calibrate system latency']}

    def execute(self):
        """
        The 'execute' method contains the actual work that the
        test step is doing.
        """

        dut = self.context.get_active_dut()
        tip = self.context.get_active_tip()

        base_distance = dut.base_distance

        # PIT or Dummy driver is required for this test case.
        active_dut_driver = self.context.get_active_dut_driver()
        if active_dut_driver != "PIT" and active_dut_driver != "Dummy":
            self.context.html_error("One Finger First Contact Latency Test can only be executed with PIT or with "
                                    "simulator")
            return

        pit = self.context.duts_node.active_driver_object.pit

        system_latency = 0.0
        power_states = {"Active": 1, "Idle": 2}

        self.context.html("Running One First Contact Latency Test for dut:{}, tip:{}".format(dut, tip))

        test_item = self.context.create_db_test_item("One Finger First Contact Latency Test")
        point_number = 1
        measurement_points = self.create_grid(dut)

        clearance = float(self.controls.clearance)

        if get_config_value("enable_pit_system_latency_calibration"):
            if self.controls.calibrateSystemLatency:
                """System delay needs to be calibrated because otherwise delay values are too big"""
                calibrationtarget = self.context.tnt.dut("OF_PIT_LATENCY")
                calibrationtarget.jump(0.2, 0.2, base_distance)
                system_latencies = []

                for tap_count in range(10):
                    pit.SingleTrigger()
                    calibrationtarget.watchdog_tap(0.2, 0.2, clearance=clearance, trigger_direction="TOUCH_START")
                    timestamps = pit.ReturnTimestamps()
                    self.context.html(timestamps)
                    # System latency is timestamp of the finger trigger minus electrical pulse
                    system_latencies.append((timestamps[0] - timestamps[1]))
                    self.context.breakpoint()

                system_latency = round(numpy.median(system_latencies), 2)
                self.context.html("System latency median: " + str(system_latency) + " ms")
                pit.NormalTrigger()

        dut.jump(0.0, 0.0, base_distance)

        for point in measurement_points:
            for power_state in power_states:
                dut.jump(point.x, point.y, base_distance, base_distance)
                pit.WriteSleepMode(power_states[power_state])
                pit.SingleTrigger()

                """Tap each measurement point and store results to database"""
                self.context.indicators.set_test_details(
                    [('Power state', power_state),
                     ('Point', str(point_number) + ' / ' + str(len(measurement_points)))])

                # LatencyMeasurement object is created and that's PIT specific just like First Contact Latency test
                # so it's handled here instead of LoopContext.
                if active_dut_driver == "Dummy":
                    latency_measurement = DummyLatencyMeasurement(self.context.indicators, point,
                                                                  self.context.duts_node.active_driver_object)
                    # Trigger direction is not given in simulator.
                    trigger_direction = None
                elif active_dut_driver == "PIT":
                    latency_measurement = LatencyMeasurement(self.context.indicators, point,
                                                             self.context.duts_node.active_driver_object)
                    trigger_direction = "TOUCH_START"

                # Draw expected point to UI.
                self.context.add_dut_point(point.x, point.y, True, True)

                latency_measurement.start(timeout=get_tap_measurement_timeout())
                dut.watchdog_tap(point.x, point.y, clearance=clearance, trigger_direction=trigger_direction)
                latency_measurement.end()

                self.save_measurement_data(latency_measurement.results, point, test_item, power_states[power_state],
                                           system_latency)

                # Check if test should pause or stop.
                self.context.breakpoint()

            point_number += 1

        pit.NormalTrigger()
        pit.WriteSleepMode(power_states["Active"])
        self.context.close_db_test_item(test_item)

    def create_grid(self, dut):
        """
        Create grid of points that define the geometry of the test case.
        :param dut: DUT where the grid is evaluated on.
        """

        if self.controls.usegridfile:
            grid_file_path = os.path.join(GRID_FILE_DIR, self.controls.gridfile)

            return create_grid_from_file(dut, grid_file_path, self.controls.gridunit)
        else:
            return create_random_points(dut, self.controls.AmountOfPoints, self.controls.edge_offset)

    def visualize_grid(self, dut):
        """
        Construct a visualization of the test case grid.
        :param dut: DUT where the grid is evaluated on.
        """

        return GridVisContainer(self.__class__.__name__, (dut.width, dut.height), self.create_grid(dut), dut.name)

    def save_measurement_data(self, measured_point_data, robot_point, tap_test_item, power_state,
                              system_latency):
        """
        Save first contact latency measurement to database.
        """

        test_result = OneFingerFirstContactLatencyTest()

        test_result.test_id = tap_test_item.id
        test_result.robot_x = robot_point.x
        test_result.robot_y = robot_point.y
        test_result.robot_z = 0.0  # meas_point[2]
        test_result.powerstate = power_state
        test_result.system_latency = system_latency

        if len(measured_point_data) > 0:
            p2p_data = measured_point_data[0]

            # PIT1 had delay and touch time in ReturnTimestamp value (ReturnP2PArray has also touch time):
            #   test_result.delay = timestamps[1]
            #   test_result.time = timestamps[0]  # p2p_data[5]

            # PIT2 has delay and touch time in ReturnP2PArray
            test_result.delay = p2p_data[4]  # trigger timestamp
            test_result.time = p2p_data[5]  # touch timestamp

            test_result.panel_x = p2p_data[0]
            test_result.panel_y = p2p_data[1]

            self.context.add_dut_point(p2p_data[0], p2p_data[1], True, False)

        self.context.db.add(test_result)
