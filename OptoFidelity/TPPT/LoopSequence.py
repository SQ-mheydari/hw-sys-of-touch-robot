import os
from TPPTcommon.visualization import GridVisualizer
from TPPTcommon.DutNode import DutsNode
from TPPTcommon.TipNode import TipsNode
from TPPTcommon.TestsNode import TestsNode, get_test_case_modules
from TPPTcommon.SettingsNode import SettingsNode
from TPPTcommon.Node import *
from TPPTcommon.Indicators import Indicators
import MeasurementDB
from scriptpath import join_script_root_directory
from client.tntclient.tnt_client import TnTClient
import threading
import traceback

logger = logging.getLogger(__name__)

# TnT Server address and port.
SERVER_HOST = '127.0.0.1'
SERVER_PORT = '8000'

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Absolute path of database file where results are saved.
DATABASE_PATH = join_script_root_directory('database.sqlite')

# Absolute path of file where script parameter history is saved.
HISTORY_PATH = join_script_root_directory('history.json')

# State of script context
STATE_WAITING = 0
STATE_EXECUTING = 1
STATE_PAUSED = 2
STATE_STOPPED = 3


class Context:
    """
    Contains data that is used by test cases such as
    - TnT client
    - Sequence nodes
    - Measurement data collection drivers
    - Interface to UI
    """

    def __init__(self, ui):
        """
        This is called when script is loaded.
        Sets up TnT client, discovers available DUTs and tips, creates GUI controls for test cases,
        initializes TCP socket and loads test cases as child nodes.
        :param ui: User interface object that initializes script context.
        """

        self.ui = ui

        self.state = STATE_WAITING

        # Test sequence is executed in a thread to keep the calling thread responsive.
        self.execution_thread = None

        # Parameters show up in UI as text input fields.
        self.parameters = []
        self.parameters.append(Parameter('Program'))
        self.parameters.append(Parameter('Manufacturer'))
        self.parameters.append(Parameter('Version'))
        self.parameters.append(Parameter('Operator'))
        self.parameters.append(Parameter('Serial'))
        self.parameters.append(Parameter('Notes', single_line=False))

        self.indicators = Indicators(ui)

        # These are tuples of type (function, label). UI creates buttons for each tuple.
        self.callables = [(self.visualize_grids, 'Show measurement points')]

        self.tooltips = self.read_tooltips_to_dict('tooltips.md')
        # Connect to TnT Server by using TnTClient and get the default robot.
        self.tnt = TnTClient(SERVER_HOST, SERVER_PORT)
        self.robot = self.tnt.robot("Robot1")

        # DUT ID is used to track DUT database entry during test session.
        self.dut_id = None

        self.test_session = None
        self.test_session_id = None

        # Root node contains all other nodes.
        self.root_node = RootNode()

        self.settings_node = SettingsNode(self)
        self.root_node.add_child(self.settings_node)

        self.duts_node = DutsNode(self)
        self.duts_node.create_duts()
        self.root_node.add_child(self.duts_node)

        # Dut dimensions and resolution so that point places can be calculated in pixels and mm.
        self.dut_width = 0
        self.dut_height = 0
        self.dut_resolution = (0, 0)

        self.tips_node = TipsNode(self)
        self.tips_node.create_tips()
        self.root_node.add_child(self.tips_node)

        self.tests_node = TestsNode('Tests')
        self.root_node.add_child(self.tests_node)

        self.one_finger_tests_node = TestsNode('One finger tests')
        self.one_finger_tests_node.import_test_cases(self, 'OneFinger')
        self.tests_node.add_child(self.one_finger_tests_node)

        self.two_finger_tests_node = TestsNode('Two finger tests')

        if os.path.exists(os.path.join(join_script_root_directory('testcases'), 'TwoFinger')):
            self.two_finger_tests_node.import_test_cases(self, 'TwoFinger')
            self.tests_node.add_child(self.two_finger_tests_node)

        self.multi_finger_tests_node = TestsNode('MultiFinger tests')

        if os.path.exists(os.path.join(join_script_root_directory('testcases'), 'MultiFinger')):
            self.multi_finger_tests_node.import_test_cases(self, 'MultiFinger')
            self.tests_node.add_child(self.multi_finger_tests_node)

        # Import test cases.
        self.tests_node.import_test_cases(self)

        self.db = None

        self.database_path = MeasurementDB.getLastPath()

        # Update initial values in UI.
        ui.set_history_headers(self.load_history_headers())
        ui.set_script_nodes(self.root_node.to_dict())
        ui.set_script_parameters(self.parameters_to_list())
        ui.set_results_database_filename(self.database_path)
        ui.set_script_callables([c[1] for c in self.callables])

        ui.script_ready()

    def get_parameter(self, name):
        """
        Get parameter by name.
        :param name: Name of parameter
        :return: The parameter
        """
        for p in self.parameters:
            if p.name == name:
                return p

    def create_dut_visualization(self, xpixels, ypixels):
        """
        Create DUT visualization in UI to show test step progress.
        :param xpixels: Number of DUT screen pixels in x-direction.
        :param ypixels: Number of DUT screen pixels in y-direction.
        """
        self.ui.create_dut_svg(xpixels, ypixels)

    def add_dut_point(self, x, y, from_taplike, expected):
        """
        Add DUT measurement point and expected point to UI to show test step progress.
        :param x: X-coordinate of point in pixels.
        :param y: Y-coordinate of point in pixels.
        :param from_taplike: Tells if current point is from tap like gesture or from swipe gesture.
        :param expected: Tells if this is expected or measured point.
        """
        if expected:
            # Calculate expected x and y in pixels.
            x_pixels = x * self.dut_resolution[0] / self.dut_width
            y_pixels = y * self.dut_resolution[1] / self.dut_height
            self.ui.add_dut_point(x_pixels, y_pixels, x, y, expected, from_taplike)
        else:
            dut_node = self.get_active_dut_node()
            x, y, x_mm, y_mm = dut_node.panel_to_target(x, y, self.dut_width, self.dut_height)
            self.ui.add_dut_point(x, y, x_mm, y_mm, expected, from_taplike)

    def draw_dut_expected_line(self, start_x, start_y, end_x, end_y):
        """
        Send line data to UI
        :param start_x: Start X-coordinate for the line.
        :param start_y: Start Y-coordinate for the line.
        :param end_x: End X-coordinate for the line.
        :param end_y: End Y-coordinate for the line.
        """
        # Get necessary info from DUT to perform all calculations
        dut_width = self.get_active_dut().width
        dut_height = self.get_active_dut().height
        dut_resolution = self.get_active_dut_node().resolution


        # Calculate expected x and y in pixels.
        start_x_pixels = start_x * dut_resolution[0] / dut_width
        start_y_pixels = start_y * dut_resolution[1] / dut_height
        end_x_pixels = end_x * dut_resolution[0] / dut_width
        end_y_pixels = end_y * dut_resolution[1] / dut_height

        self.ui.draw_dut_expected_line(start_x_pixels, start_y_pixels, end_x_pixels, end_y_pixels)


    def clear_dut_points(self):
        """
        Clear DUT measurement points in UI.
        """
        self.ui.clear_dut_points()

    def execute_one_finger_tests(self):
        if self.one_finger_tests_node.num_enabled_children == 0:
            return

        # Make sure there is no tip in the separated finger.
        self.tips_node.detach_tip(1)

        num_tips = 0

        for tip_node in self.tips_node.children:
            if tip_node.enabled and not tip_node.tnt_tip.is_multifinger:
                num_tips += 1

        if num_tips == 0:
            raise Exception("No tips selected for one-finger tests")

        tip_count = 0

        # Loop through enabled tips.
        for tip_node in self.tips_node.children:
            if not tip_node.enabled:
                continue

            # Skip multifinger tips in one-finger tests.
            if tip_node.tnt_tip.is_multifinger:
                continue

            self.indicators.set_status("Changing tip to " + tip_node.name)

            self.tips_node.set_active_tip(tip_node)

            tip_count += 1
            self.indicators.set_tip_name(
                tip_node.name + ' (' + str(tip_count) + ' / ' + str(num_tips) + ')')

            test_count = 0

            # Jump over DUT origin.
            self.set_robot_dut_change_speed()
            active_dut = self.get_active_dut()
            active_dut.jump(0.0, 0.0, active_dut.base_distance)

            # Run the tests with current DUT and tip.
            for test in self.one_finger_tests_node.children:
                # Skip test case if it is not enabled.
                if not test.enabled:
                    continue

                # Set default robot speed before running test case. Previous test may have changed current robot speed.
                self.set_robot_default_speed()

                self.clear_dut_points()

                test_count += 1
                self.indicators.set_status(
                    "Executing one-finger test case " + test.name + ' (' + str(test_count) + ' / ' + str(
                        self.one_finger_tests_node.num_enabled_children) + ')')

                # Run test case.
                test.execute()

            # Update test session status.
            self.test_session.endtime = time.strftime(TIME_FORMAT)
            self.test_session.invalid = False
            self.db.update(self.test_session)

    def _execute(self):
        """
        This is called when test is started.
        Loops every DUT and tip and calls test case child nodes.
        TODO: Should perhaps refactor looping DUTs and tips into separate nodes for flexibility.
        """

        # Reset indicators.
        self.indicators = Indicators(self.ui)
        self.indicators.update_ui()

        self.html_color("Starting test sequence (" + time.strftime(TIME_FORMAT) + ")", "green")

        # Make the axial finger active as test cases are designed for that.
        self.robot.set_active_finger(0)

        # Make sure there is no tip in the separated finger. This must be ensure for one-finger tests.
        self.tips_node.detach_tip(1)

        if not self.duts_node.check_duts():
            return

        if not self.tips_node.check_tips() and self.one_finger_tests_node.num_enabled_children > 0:
            self.html_error("No tips selected!")
            return

        # Create test session database entry.
        self.test_session = MeasurementDB.TestSession()
        self.test_session.operator = self.get_parameter('Operator').value
        self.test_session.starttime = time.strftime(TIME_FORMAT)
        self.test_session.notes = self.get_parameter('Notes').value
        self.test_session_id = self.db.add(self.test_session)
        # self.test_session_id = self.test_session.id

        dut_count = 0

        self.save_test_session_parameters()

        # Loop through enabled DUTs.
        for dut_node in self.duts_node.children:
            if not dut_node.enabled:
                continue

            # At the moment this is not very useful as jump between DUTs is done in test case execution.
            self.indicators.set_status("Changing DUT to " + dut_node.name)

            dut = dut_node.tnt_dut

            # Initialize the DUT and the driver
            try:
                self.duts_node.initialize(dut_node)
                self.html("Initialized {}".format(dut_node.name))
                self.html("Initialized {}".format(self.duts_node.active_driver))
            except Exception as e:
                self.html_error('Following error happened while initializing the DUT and the driver: ' + str(e))
                continue

            dut_count += 1
            self.indicators.set_dut_name(
                dut_node.name + ' (' + str(dut_count) + ' / ' + str(self.duts_node.num_enabled_children) + ')')

            # Assign DUT db table ID to be used by test cases to create test case database entries.
            self.dut_id = self.create_dut_db_entry(dut)

            self.save_control_values()

            # Get necessary info from DUT to perform all calculations
            self.dut_width = dut.width
            self.dut_height = dut.height
            self.dut_resolution = dut_node.resolution

            # One-finger tests.
            self.execute_one_finger_tests()

            # Two-finger and multi-finger tests.

            # Jump over DUT origin.
            self.set_robot_dut_change_speed()
            active_dut = self.get_active_dut()
            active_dut.jump(0.0, 0.0, active_dut.base_distance)

            test_nodes = self.two_finger_tests_node.children + self.multi_finger_tests_node.children

            # Run the tests with current DUT and tip.
            for test in test_nodes:
                # Skip test case if it is not enabled.
                if not test.enabled:
                    continue

                # Set default robot speed before running test case. Previous test may have changed current robot speed.
                self.set_robot_default_speed()

                self.clear_dut_points()

                # Run test case.
                test.execute()

            # Update test session status.
            self.test_session.endtime = time.strftime(TIME_FORMAT)
            self.test_session.invalid = False
            self.db.update(self.test_session)

        self.html_color('Test sequence completed', 'green')
        self.indicators.set_status("Test sequence completed")

    def _try_execute(self):
        """
        Execute test cases in try block to catch stop condition.
        """

        # Open database just before execution to make sure that SQL objects are created in the same thread.
        test_case_modules = get_test_case_modules(self.tests_node)

        self.db = MeasurementDB.ResultDatabase(self.database_path, test_case_modules)

        try:
            self._execute()
        except Stop:  # User stopped execution
            pass
        except Exception as e:
            # Call UI error function directly as exception is not passed to calling thread.
            message = str(e)
            message += traceback.format_exc()
            self.ui.script_failed(message)

        self.state = STATE_WAITING
        self.ui.script_finished()
        self.ui.set_history_headers(self.load_history_headers())

    def save_test_session_parameters(self):
        """
        Save test session specific parameters.
        """
        # Save each general setting as test session parameter.
        for name in self.settings_node.controls.get_controls():
            value = getattr(self.settings_node.controls, name)
            value = str(value)

            parameter = MeasurementDB.SessionParameters()
            parameter.testsession_id = self.test_session_id
            parameter.name = name
            parameter.valueString = value
            parameter.isFloat = False

            self.db.add(parameter)

    def save_control_values(self):
        """
        Save values of controls to database in order to restore them later if needed.
        """

        dut_node = self.duts_node.active_dut_node

        # Save all control values to session parameters table in database
        for control in dut_node.controls.get_controls():
            parameter_label = dut_node.controls.info[control]["label"]

            session_parameters = MeasurementDB.DutParameters()
            session_parameters.dut_id = self.dut_id

            # TODO: Might be better to use control key as parameter name instead of label.
            session_parameters.name = parameter_label

            selected_value = getattr(dut_node.controls, control)

            # Database expects to receive some values in float;float or int;int format
            if control == 'dut_resolution':
                selected_value = str(selected_value[0]) + ";" + str(selected_value[1])

            if isinstance(selected_value, bool):
                session_parameters.valueString = str(int(selected_value))
            else:
                session_parameters.valueString = str(selected_value)

            self.db.add(session_parameters)

    def create_dut_db_entry(self, dut):
        """
        Create database entry from DUT data.
        :param dut: DUT to use.
        :return: ID of DUT database table entry.
        """

        # Each test run creates new DUT information in case DUT parameters were changed.
        test_dut = MeasurementDB.TestDUT()
        test_dut.program = self.get_parameter('Program').value
        test_dut.manufacturer = self.get_parameter('Manufacturer').value
        test_dut.batch = self.get_parameter('Version').value
        test_dut.serial = self.get_parameter('Serial').value
        test_dut.sample_id = str(dut)
        self.db.add(test_dut)

        # Add DUT dimensions
        session_parameters = MeasurementDB.DutParameters()
        session_parameters.dut_id = test_dut.id
        session_parameters.name = 'DUT dimensions [x;y, mm]'
        session_parameters.valueString = "%s;%s" % (self.tnt.dut(str(dut)).width,
                                                    self.tnt.dut(str(dut)).height)
        self.db.add(session_parameters)

        # Add DUT offset, this should be set when a new DUT is created.
        # TODO: Read this information from TnT API when this feature is implemented
        session_parameters = MeasurementDB.DutParameters()
        session_parameters.dut_id = test_dut.id
        session_parameters.name = 'DUT offset [x;y, mm]'
        session_parameters.valueString = "0;0"
        self.db.add(session_parameters)

        # Add display resolution, this should be set when a new DUT is created.
        # TODO: Read this information from TnT API when this feature is implemented
        session_parameters = MeasurementDB.DutParameters()
        session_parameters.dut_id = test_dut.id
        session_parameters.name = 'Display resolution [x;y, p.c.]'
        session_parameters.valueString = "0;0"
        self.db.add(session_parameters)

        return test_dut.id

    def visualize_grids(self):
        """
        Visualizes the test grids.
        """
        try:
            self.ui.change_to_figure_page()
            tests = []

            for finger_mode_node in self.tests_node.children:
                for test in finger_mode_node.children:
                    if test.enabled:
                        tests.append(test)

            if not self.duts_node.check_duts():
                self.html_color('Could not display test grid:', 'red')
                self.html_color('No DUTS selected.', 'red')
                return

            if not tests:
                self.html_color('Could not display test grid:', 'red')
                self.html_color('No tests selected.', 'red')
                # self.app.warning_dialog(self, "No tests selected.", caption = "Could not display test grid!")
                self.ui.hide_loading_element()
                return

            grids = {}
            for i in tests:
                i_name = i.__class__.__name__
                for j in self.duts_node.children:
                    if not j.enabled:
                        continue

                    if i_name not in grids: grids[i_name] = []

                    if hasattr(i, 'visualize_grid'):
                        grids[i_name].append(i.visualize_grid(j.tnt_dut))

            plotter = GridVisualizer()
            plotter.AddGridList(grids)
            images = plotter.Render()
            self.ui.hide_loading_element()
            self.ui.append_images_to_figure_page(images)
        except Exception as e:
            self.html("visualize_grids: %s" % e)
            self.ui.script_failed(str(e))
            # self.dialog("Active grid calculation failed!\n It seems that the grid value is too big.\nPlease try again with different grid value (e.g. 2.0)")

    def get_active_dut(self):
        """
        :return: The active DUT.
        """
        if self.duts_node.active_dut is None:
            self.html("Could not find active DUT")
            raise Exception("Could not find active DUT")

        return self.duts_node.active_dut

    def get_active_dut_node(self):
        """
        :return: The active DUT's node.
        """
        dut = self.duts_node.active_dut_node
        if dut is None:
            self.html("Could not find active DUT node")
            raise Exception("Could not find active DUT node")
        return dut

    def get_active_tip(self):
        """
        :return: The active tip.
        """
        if self.tips_node.active_tip is None:
            self.html("Could not find active tip")
            raise Exception("Could not find active tip")

        return self.tips_node.active_tip

    def get_active_dut_driver(self):
        """
        :return: Current DUT driver.
        """
        return self.duts_node.active_driver

    def create_db_test_item(self, test_name, speed: float = None):
        """
        Creates new test to test table to database.
        :param test_name: Name of test that is used to find the test type ID for database.
        :param speed: swipe speed used for certain test items
        :return: TestItem object.
        """

        # Create dictionary to find test type ID by test name.
        test_types = self.db.get_TestTypes()
        logger.debug(test_types)
        test_dictionary = {}
        for test_type in test_types:
            test_dictionary[test_type.name] = test_type.id

        # Create a new ddt test table to database
        ddt_test = MeasurementDB.TestItem()
        if speed is not None:
            ddt_test.speed = speed
        else:
            ddt_test.speed = self.settings_node.controls.default_speed
        ddt_test.dut_id = self.dut_id
        ddt_test.finger_type = str(self.get_active_tip()) if self.tips_node.active_tip is not None else ""
        ddt_test.testsession_id = self.test_session_id
        # Slot id needs to be saved always for legacy reasons.
        try:
            ddt_test.slot_id = int(self.duts_node.active_dut_node.controls.pit_slot)
        except AttributeError:
            logger.info("PIT Slot_id not defined, using value 0")
            ddt_test.slot_id = 0
        ddt_test.starttime = time.strftime(TIME_FORMAT)
        ddt_test.invalid = True
        ddt_test.testtype_id = test_dictionary[test_name]

        # Add and commit but don't expire.
        # This is because close_db_test_item() later changes test status (e.g. invalid to False).
        self.db.add(ddt_test, expire_on_commit=False)

        return ddt_test

    def close_db_test_item(self, db_item):
        """
        Close database test item i.e. commit changes to database.
        This also marks the test item complete for the analyzer.
        :param db_item: Database item to close. Must have been created with create_db_test_item().
        """
        db_item.endtime = time.strftime(TIME_FORMAT)
        db_item.invalid = False

        self.db.update(db_item)
        self.html_color("Test step completed", "green")

    def set_robot_speed(self, speed, acceleration=None):
        self.robot.set_speed(speed, acceleration)

    def set_robot_default_speed(self):
        """
        Set speed and acceleration defined by main sequence controls.
        """
        self.set_robot_speed(self.settings_node.controls.default_speed,
                             self.settings_node.controls.default_acceleration)

    def set_robot_dut_change_speed(self):
        """
        Set speed and acceleration that are appropriate for changing DUTs.
        Usually should use high speed but medium acceleration.
        """

        self.set_robot_speed(100, 100)

    def send_image(self, image_filename=None):
        """
        Sends given image to DUT. JPG and PNG image formats are supported.
        :param image_filename: Image filename.
        :return: Nothing.
        """

        # In case there is some error in sending image, retry a fixed number of times.
        num_retrys = 5

        for i in range(0, num_retrys):
            try:
                if image_filename is not None and len(image_filename) > 0:
                    script_file_path = os.path.dirname(os.path.realpath(__file__))
                    image_filename = os.path.join(script_file_path, 'background_images', image_filename)
                else:
                    image_filename = None
                dut = self.get_active_dut()

                if image_filename is not None:
                    with open(image_filename, "rb") as file:
                        im_data = file.read()
                else:
                    im_data = None

                dut.show_image(im_data)
                return
            except Exception as e:  # Not sure what kind of errors may occur but retry in case of any error.
                message = "Sending image to DUT failed. Retrying ({}/{}) ...".format(i + 1, num_retrys)
                self.html_error(message)

                # Sleep for a while between retries in case e.g. network has some temporary problem.
                time.sleep(1.0)

        # If problem is not fixed by retrying, raise exception to be handled by caller.
        raise Exception("Sending image to DUT failed after retries.")

    def create_tap_measurement(self, point):
        '''
        Create tap measurement instance according to current state (DUT, tip).
        :param point: Robot point where tap is performed.
        :return: Tap measurement object based on TapMeasurement super class.
        '''
        tap_measurement_class = self.duts_node.active_driver_tap_meas
        active_driver = self.duts_node.active_driver_object

        return tap_measurement_class(self.indicators, point, active_driver)

    def create_continuous_measurement(self, line):
        '''
        Create continuous measurement instance according to current state (DUT, tip).
        :param line: Line that robot will swipe.
        :return: Continuous measurement object based on ContinuousMeasurement super class.
        '''
        cont_measurement_class = self.duts_node.active_driver_continuous_meas
        active_driver = self.duts_node.active_driver_object

        return cont_measurement_class(self.indicators, line, active_driver)

    def set_indicators(self, text):
        """
        Set indicators in UI.
        Indicators is currently just a text caption that can use HTML / CSS.
        :param text: Text to set for indicator.
        """
        self.ui.set_indicators(text)

    def stop(self):
        """
        Stop test execution.
        Assuming that execute_tests() is running in another thread, the execution there will stop.
        """
        if self.state != STATE_WAITING:
            self.state = STATE_STOPPED

        self.execution_thread.join()
        try:
            self.duts_node.active_driver_object.close_at_test_finish()
        except AttributeError:
            # No active driver object, no need to close securely.
            pass

    def toggle_pause(self):
        """
        Stop or continue test execution.
        """
        if self.state == STATE_EXECUTING:
            self.state = STATE_PAUSED
        elif self.state == STATE_PAUSED:
            self.state = STATE_EXECUTING

    def breakpoint(self):
        """
        Test whether test execution should pause or stop.
        This should be called by test cases at regular intervals.
        """
        while self.state == STATE_PAUSED:
            time.sleep(1.0)

        if self.state == STATE_STOPPED:
            raise Stop()

    def html(self, message):
        """
        Print message to UI and log.
        Can use HTML / CSS.
        :param message: Message to print.
        """
        self.ui.log(message)
        logger.info(message)

    def html_color(self, text, color):
        """
        Print message to UI and log.
        Can use HTML / CSS.
        :param message: Message to print.
        :param color: Color of the message. A string such as 'red'.
        """
        self.ui.log('<font color="%s">%s</font>' % (color, text))
        logger.info(text)

    def html_warning(self, warning_message):
        """
        Print warning message to UI and log.
        Can use HTML / CSS.
        :param warning_message: Message to print.
        """
        self.ui.log('<font color="orange">%s</font>' % (warning_message))
        logger.warning(warning_message)

    def html_error(self, error_message):
        """
        Print error message to UI (with red color) and log.
        Can use HTML/CSS
        :param error_message: Message to print
        :return: -
        """
        self.ui.log('<font color="red">%s</font>' % (error_message))
        logger.error(error_message)

    def execute_tests(self):
        """
        Executes test cases.
        This is called by UI.
        Launches a separate thread for test case execution to keep the calling UI responsive.
        UI should call stop() even after completion of test sequence to join the thread.
        """

        if self.state != STATE_WAITING:
            return

        self.state = STATE_EXECUTING

        # self.root.traverse('execute', self)

        self.execution_thread = threading.Thread(target=self._try_execute)
        self.execution_thread.start()

    def set_database_path(self, path):
        """
        Set results database file to a specified path.
        :param path: Filename for results database.
        :return:
        """
        self.database_path = path

    def save(self, name=None, path=None):
        """
        Save script value state to history file.
        :param name: Name to use for parameter set instead of default generated timestamp.
        :param path: Path to JSON filename to use.
        """
        path = HISTORY_PATH if path is None else path
        save_script_values(path, self.root_node.children, self.parameters, name=name)

    def load(self, name, path=None):
        """
        Load script value state from a file.
        :param name: Name of the piece of history to load (by default date and time of save).
        :param path: Path to JSON file containing script settings.
        """
        path = HISTORY_PATH if path is None else path
        load_script_values(path, name, self.root_node.children, self.parameters)

        # Update script content in UI according to loaded values.
        self.ui.set_script_nodes(self.root_node.to_dict())
        self.ui.set_script_parameters(self.parameters_to_list())
        self.ui.set_script_callables([c[1] for c in self.callables])

    def load_history_headers(self):
        """
        Load script value state history headers i.e. dates and times.
        :return: List of header strings.
        """
        return load_script_history_headers(HISTORY_PATH)

    def parameters_to_list(self):
        """
        Get parameters as list of dictionary objects.
        :return: Parameter list.
        """
        return [p.to_dict() for p in self.parameters]

    def execute_callable(self, callable_name):
        """
        Execute callable by name.
        :param callable_name: Name of callable.
        """

        for c in self.callables:
            if c[1] == callable_name:
                c[0]()
                break

    def update_nodes(self, root_node):
        """
        Update node hierarchy according to given dictionary hierarchy.
        :param root_node: Dictionary of root node that has updated values.
        """
        self.root_node.from_dict(root_node)

    def set_parameter(self, name, value):
        """
        Set script parameter.
        :param name: Name of parameter to set.
        :param value: Value string to set to paramter.
        """
        self.get_parameter(name).value = value

    def get_test_nodes(self):
        test_nodes = []

        for child in self.root_node.children:
            # Find the 'Tests' root node
            if isinstance(child, TestsNode):
                # The child.children is list of TestsNodes that group finger type tests together
                for grandchild in child.children:
                    # grandchild.children is a list of individual TestNodes
                    test_nodes = test_nodes + grandchild.children

        return test_nodes

    def read_tooltips_to_dict(self, file_name):
        """
        Reads tooltips to dict from a markdown file. The dict keys are the headers and the value is
        the text between the key header and the next header. The newline characters and all the lines
        starting with '[' are removed.
        :param file_name: name of the file (remember .md ending!)
        :return: dict of the tooltips
        """
        tooltips = {}
        folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'documentation')

        try:
            with open(os.path.join(folder_path, file_name), 'r') as file:
                header = None
                for line in file:
                    if line[0] == "#":
                        # the line includes a header
                        line = line.replace('#', '').replace('\n', '').replace('\r', '')
                        line = line.strip()
                        header = line
                        # Adding the header as a key to the dict
                        tooltips[header] = ''

                    elif header is not None: # Adding text to the dict
                        line = line.replace('\n', '').replace('\r', '')
                        if len(line) == 0: continue
                        # having '[' in the beginning of line indicates that it is not purely text
                        if line[0] == '[': continue
                        tooltips[header] += line + ' '

        except Exception as e:
            logger.warning("Failed to retrieve tooltip text from .md file: " + str(e))

        return tooltips


