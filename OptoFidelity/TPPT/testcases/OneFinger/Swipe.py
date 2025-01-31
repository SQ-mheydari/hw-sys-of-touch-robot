from TPPTcommon.Node import *
from TPPTcommon.grid import *
from TPPTcommon.visualization import GridVisContainer
from MeasurementDB import *
from TPPTcommon.script_config import *
# Logging module is needed if script wants to send logging
# information to the debug window.
import logging
logger = logging.getLogger(__name__)

# Database table name for the test case.
DB_TEST_TABLE_NAME = 'one_finger_swipe_test'

# Database table name for the test results.
DB_RESULTS_TABLE_NAME = 'one_finger_swipe_results'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TEST_TABLE_NAME, 'test_id'], [DB_RESULTS_TABLE_NAME, 'swipe_id']]


class OneFingerSwipeTest( Base ):

    #One-finger swipe test is defined here
    __tablename__ = DB_TEST_TABLE_NAME

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref(DB_TEST_TABLE_NAME, order_by = id) )
    robot_azimuth = Column( Float )
    robot_tilt = Column( Float )

    #For straight lines, start and stop positions are defined
    start_x = Column( Float )
    start_y = Column( Float )
    end_x = Column( Float )
    end_y = Column( Float )

    #For circular lines, also through position and radius in x and y directions are defined
    through_x = Column( Float )
    through_y = Column( Float )
    radius_x = Column( Float )
    radius_y = Column( Float )


