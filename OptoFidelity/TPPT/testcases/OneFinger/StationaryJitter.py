from TPPTcommon.Node import *
from TPPTcommon.grid import *
from MeasurementDB import *
from TPPTcommon.script_config import get_continuous_measurement_timeout, get_config_value
from TPPTcommon.visualization import GridVisContainer
# Logging module is needed if script wants to send logging
# information to the debug window.
import logging
import time
import os
logger = logging.getLogger(__name__)

# Database table name for the test case.
DB_TEST_TABLE_NAME = 'one_finger_stationary_jitter_test'

# Database table name for the test results.
DB_RESULTS_TABLE_NAME = 'one_finger_stationary_jitter_results'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TEST_TABLE_NAME, 'test_id'], [DB_RESULTS_TABLE_NAME, 'point_id']]

class OneFingerStationaryJitterTest(Base):

    #One Finger Non Stationary Reporting Rate Test is defined here
    __tablename__ = DB_TEST_TABLE_NAME

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref(DB_TEST_TABLE_NAME, order_by = id) )

    #For straight lines, start and stop positions are defined
    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_azimuth = Column( Float )
    robot_tilt = Column( Float )


class OneFingerStationaryJitterResults(Base):

    #One Finger Non Stationary Reporting Rate results are defined here
    __tablename__ = DB_RESULTS_TABLE_NAME

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey(DB_TEST_TABLE_NAME + '.id', ondelete='CASCADE'), nullable=False )
    point = relation( OneFingerStationaryJitterTest, backref = backref(DB_RESULTS_TABLE_NAME, order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column( Float )
    panel_tilt = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class StationaryJitter(TestStep):
    """
    In stationary jitter test robot touches DUT surface for a moment while a stream of touch events is collected.
    In analysis it is inspected how much the reported locations vary.
    """

    def __init__(self, context):
        """
        The 'init' method mainly defines the test case controls for GUI and is executed when script is loaded.
        """

        super().__init__('Stationary Jitter')

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

        if get_config_value("tilt_angles"):
            self.controls.tilt_angles = "0, 30, 60"
            self.controls.info["tilt_angles"] = {"label": "Tilt angles [°]",
                                                 "tooltip": self.context.tooltips["Tilt angles"]}

        if get_config_value("azimuth_angles"):
            self.controls.azimuth_angles = "-45, 0, 45"
            self.controls.info["azimuth_angles"] = {"label": "Azimuth angles [°]",
                                                    "tooltip": self.context.tooltips["Azimuth angles"]}

    def execute(self):
        """
        The 'execute' method contains the actual work that the
        test step is doing.
        """

        dut = self.context.get_active_dut()
        tip = self.context.get_active_tip()

        base_distance = dut.base_distance

        self.context.html("Running One Finger Stationary Jitter test for dut:%s, tip:%s"%(dut, tip))

        # Create database entry for the test case.
        test_item = self.context.create_db_test_item("One Finger Stationary Jitter")

        measurement_points = self.create_grid(dut)

        settings = self.context.settings_node.controls

        clearance = float(self.controls.clearance)

        for index, point in enumerate(measurement_points):
            # Update indicators in GUI.
            self.context.indicators.set_test_detail('Point', str(index + 1) + ' / ' +str(len(measurement_points)))

            # Create database entry for the point to be measured.
            point_id = self.create_point_id(point, test_item)

            # Move over the point.
            dut.move(x=point.x, y=point.y, z=base_distance, tilt=point.tilt, azimuth=point.azimuth)

            # Start continuous measurement to obtain a stream of touch events.
            # Timeout is used to stop event stream after robot has moved off the surface.
            continuous_measurement = self.context.create_continuous_measurement(None)
            continuous_measurement.point = point
            continuous_measurement.start(timeout=get_continuous_measurement_timeout())

            if get_config_value('enable_force') and settings.force_application == 'Force gesture':
                # Press DUT surface with force.
                dut.press(x=point.x, y=point.y, force=settings.default_force, tilt=point.tilt, azimuth=point.azimuth,
                          duration=1.0)

                # Draw expected point to UI
                self.context.add_dut_point(point.x, point.y, True, True)

                # End measurement.
                continuous_measurement.end()

                # Collect all touches. Note: this contains touches also from press start and end.
                touchlist = continuous_measurement.parse_data()
            else:
                # Move to touch the DUT surface.
                dut.move(x=point.x, y=point.y, z=clearance, tilt=point.tilt, azimuth=point.azimuth)

                # Store touchlist length so that we know the event from the moment the move gesture ended.
                touchlist_len = len(continuous_measurement.parse_data())

                # Sleep for a while to get a good stream of touch values.
                time.sleep(1.0)

                # Get measurement data before moving off DUT to avoid getting garbage data from lift-off.
                touchlist = continuous_measurement.parse_data()

                # Draw expected point to UI
                self.context.add_dut_point(point.x, point.y, True, True)

                # Move off DUT surface to end jitter data collection.
                dut.move(x=point.x, y=point.y, z=base_distance, tilt=point.tilt, azimuth=point.azimuth)

                # End measurement.
                continuous_measurement.end()

                # Get touch events. touchlist_len divides the events into two sets:
                # 1) Events from the duration of move gesture and 2) events during contact with no robot movement.
                # Take the last event from set 1 and all events from set 2.
                # This is because some devices have practically no jitter so that set 2 is most often empty.
                # We want to have at least one event in touchlist to indicate that there was no error in the measurement.
                if touchlist_len > 0:
                    touchlist = touchlist[touchlist_len - 1:]

            # Save results to database.
            self.save_measurement_data(point_id, touchlist)

            # Check if test should pause or stop.
            self.context.breakpoint()

        self.context.close_db_test_item(test_item)

    def create_grid(self, dut):
        """
        Create grid of points that define the geometry of the test case.
        :param dut: DUT where the grid is evaluated on.
        """

        if self.controls.usegridfile:
            grid_file_path = os.path.join(GRID_FILE_DIR, self.controls.gridfile)

            grid = create_grid_from_file(dut, grid_file_path, self.controls.gridunit)
        else:
            grid = create_random_points(dut, self.controls.AmountOfPoints, self.controls.edge_offset)

        azimuth_angles = [0.0]

        if hasattr(self.controls, "azimuth_angles"):
            azimuth_angles = parse_numbers(self.controls.azimuth_angles)

        tilt_angles = [0.0]

        if hasattr(self.controls, "tilt_angles"):
            tilt_angles = parse_numbers(self.controls.tilt_angles)

        return augment_grid_orientation(grid, azimuth_angles, tilt_angles)

    def visualize_grid(self, dut):
        """
        Construct a visualization of the test case grid.
        :param dut: DUT where the grid is evaluated on.
        """

        return GridVisContainer(self.__class__.__name__, (dut.width, dut.height), self.create_grid(dut), dut.name)

    def create_point_id(self, point, test_item):

        stationary_jitter_test = OneFingerStationaryJitterTest()

        stationary_jitter_test.robot_x = point.x
        stationary_jitter_test.robot_y = point.y
        stationary_jitter_test.robot_azimuth = point.azimuth if hasattr(self.controls, "azimuth_angles") else None
        stationary_jitter_test.robot_tilt = point.tilt if hasattr(self.controls, "tilt_angles") else None
        stationary_jitter_test.test_id = test_item.id
        self.context.db.add(stationary_jitter_test)

        return stationary_jitter_test.id

    def save_measurement_data(self, point_id, touchlist):
        """
        Save stationary jitter measurement to database.
        """
        dblist = []

        for testresult in touchlist:
            test_results_stationary_jitter = OneFingerStationaryJitterResults()

            test_results_stationary_jitter.panel_x = float(testresult[0])
            test_results_stationary_jitter.panel_y = float(testresult[1])
            test_results_stationary_jitter.sensitivity = float(testresult[2])
            test_results_stationary_jitter.finger_id = int(testresult[3])
            test_results_stationary_jitter.delay = testresult[4]
            test_results_stationary_jitter.time = testresult[5]
            test_results_stationary_jitter.event = testresult[6]
            test_results_stationary_jitter.panel_azimuth = testresult[7]
            test_results_stationary_jitter.panel_tilt = testresult[8]
            test_results_stationary_jitter.point_id = point_id
            dblist.append(test_results_stationary_jitter)

            self.context.add_dut_point(float(testresult[0]), float(testresult[1]), True, False)

        self.context.db.addAll(dblist)
