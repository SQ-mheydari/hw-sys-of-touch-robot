import os
from .Node import *
from scriptpath import get_script_root_directory
from TPPTcommon.script_config import get_config_value
import importlib
import copy


class DutNode(Node):
    """
    Node that represents DUT.
    Defines some DUT properties such as resolution and  measurement driver.
    """

    def __init__(self, name, tnt_dut, drivers, context):
        super().__init__(name)

        self.tnt_dut = tnt_dut

        self.display_enabled = True

        self.context = context

        # Creating a list of items in the drivers dict
        driver_list = []
        if drivers is not None:
            for driver_dict in drivers:
                driver_list.append(driver_dict["driver"].driver_name)
            # Drivers should be displayed always in alphabetical order
            driver_list.sort(key=str.lower)

        # Selecting the first in the list to be active default driver
        if len(driver_list) > 0:
            self.controls.driver = driver_list[0]
        else:
            self.controls.driver = "No drivers found!"
            driver_list = ["No drivers found!"]

        self.controls.info['driver'] = {'label': 'Driver', 'items': driver_list,
                                        'tooltip': self.context.tooltips['Driver']}

        # Add controls defined by the driver.
        for driver_dict in drivers:
            driver = driver_dict["driver"]

            if not hasattr(driver, "controls"):
                continue

            for control in driver.controls:
                if hasattr(self.controls, control["name"]):
                    raise Exception("Conflicting control '{}' in driver {}.".format(control["name"], driver.driver_name))

                setattr(self.controls, control["name"], control["default_value"])

                # Set info and force control visibility according to selected driver.
                info = copy.deepcopy(control["info"])
                info["visibility_control"] = "driver"
                info["visibility_value"] = driver.driver_name
                self.controls.info[control["name"]] = info

        self.controls.fetch_resolution = True
        self.controls.info['fetch_resolution'] = {'label': 'Fetch device resolution automatically',
                                                  'tooltip': self.context.tooltips['Fetch resolution']}

        self.controls.dut_resolution = [800, 600]
        self.controls.info['dut_resolution'] = {'label': 'DUT resolution [x;y, p.c.]', "type": "double_number",
                                                'visibility_control': 'fetch_resolution',
                                                'visibility_value': False,
                                                "min": 1, "step": 1, 'tooltip': self.context.tooltips['Dut resolution']}

        self.controls.flip_x = False
        self.controls.info['flip_x'] = {'label': 'Flip X coordinates', 'tooltip': self.context.tooltips['Flip x']}

        self.controls.flip_y = False
        self.controls.info['flip_y'] = {'label': 'Flip Y coordinates', 'tooltip': self.context.tooltips['Flip y']}

        self.controls.flip_x_and_y = False

        # Rotate by 90 deg and flip other coordinate.
        self.controls.info['flip_x_and_y'] = {'label': '(X,Y) --> (Y,X)',
                                              'tooltip': self.context.tooltips['Flip x and y']}

    @property
    def resolution(self):
        return self.controls.dut_resolution

    def panel_to_target(self, x, y, dut_width, dut_height):
        """
        Calculate new position of the point in the SVG in case of possible flipping.
        :param x: X-coordinate of point in pixels.
        :param y: Y-coordinate of point in pixels.
        :returns: Transformed X and Y in pixels and in mm.
        """
        dut_setup = self.controls
        resolution = self.resolution
        if dut_setup.flip_x_and_y:
            # Temp values to store the original x and y values that are used when transforming the points.
            temp_x = x
            temp_y = y

            # When x and y are switched the coordinates need to be transformed to the SVG's coordinates where
            # the positive x-axis goes to left and positive y-axis goes down.
            if dut_setup.flip_y:
                y = resolution[1] - temp_x
            else:
                y = temp_x
            if dut_setup.flip_x:
                x = resolution[0] - temp_y
            else:
                x = temp_y
        else:
            if dut_setup.flip_x:
                x = resolution[0] - x
            if dut_setup.flip_y:
                y = resolution[1] - y

        # Calculate mm to measured X and Y-coordinates
        x_mm = x * dut_width / resolution[0]
        y_mm = y * dut_height / resolution[1]


        return x, y, x_mm, y_mm