class OneFingerSwipeResults( Base ):

    #One-finger swipe results are defined here
    __tablename__ = DB_RESULTS_TABLE_NAME

    id = Column( Integer, primary_key = True )
    swipe_id = Column( Integer, ForeignKey(DB_TEST_TABLE_NAME + '.id', ondelete='CASCADE'), nullable=False )
    swipe = relation( OneFingerSwipeTest, backref = backref(DB_RESULTS_TABLE_NAME, order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column( Float )
    panel_tilt = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )


class Swipe(TestStep):
    """
    In swipe test DUT is swept along set of lines and touch events are collected as continuous stream.
    """

    def __init__(self, context):
        super().__init__('Swipe')
        """
        The 'init' method mainly defines the test case controls for GUI and is executed when script is loaded.
        """

        self.context = context

        self.controls.grid_spacing = 2.0
        self.controls.info['grid_spacing'] = {'label': 'Grid spacing [mm]', "validate": \
            ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
            'tooltip': self.context.tooltips['Grid spacing swipe']}

        self.controls.swipe_radius = 6.0
        self.controls.info['swipe_radius'] = {'label': 'Swipe radius [mm]', 'min': get_min_swipe_radius(),
                                              'max': get_max_swipe_radius(),
                                              'tooltip': self.context.tooltips['Swipe radius']}
        self.controls.clearance = -0.1
        self.controls.info['clearance'] = {'label': 'Clearance [mm]', 'min': get_min_swipe_clearance(),
                                           'max': get_max_swipe_clearance(),
                                           'tooltip': self.context.tooltips['Clearance']}

        if get_config_value("grid_offsets") and get_config_value("separate_xy_parameters"):
            self.controls.edge_offset_x = 0.0
            self.controls.info['edge_offset_x'] = {'label': 'Edge offset X [mm]', "validate": \
                ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                    'tooltip': self.context.tooltips['Edge offset x']}
            self.controls.edge_offset_y = 0.0
            self.controls.info['edge_offset_y'] = {'label': 'Edge offset Y [mm]', "validate": \
                ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                    'tooltip': self.context.tooltips['Edge offset y']}
        elif get_config_value("grid_offsets"):
            self.controls.edge_offset = 0.0
            self.controls.info['edge_offset'] = {'label': 'Edge offset [mm]', "validate": \
                ('(^[+]?\d+(?:\.\d+)?(?:[eE][+]\d+)?$)', "Correct format is 'x mm'(eg. 2 or 2.0)"),
                    'tooltip': self.context.tooltips['Edge offset']}

        self.controls.swipe_type = 'swipe'
        self.controls.info['swipe_type'] = {'label': 'Swipe type', 'items': {'swipe', 'drag'},
                                            'tooltip': self.context.tooltips['Swipe type']}

        self.controls.worstcasetest = True
        self.controls.info['worstcasetest'] = {'label': 'Worst case lines',
                                               'tooltip': self.context.tooltips['Worst case lines']}

        self.controls.verticallines = False
        self.controls.info['verticallines'] = {'label': 'Vertical/Horizontal lines.',
                                               'tooltip': self.context.tooltips['Vertical/horizontal lines']}

        self.controls.diagonallines = False
        self.controls.info['diagonallines'] = {'label': 'Diagonal lines',
                                               'tooltip': self.context.tooltips['Diagonal lines']}

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
        speeds = parse_numbers(self.context.settings_node.controls.line_drawing_speed)
        base_distance = dut.base_distance
        clearance = float(self.controls.clearance)
        swipe_radius = float(self.controls.swipe_radius)

        # Sanity checks for swipe parameters.
        check_swipe_parameters(clearance, swipe_radius)

        # Swipe test consists of multiple optional sets of swipes.
        tests = []
        if self.controls.verticallines:
            tests.append("vertical_horizontal")
        if self.controls.diagonallines:
            tests.append("diagonal")
        if self.controls.worstcasetest:
            tests.append("worst_case")

        for speed in speeds:

            settings = self.context.settings_node.controls

            for test in tests:
                self.context.html("Running One Finger Swipe test for dut: %s, tip: %s, drawing speed: %s "
                                  "Test pattern is %s" % (dut, tip, speed, test))

                # Create database entry for the test case. Each swipe set is separate test case.
                test_item = self.context.create_db_test_item("One Finger Swipe Test", speed=speed)

                # Create swipe lines for current test set.
                measurement_lines = self.create_grid(dut, test)

                for index, line in enumerate(measurement_lines):
                    # Update indicators in GUI.
                    self.context.indicators.set_test_detail('Line', str(index + 1) + ' / ' +str(len(measurement_lines)))

                    # Create database entry for the line to swipe.
                    swipe_id = self.create_line_id(line, test_item)

                    # Jump with default speed over the start point of the line to swipe.
                    self.context.set_robot_default_speed()
                    dut.jump(line.start_x, line.start_y, base_distance, base_distance)

                    # Set angle before measurement start
                    dut.move(x=line.start_x, y=line.start_y, z=base_distance, azimuth=line.azimuth, tilt=line.tilt)

                    # Swipe with specific speed.
                    self.context.set_robot_speed(speed)

                    # Start capturing a continuous stream of touch events.
                    continuous_measurement = self.context.create_continuous_measurement(line)
                    continuous_measurement.start(timeout=get_continuous_measurement_timeout())

                    # Draw expected line to UI
                    self.context.draw_dut_expected_line(line.start_x, line.start_y, line.end_x, line.end_y)

                    if get_config_value('enable_force') and settings.force_application == 'Force gesture':
                        dut.drag_force(line.start_x, line.start_y, line.end_x, line.end_y, force=settings.default_force)
                    else:
                        # Perform swipe or drag gesture based on user preference
                        if self.controls.swipe_type == 'drag':
                            dut.drag(line.start_x, line.start_y, line.end_x, line.end_y, clearance=clearance,
                                     azimuth1=line.azimuth, azimuth2=line.azimuth, tilt1=line.tilt, tilt2=line.tilt)
                        else: # normal swipe
                            dut.swipe(line.start_x, line.start_y, line.end_x, line.end_y, clearance=clearance,
                                      radius=swipe_radius, azimuth1=line.azimuth, azimuth2=line.azimuth,
                                      tilt1=line.tilt, tilt2=line.tilt)

                    # End measuring touch events.
                    continuous_measurement.end()

                    # Parse touch event data.
                    touchlist = continuous_measurement.parse_data()

                    # Save results to database.
                    self.save_measurement_data(swipe_id, touchlist)

                    # Check if test should pause or stop.
                    self.context.breakpoint()

                self.context.close_db_test_item(test_item)
        
    def create_grid(self, dut, pattern):
        """
        Create grid of lines that define the geometry of the test case.
        :param dut: DUT where the grid is evaluated on.
        :param pattern: Pattern string that defines sweep line set.
        """

        _, _, edge_offset_x, edge_offset_y = get_spacing_and_offset(self.controls)

        if pattern == "vertical_horizontal":
            grid = create_vertical_horizontal_line_grid(dut, self.controls.grid_spacing, edge_offset_x, edge_offset_y)
        elif pattern == "diagonal":
            grid = create_diagonal_line_grid(dut, self.controls.grid_spacing, edge_offset_x, edge_offset_y)
        elif pattern == "worst_case":
            grid = create_worst_case_lines(dut, edge_offset_x, edge_offset_y)
        else:
            assert False

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

        test_pattern = []

        # Show swipe lines of all enabled sets.
        if self.controls.verticallines:
            test_pattern += self.create_grid(dut, "vertical_horizontal")
        if self.controls.diagonallines:
            test_pattern += self.create_grid(dut, "diagonal")
        if self.controls.worstcasetest:
            test_pattern += self.create_grid(dut, "worst_case")

        return GridVisContainer(self.__class__.__name__, (dut.width, dut.height), test_pattern, dut.name)

    def create_line_id(self, line, test_item):

        swipetest = OneFingerSwipeTest()

        swipetest.start_x = line.start_x
        swipetest.start_y = line.start_y
        swipetest.end_x = line.end_x
        swipetest.end_y = line.end_y
        swipetest.robot_azimuth = line.azimuth if hasattr(self.controls, "azimuth_angles") else None
        swipetest.robot_tilt = line.tilt if hasattr(self.controls, "tilt_angles") else None
        swipetest.test_id = test_item.id
        self.context.db.add(swipetest)

        return swipetest.id

    def save_measurement_data(self, line_id, touchlist):
        """
        Save swipe measurement to database.
        """

        dblist = []

        for testresult in touchlist:
            testresultswipe = OneFingerSwipeResults()

            testresultswipe.panel_x = float(testresult[0])
            testresultswipe.panel_y = float(testresult[1])
            testresultswipe.sensitivity = float(testresult[2])
            testresultswipe.finger_id = int(testresult[3])
            testresultswipe.delay = testresult[4]
            testresultswipe.time = testresult[5]
            testresultswipe.event = testresult[6]
            testresultswipe.panel_azimuth = float(testresult[7])
            testresultswipe.panel_tilt = float(testresult[8])
            testresultswipe.swipe_id = line_id
            dblist.append(testresultswipe)

            self.context.add_dut_point(float(testresult[0]), float(testresult[1]), False, False)

        self.context.db.addAll(dblist)