class UiProxyMultiprocess:
    """
    Proxy class for UI object that is used in multiprocess scheme.
    In this scheme script runs in separate Python process and calls to UI are
    done via Pipe connection object.

    From script's point of view, calling UI via this proxy object has the
    the effect as calling the UI object methods directly in singleprocess scheme.
    """

    def __init__(self, conn):
        self.conn = conn

    def _call_ui(self, method_name, *args):
        self.conn.send((method_name, args))

    def __getattr__(self, name):
        """
        Override attribute getter to redirect UI method calls via Pipe connection.
        :param name: Name of UI method to call.
        :return: Function object that is proxy for the UI method.
        """
        return lambda *args: self._call_ui(name, *args)


class PipeLogHandler(logging.Handler):
    """
    Log handler that passes log record to UI process to be shown in application console.
    """

    def __init__(self, ui):
        logging.Handler.__init__(self)
        self.ui = ui

    def emit(self, record):
        try:
            self.ui.sys_log(record)
        except:
            self.handleError(record)


def run_multiprocess(conn):
    """
    In multiprocess scheme, UI calls this function after launching Python process for the script.
    The script Python process then creates Context object and interacts with UI via Pipe connection.
    This is in contrast to singleprocess scheme, where UI directly imports this Python module and
    creates Context object in the UI process.
    :param conn: Pipe connection object provided by UI for scripts to interact with the UI.
    """

    # Create UI proxy that script uses to communicate to UI.
    ui = UiProxyMultiprocess(conn)

    # Add log handler to pass script logs to UI process.
    root = logging.getLogger()
    root.addHandler(PipeLogHandler(ui))

    # Change level to affect which messages are shown in UI console.
    root.setLevel(logging.DEBUG)

    # Create script context.
    context = Context(ui)

    # Receive messages from UI via Pipe connection and execute corresponding context methods.
    while True:
        msg = conn.recv()

        method_name = msg[0]
        args = msg[1]

        # 'exit' is special message and signals that script process should terminate.
        if method_name == 'exit':
            ui.exit()
            break

        method = getattr(context, method_name)
        method(*args)
