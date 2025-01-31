import logging
from .Base import *
import queue
import TPPTcommon.Measurement.Communication.devicesocket as devicesocket
from threading import Event
import time

logger = logging.getLogger(__name__)


class Driver(DriverBase):
    def __init__(self, **kwargs):
        """
        This function is called already when the "Load Script" button is pressed
        """
        super().__init__()

        self.driver_name = "TCP Socket"

        try:
            self.dsock = devicesocket.DeviceSocket()
            logger.info("Started TCP socket")
        except Exception as e:
            logger.warning("Failed to initialize TCP socket: {}".format(str(e)))

    def init_at_test_start(self, **kwargs):
        """
        This function is called every time the dut is changed.
        """
        pass

    def close_at_test_finish(self, **kwargs):
        """
        This function is called when the "Stop" or "Finish" button is pressed.
        """
        pass

    def get_device_resolution(self, dut_node):
        """
        Gets DUT resolution. No driver initalization needed
        :param dut_node: DUT node for current device.
        :returns: Device resolution as a list [x, y]
        """
        dut = dut_node.tnt_dut
        dut_info = dut.info()
        width = int(dut_info['display_resolution']['width'])
        height = int(dut_info['display_resolution']['height'])
        return [width, height]


class TapMeasurement(TapMeasurementBase):
    '''
    Tap measurement from device socket (TCP).
    '''

    def __init__(self, indicators, point, driver):
        super(TapMeasurement, self).__init__(indicators, point)

        self.dsock = driver.dsock

    def _start(self):
        # Clear queue before launching the measurement thread.
        self.dsock.clear_queue()

    def _end(self):
        # Get the first queued event from the device and store that as result. Returns empty list if timeout occurs.
        # This is called at the end of measurement when robot has completed the motion.
        self.results = self.dsock.ReturnP2PArray(timeout=self.timeout)
        self._update_tap_coordinate_indicators()


class ContinuousMeasurement(ContinuousMeasurementBase):
    '''
    Continuous measurement from device socket (TCP).
    '''

    def __init__(self, indicators, line, driver):
        super(ContinuousMeasurement, self).__init__(indicators, line)

        self.dsock = driver.dsock
        self.event = Event()

    def _start(self):
        # Clear queue before launching the measurement thread.
        self.dsock.clear_queue()

    def _get_touches(self, timeout):
        try:
            # Read events until timeout is exceeded
            for touch in self.dsock.CLine(timeout=timeout):
                if touch is not None:
                    self.results.append(touch)
        except queue.Empty:
            pass  # There was no event reported within timeout. This ends the measurement.

    def _read_results(self):
        # Read touches until event is set. This way touches are guaranteed to be collected during entire gesture.
        # Use fixed short timeout between touch queries. This value has no effect as touches are collected until
        # event is set.
        while not self.event.is_set():
            self._get_touches(0.01)

        # After event is set, get touch events until specified timeout.
        self._get_touches(self.timeout)

    def _end(self):
        # Set event to allow measurement thread to terminate.
        self.event.set()
