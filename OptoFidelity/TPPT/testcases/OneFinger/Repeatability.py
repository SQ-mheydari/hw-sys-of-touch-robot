from TPPTcommon.Node import *
from TPPTcommon.grid import *
from MeasurementDB import *
from TPPTcommon.script_config import get_tap_measurement_timeout, get_config_value
from TPPTcommon.visualization import GridVisContainer
# Logging module is needed if script wants to send logging
# information to the debug window.
import logging
import os
logger = logging.getLogger(__name__)

# Database table name for the test case.
DB_TABLE_NAME = 'one_finger_tap_repeatability_test'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TABLE_NAME, 'test_id']]


class OneFingerTapRepeatabilityTest( Base ):

    #One-finger tap results are defined here
    __tablename__ = DB_TABLE_NAME

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref(DB_TABLE_NAME, order_by=id) )

    #Common parameters
    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    robot_azimuth = Column( Float )
    robot_tilt = Column( Float )
    point_number = Column( Integer )

    #Results
    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column( Float )
    panel_tilt = Column( Float )
    sensitivity = Column( Float )
    finger_id = Column( Integer )
    delay = Column( Float )
    time = Column( Float )
    event = Column( Integer )


class Repeatability(TestStep):
    """
    In repeatability test DUT is tapped at random locations multiple times per location.
    Touch events are used in analysis to inspect how close-by taps at single location are.
    """

    def __init__(self, context):
        """
        The 'init' method mainly defines the test case controls for GUI and is executed when script is loaded.
        """

        super().__init__('Repeatability')

        self.context = context

        self.controls.clearance = -0.1
        self.controls.info['clearance'] = {'label': 'Clearance [mm]', 'min': -2.0, 'max': 10.0,
                                           'tooltip': self.context.tooltips['Clearance']}

        self.controls.AmountOfTaps = 5
        self.controls.info['AmountOfTaps'] = {'label': 'Amount of taps per point', "min": 2,
                                              'tooltip': self.context.tooltips['Amount of taps']}

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

        self.context.html("Running One Finger Tap Repeatability test for dut:%s, tip:%s"%(dut, tip))

        # Create database item for the test.
        test_item = self.context.create_db_test_item("One Finger Tap Repeatability")

        measurement_points = self.create_grid(dut)

        settings = self.context.settings_node.controls

        clearance = float(self.controls.clearance)

        for point_index, point in enumerate(measurement_points):
            # Move over tap location. This might be far away from current location.
            # This makes sure that measurement timeout appropriately describes the tap gesture.
            dut.move(x=point.x, y=point.y, z=base_distance, azimuth=point.azimuth, tilt=point.tilt)

            # Draw expected point to UI.
            self.context.add_dut_point(point.x, point.y, True, True)

            for tap in range(self.controls.AmountOfTaps):
                point_number = point_index + 1

                # Update test indicators in GUI.
                tap_info = str(tap + 1) + ' / ' + str(self.controls.AmountOfTaps)
                point_info = str(point_number) + ' / ' + str(len(measurement_points))
                self.context.indicators.set_test_details([('Tap', tap_info), ('Point', point_info)])

                # Start measuring tap event.
                tap_measurement = self.context.create_tap_measurement(point)
                tap_measurement.start(timeout=get_tap_measurement_timeout())

                # Tap DUT at current test location.
                if get_config_value('enable_force') and settings.force_application == 'Force gesture':
                    dut.press(x=point.x, y=point.y, force=settings.default_force, azimuth=point.azimuth,
                              tilt=point.tilt)
                else:
                    dut.watchdog_tap(x=point.x, y=point.y, clearance=clearance, azimuth=point.azimuth, tilt=point.tilt)

                # End measuring tap event.
                tap_measurement.end()

                # Save tap measurement to database.
                self.save_measurement_data(tap_measurement.results, point, test_item, point_number)

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

    def save_measurement_data(self, measured_point_data, robot_point, tap_test_item, index):
        """
        Save repeatability measurement to database.
        """
        test_result = OneFingerTapRepeatabilityTest()

        test_result.test_id = tap_test_item.id
        test_result.robot_x = robot_point.x
        test_result.robot_y = robot_point.y
        test_result.robot_z = 0.0#meas_point[2]
        test_result.robot_azimuth = robot_point.azimuth if hasattr(self.controls, "azimuth_angles") else None
        test_result.robot_tilt = robot_point.tilt if hasattr(self.controls, "tilt_angles") else None
        test_result.point_number = int(index)

        if len(measured_point_data) > 0:
            p2p_data = measured_point_data[0]
            test_result.panel_x = p2p_data[0]
            test_result.panel_y = p2p_data[1]
            test_result.sensitivity = p2p_data[2]
            test_result.finger_id = p2p_data[3]
            test_result.panel_azimuth = p2p_data[7]
            test_result.panel_tilt = p2p_data[8]

            self.context.add_dut_point(p2p_data[0], p2p_data[1], True, False)

        self.context.db.add(test_result)