class DutsNode(Node):
    """
    Node that hosts DUT nodes as children and keeps track of current robot DUT.
    """

    def __init__(self, context):
        super().__init__('Duts')

        self.active_dut = None
        self.active_dut_node = None
        self.context = context
        # We have to use list for drivers to keep the order the same always
        self.available_drivers = []
        self.list_drivers()

    def list_drivers(self):
        '''
        Create a list of dicts of all the available DUT drivers based on files that are found in TPPTcommon/Measurement
        :return: list of dicts that contain classes for tap measurement and continuous measurement and the driver
        instance
        '''
        # Going through all the files in the directory TPPTcommon/Measurement
        for file in os.listdir(os.path.join(get_script_root_directory(), "TPPTcommon", "Measurement")):
            file_name_split = os.fsencode(file).decode('utf-8').split('.')

            # Check if the file could theoretically be a driver
            if len(file_name_split) != 2 or file_name_split[1] != "py":
                continue

            # Check if module can be imported and contains Driver class (only files with
            # drivers should go through this step)
            try:
                module_full_path = "TPPTcommon.Measurement.{}".format(file_name_split[0])
                driver_module = importlib.import_module(module_full_path)
                driver = driver_module.Driver
            except:
                continue

            # At this point we can be sure we are working with a driver, so we can add it to the list
            try:
                driver_instance = driver()
                # Checking if Dummy driver should be added to the list or not.
                if driver_instance.driver_name == "Dummy" and not get_config_value("enable_dummy", False):
                    continue
                self.available_drivers.append({"tap_measurement": driver_module.TapMeasurement,
                                               "continuous_measurement": driver_module.ContinuousMeasurement,
                                               "driver": driver_instance})
                self.context.html("Found DUT driver with name: {}".format(driver_instance.driver_name))
            except Exception as e:
                self.context.html_warning("Couldn't initialized driver from file {}: {}".format(os.fsencode(file).decode,
                                          str(e)))

        if len(self.available_drivers) == 0:
            self.context.html_warning("No DUT drivers found", "orange")

    def create_duts(self):
        """
        Create controls for enabling DUTs for tests and for setting their properties.
        """

        # Get DUT definitions from server.
        try:
            duts = self.context.tnt.duts()

            for dut in duts:

                dut.robot = self.context.robot
        except:
            self.context.html_color("No connection to TnT server. Please start TnT server and reload the script", "red")
            raise Stop("No connection to TnT server. Please start TnT server and reload the script")

        for dut in duts:
            # DUT named "OF" is special and not listed in GUI.
            # This is a device that is used to calibrate latency test.
            if dut.name == "OF":
                continue

            dut_node = DutNode(dut.name, dut, self.available_drivers, self.context)
            dut_node.enabled = False
            self.add_child(dut_node)

            # Indicators showing DUT sizes
            # setattr(self.indicators, dut.name + "_dutDimensions", str(round(dut.width, 2)) + ";" + str(round(dut.height, 2)))
            # self.indicators.label(dut.name + "_dutDimensions", dut.name + " dimensions [x;y, mm]")

    def initialize(self, dut_node):
        """
        Set active DUT to be used by test cases.
        Makes required DUT initializations.
        :param dut_node: DUT node to set.
        """
        dut = dut_node.tnt_dut
        self.active_dut_node = dut_node

        # Set active DUT state.
        self.active_dut = dut

        # Initialize driver
        driver_dict = next((x for x in self.available_drivers if x['driver'].driver_name == self.active_driver), None)
        driver = driver_dict['driver']
        driver.init_at_test_start(active_dut=dut_node)
        
        if dut_node.controls.fetch_resolution:
            res = driver.get_device_resolution(dut_node)
            dut_node.controls.dut_resolution = res
        else:
            res = dut_node.resolution

        self.context.create_dut_visualization(*res)

    def check_duts(self):
        """
        Check that at least one DUT is enabled.
        """

        for dut in self.children:
            if dut.enabled:
                return True

        self.context.html_color("No DUTs selected!", color="red")

        return False

    @property
    def active_driver(self):
        """
        The active driver name
        """
        return self.active_dut_node.controls.driver

    @property
    def active_driver_object(self):
        """
        The active driver Driver() object
        """
        for driver in self.available_drivers:
            if driver["driver"].driver_name == self.active_driver:
                return driver["driver"]

    @property
    def active_driver_tap_meas(self):
        """
        The tap measurement class of the active driver
        """
        for driver in self.available_drivers:
            if driver["driver"].driver_name == self.active_driver:
                return driver["tap_measurement"]

    @property
    def active_driver_continuous_meas(self):
        """
        The continuous measurement class of the active driver
        """
        for driver in self.available_drivers:
            if driver["driver"].driver_name == self.active_driver:
                return driver["continuous_measurement"]
