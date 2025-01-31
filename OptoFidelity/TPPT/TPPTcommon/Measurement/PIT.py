import ast
import json

from .Base import *
import os
import logging
from TPPTcommon.Measurement.Communication.pitwrapper import PITWrapper

logger = logging.getLogger(__name__)


class Driver(DriverBase):

    def __init__(self, **kwargs):
        """
        This function is called already when the "Load Script" button is pressed
        """
        super().__init__()

        self.driver_name = "PIT"
        self.active_dut_node = None
        self.pit = None
        self.pit_slot = None
        self.pit_index = None
        self.pit_drivers_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "PIT_Drivers")
        self.pit_connected = False
        self.pit_drivers_list = self.get_pit_drivers_list()
        self.device_resolution = None

        pit_drivers = self.pit_drivers_list if len(self.pit_drivers_list) > 0 else ["No driver found"]

        self.controls = [
            dict(name="pit_driver", default_value=pit_drivers[0],
                 info=dict(label="PIT driver", tooltip="Drivers for PIT.", items=pit_drivers)),
            dict(name="pit_slot", default_value=1,
                 info=dict(label="PIT slot", tooltip="Slot that the PIT is connected to."))
        ]

    def init_at_test_start(self, **kwargs):
        """
        This function is called every time the dut is changed.
        """
        self.active_dut_node = kwargs.get("active_dut")
        # Pit slot is the indexing visible to user (starts from 1)
        self.pit_slot = self.active_dut_node.controls.pit_slot
        # Pit index is the indexing used in low level (starts from 0)
        self.pit_index = self.pit_slot - 1
        if self.active_dut_node.controls.pit_driver == "PIT-USB":
            dut_handler_name = "PIT_USB"
            dut_handler_ip = '10.10.14.2'
        else:
            dut_handler_name = "PIT"
            dut_handler_ip = '10.10.10.2'

        if not self.pit_connected:
            logger.info("Accessing {} ...".format(dut_handler_name))
            self.pit = PITWrapper(host=dut_handler_ip, port=5001)
            self.pit_connected = True

        pit_driver = open(os.path.join(self.pit_drivers_path, (self.active_dut_node.controls.pit_driver))).read()
        self.pit.LoadDriver(pit_driver)

        # Select PIT slot
        self.pit.Multiplexer(self.pit_index)

        # Initialize current DUT
        logger.info("Initializing {} driver".format(dut_handler_name))

        try:
            res = self.pit.InitializePanel()
            try:
                parsed_result = res[0].replace('[', '').replace(']', '').split(', ')
                width = int(parsed_result[1])
                height = int(parsed_result[2])
                self.device_resolution = [width, height]
            except Exception as e:
                logger.warning("Could not get resolution from the driver. "
                               "Following exception happened: {}".format(str(e)))

        except Exception as e:
            logger.error("{} driver initialization failed: {}".format(dut_handler_name, str(e)))

    def close_at_test_finish(self, **kwargs):
        """
        This function is called when the "Stop" or "Finish" button is pressed.
        """
        pass

    def get_pit_drivers_list(self):
        """
        List all the PIT drivers found from the PIT_drivers folder
        :return: List of driver names
        """
        return os.listdir(self.pit_drivers_path)

    def get_device_resolution(self, dut_node):
        """
        Initializes PIT driver and gets resolution from pit.
        :param dut_node: DUT node for current device. This is not needed in the PIT driver.
        :returns: Device resolution as a list ([x, y])
        """
        logger.info(self.device_resolution)
        return self.device_resolution


class TapMeasurement(TapMeasurementBase):
    """
    Tap measurement from PIT box.
    """

    def __init__(self, indicators, point, driver):
        super(TapMeasurement, self).__init__(indicators, point)

        self.pit = driver.pit
        self.pit_index = driver.pit_index

    def _start(self):
        # Start CLine function with 8000ms timeout
        self.pit.CLine(8000)

    def _read_results(self):
        try:
            first = True
            for touch in self.pit.receive_data_generator():
                # Ignore other than actual touch events that are labelled with "OK".
                if "OK" not in touch:
                    continue

                # Take the first touch and read all the rest to throw them away to clear the buffer.
                # There are buffers at different layers and they won't otherwise get cleaned.
                if first:
                    self.results = touch
                    first = False
        except:
            # If no touches are detected, I2C timeout occurs and exception with error message is received.
            pass

    def _end(self):
        # Stop reading
        self.pit.CLineOff()
    

class ContinuousMeasurement(ContinuousMeasurementBase):
    """
    Continuous measurement from PIT box.
    """

    def __init__(self, indicators, line, driver):
        super(ContinuousMeasurement, self).__init__(indicators, line)

        self.pit = driver.pit

    def _start(self):
        # Start CLine function with 8000ms timeout
        self.pit.CLine(8000)

    def _read_results(self):
        for touch in self.pit.receive_data_generator():
            self.results.append(touch)

    def _end(self):
        # Stop reading
        self.pit.CLineOff()


class LatencyMeasurement(TapMeasurementBase):
    """
    Latency measurement from PIT box.
    """

    def __init__(self, indicators, point, driver):
        super(LatencyMeasurement, self).__init__(indicators, point)

        self.pit = driver.pit
        self.pit_index = driver.pit_index

    def _start(self):
        # Start CLine. Params:
        # 1: Cline timeout (ms)
        # 2: Finger interrupt timeout (ms)
        # 3: Wait finger interrupt
        self.pit.CLine(8000, 5000, True)

    def _read_results(self):
        try:
            first = True
            for touch in self.pit.receive_data_generator():
                # Ignore other than actual touch events that are labelled with "OK".
                if "OK" not in touch:
                    continue

                # Take the first touch and read all the rest to throw them away to clear the buffer.
                # There are buffers at different layers and they won't otherwise get cleaned.
                if first:
                    self.results = touch
                    first = False
        except:
            # If no touches are detected, I2C timeout occurs and exception with error message is received.
            pass

    def _end(self):
        # Stop reading
        self.pit.CLineOff()
