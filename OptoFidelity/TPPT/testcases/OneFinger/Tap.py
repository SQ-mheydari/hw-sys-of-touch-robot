from TPPTcommon.Node import *
from TPPTcommon.grid import *
from TPPTcommon.visualization import GridVisContainer
from MeasurementDB import *
from TPPTcommon.script_config import *
# Logging module is needed if script wants to send logging
# information to the debug window.
import logging
import time
import os
logger = logging.getLogger(__name__)

# Database table name for the test case.
DB_TABLE_NAME = 'one_finger_tap_test'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TABLE_NAME, 'test_id']]


class OneFingerTapTest( Base ):

    #One-finger tap results are defined here
    __tablename__ = DB_TABLE_NAME

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref(DB_TABLE_NAME, order_by=id) )

    #Are results single tap or jitter
    jitter = Column( Boolean )

    #Common parameters
    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    robot_azimuth = Column(Float)
    robot_tilt = Column(Float)
    point_number = Column( Integer )

    #Results
    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column(Float)
    panel_tilt = Column(Float)
    sensitivity = Column( Float )
    finger_id = Column( Integer )
    delay = Column( Float )
    time = Column( Float )


class Tap(TestStep):
    """
    In tap test robot taps DUT surface at a regular grid of points and touch event for each tap is recorded.
    User can also supply a custom set of points as a "grid file".
    """

    def __init__(self, context):
        super().__init__('Tap')

        self.context = context

        self.controls.clearance = -0.1
        self.controls.info['clearance'] = {'label': 'Clearance [mm]', 'min': -2.0, 'max': 10.0,
                                           'tooltip': self.context.tooltips['Clearance']}

        add_grid_file_controls(self)

        if get_config_value("separate_xy_parameters"):
            self.controls.grid_spacing_x = 2.0
            self.controls.info['grid_spacing_x'] = {'label': 'Grid spacing x [mm]', "validate": \
                ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                                                    'visibility_control': 'usegridfile',
                                                    'visibility_value': False,
                'tooltip': self.context.tooltips['Grid spacing x tap']}

            self.controls.grid_spacing_y = 2.0
            self.controls.info['grid_spacing_y'] = {'label': 'Grid spacing y [mm]', "validate": \
                ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                                                    'visibility_control': 'usegridfile',
                                                    'visibility_value': False,
                'tooltip': self.context.tooltips['Grid spacing y tap']}
        else:
            self.controls.grid_spacing = 2.0
            self.controls.info['grid_spacing'] = {'label': 'Grid spacing [mm]', "validate": \
                ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                                                  'visibility_control': 'usegridfile',
                                                  'visibility_value': False,
                'tooltip': self.context.tooltips['Grid spacing tap']}

        if get_config_value("grid_offsets"):
            if get_config_value("separate_xy_parameters"):
                self.controls.edge_offset_x = 0.0
                self.controls.info['edge_offset_x'] = {'label': 'Edge offset x [mm]', "validate": \
                    ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                                                       'visibility_control': 'usegridfile',
                                                       'visibility_value': False,
                    'tooltip': self.context.tooltips['Edge offset x']}

                self.controls.edge_offset_y = 0.0
                self.controls.info['edge_offset_y'] = {'label': 'Edge offset y [mm]', "validate": \
                    ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                                                       'visibility_control': 'usegridfile',
                                                       'visibility_value': False,
                    'tooltip': self.context.tooltips['Edge offset y']}
            else:
                self.controls.edge_offset = 0.0
                self.controls.info['edge_offset'] = {'label': 'Edge offset [mm]', "validate": \
                    ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                                                     'visibility_control': 'usegridfile',
                                                     'visibility_value': False,
                    'tooltip': self.context.tooltips['Edge offset']}

        self.controls.tap_duration = 0.0
        self.controls.info['tap_duration'] = {'label': 'Tap duration (s)', "validate": \
            ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x s'(eg. 0.1 or 2)"),
            'tooltip': self.context.tooltips['Tap duration']}

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

        # Main sequence contains common resources and state.
        dut = self.context.get_active_dut()
        tip = self.context.get_active_tip()

        base_distance = dut.base_distance

        self.context.html("Running One Finger Tap test for DUT: %s, tip: %s" % (dut, tip))

        # Create database entry for the test case.
        tap_test_item = self.context.create_db_test_item("One Finger Tap Test")

        # Get grid of points to tap.
        measurement_points = self.create_grid(dut)

        settings = self.context.settings_node.controls

        clearance = float(self.controls.clearance)

        for index, point in enumerate(measurement_points):
            point_number = index + 1

            # Update indicators in GUI.
            self.context.indicators.set_test_detail('Point', str(point_number) + ' / ' + str(len(measurement_points)))

            # Move over tap location. This might be far away from current location.
            # This makes sure that measurement timeout appropriately describes the tap gesture.
            dut.move(x=point.x, y=point.y, z=base_distance, tilt=point.tilt, azimuth=point.azimuth)

            # Start tap measurement.
            tap_measurement = self.context.create_tap_measurement(point)
            tap_measurement.start(timeout=get_tap_measurement_timeout())

            # Draw expected point to UI.
            self.context.add_dut_point(point.x, point.y, True, True)

            # Perform tap gesture.
            if get_config_value('enable_force') and settings.force_application == 'Force gesture':
                dut.press(x=point.x, y=point.y, force=settings.default_force, tilt=point.tilt, azimuth=point.azimuth,
                          duration=self.controls.tap_duration)
            else:
                dut.watchdog_tap(x=point.x, y=point.y, tilt=point.tilt, azimuth=point.azimuth, clearance=clearance,
                        duration=self.controls.tap_duration)

            # End tap measurement.
            tap_measurement.end()

            # Save results to database.
            self.save_measurement_data(tap_measurement.results, point, tap_test_item, point_number)

            # Check if test should pause or stop.
            self.context.breakpoint()

        self.context.close_db_test_item(tap_test_item)
    
    def create_grid(self, dut):
        """
        Create grid of points that define the geometry of the test case.
        :param dut: DUT where the grid is evaluated on.
        """

        if self.controls.usegridfile:
            grid_file_path = os.path.join(GRID_FILE_DIR, self.controls.gridfile)

            grid = create_grid_from_file(dut, grid_file_path, self.controls.gridunit)
        else:
            grid_spacing_x, grid_spacing_y, edge_offset_x, edge_offset_y = get_spacing_and_offset(self.controls)

            grid = create_point_grid(dut, grid_spacing_x, grid_spacing_y, edge_offset_x, edge_offset_y)

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
        Save tap test measurement to database.
        """

        test_result = OneFingerTapTest()
        test_result.jitter = False
        test_result.test_id = tap_test_item.id
        test_result.robot_x = robot_point.x
        test_result.robot_y = robot_point.y
        test_result.robot_z = 0.0#meas_point[2]
        test_result.robot_tilt = robot_point.tilt if hasattr(self.controls, "tilt_angles") else None
        test_result.robot_azimuth = robot_point.azimuth if hasattr(self.controls, "azimuth_angles") else None
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