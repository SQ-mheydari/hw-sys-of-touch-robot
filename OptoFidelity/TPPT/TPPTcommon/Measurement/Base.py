"""
Base classes for touch event handling.

Touch events are managed as following type of tuple:

    (
        [
            (x, y, sensitivity/pressure/force, finger_id, delay, timestamp, event/action/phase, azimuth, tilt),
            (x, y, sensitivity/pressure/force, finger_id, delay, timestamp, event/action/phase, azimuth, tilt),
            (x, y, sensitivity/pressure/force, finger_id, delay, timestamp, event/action/phase, azimuth, tilt)
        ],
        'OK',
        ''
    )

The first tuple item is a list of singular touch events each of which is a tuple of 9 items. In case of
multi-finger touch this list should contain touch events corresponding to the different fingers. In case of
single-finger this list usually contains only one element (unless panel erroneously detects a ghost finger too).
The second tuple item is success code which should be 'OK' or some error message. Only 'OK' events are stored
to measurement database for further analysis.
The third tuple item is a string reserved for custom use and can be left empty.

The singular touch event items are as follows:

    x: Touch x-coordinate in pixels
    y: Touch y-coordinate in pixels
    sensitivity/pressure/force: A numeric value corresponding to sensitivity/pressure/force if supported or 0 if not.
    finger_id: Unique touch index for each finger on multi-touch devices.
    delay: Usually 0.
    timestamp: Touch timestamp in milliseconds.
    event/action/phase: Touch event type. Depends on device vendor.
    azimuth: Touch azimuth angle in degrees.
    tilt: Touch tilt angle in degrees.

For Android device, the actions are defined as follows:

    ACTION_DOWN    0
    ACTION_UP      1
    ACTION_MOVE    2
    ACTION_CANCEL  3

See https://developer.android.com/reference/android/view/MotionEvent for more information.
"""
from threading import Thread


class DriverBase:
    """
    Base class for touch event driver.
    A Python file with subclass implementation is placed under

        TPPT/TPPTcommon/Measurement/

    it will then show up in the GUI for selection as driver for a specific DUT.
    """
    def __init__(self, **kwargs):
        """
        This function is called when the "Load Script" button is pressed in the GUI.
        Subclass can do some initialization at this stage if that is valid for the duration of
        multiple test runs.
        """
        # Name that is shown in the GUI.
        self.driver_name = ""

        # A list of control definitions that GUI can display under the driver.
        # Example: dict(name="port", default_value="COM1",
        #               info=dict(label="Serial port", tooltip="Which COM port to use.", items=["COM1", "COM2"])),
        # The control values can be accessed in methods below via active_dut object.
        self.controls = []

    def init_at_test_start(self, active_dut, **kwargs):
        """
        This function is called every time the DUT is changed before executing test cases.
        :param active_dut: Object representing the active DUT used in next tests.
        """

        # The control values set via GUI can be accessed like this:
        #     port = active_dut.controls.port
        # If "port" control was defined in init method.

        # DUT resolution set via GUI can be obtained like this:
        # width = active_dut.controls.dut_resolution[0]
        # height = active_dut.controls.dut_resolution[1]
        pass

    def close_at_test_finish(self, **kwargs):
        """
        This function is called when the "Stop" or "Finish" button is pressed in GUI.
        """
        pass

    def get_device_resolution(self, dut_node):
        """
        This method is called at test start if "Fetch resolution automatically" was checked for the DUT
        in the GUI.
        :param dut_node: DUT node object for current device.
        :returns: Device resolution as a list [x, y].
        """
        raise RuntimeError("Driver does not support fetching device resolution automatically.")


class TapMeasurementBase:
    """
    Base class for tap measurement context.
    Test cases make tap measurements based on methods defined here.
    """

    def __init__(self, indicators, point):
        # Indicators object that is used to communicate received touch event information to GUI.
        self.indicators = indicators

        # Point object representing the target tap location.
        # This is mostly used for passing simulated data to database.
        self.point = point

        # List of touch events (see top of the file for explanation). Usually tap-like tests only
        # take the first item from this list and it is typical that touch driver places the first reported event to
        # this list. So the results could be like:
        # self.results = [ ([x, y, pressure, finger_id, delay, timestamp, action, azimuth, tilt), 'OK', '')  ]
        self.results = None

        # Timeout in seconds that the touch handler should wait until the first event is obtained before stopping
        # data collection.
        self.timeout = 1.0

        # Thread to use for touch event handling.
        self.thread = Thread(target=self._thread_main)

    def start(self, timeout=6.0):
        """
        Start tap-like touch measurement.
        This is called by measurement script just before robot gesture is commanded. Touch event handling
        should happen in separate thread during robot gesture command.
        :param timeout: Timeout in seconds that the touch handler should wait until the first event is obtained
        before stopping data collection.
        """
        # Initialize members used in tap measurement.
        self.timeout = timeout
        self.results = []

        self._start()
        self.thread.start()

    def end(self):
        """
        End tap measurement.
        This is called by measurement script after robot gesture is finished.
        """
        self._end()
        self.thread.join()

    def _start(self):
        """
        Subclass can override this method to define some behavior before tap measurement starts.
        """
        pass

    def _end(self):
        """
        Subclass can override this method to define some behavior before tap measurement ends.
        """
        pass

    def _thread_main(self):
        """
        This method is called by the measurement thread.
        Reads tap measurement results and updates indicators.
        """
        self._read_results()
        self._update_tap_coordinate_indicators()

    def _read_results(self):
        """
        Subclass should override this method to implement retrieving the touch events from the device
        and placing the results in self.results. This method is called once from the thread that is launched at
        measurement start. This function should return only when sufficient amount of data has been collected.
        """
        pass

    def _update_tap_coordinate_indicators(self):
        """
        Pass result touch event coordinates to GUI indicators.
        """
        if self.results:
            self.indicators.X = self.results[0][0]
            self.indicators.Y = self.results[0][1]
        else:
            self.indicators.X = '-'
            self.indicators.Y = '-'


class ContinuousMeasurementBase:
    """
    Base class for continuous measurement for swipe-like tests.
    Test cases make continuous measurements during robot gestures.
    """

    def __init__(self, indicators, line):
        # Indicators object that is used to communicate received touch event information to GUI.
        self.indicators = indicators

        # Line object representing robot movement from start point to end point.
        # This is mostly used for passing simulated data to database.
        self.line = line

        # Timeout in seconds that is waited at most for the next event until stopping measurement.
        self.timeout = 0.5

        # The same as defined in TapMeasurementBase.
        self.results = None

        # Thread to use for touch event handling.
        self.thread = Thread(target=self._thread_main)

    def start(self, timeout=0.5):
        """
        Start continuous measurement in a separate thread.
        :param timeout: Timeout in seconds between consecutive events.
        """

        self.timeout = timeout
        self.results = []

        self._start()
        self.thread.start()

    def end(self):
        """
        End continuous measurement.
        This is called by measurement script after robot gesture is finished.
        """
        self._end()
        self.thread.join()

        # Show last measured point in UI.
        self._update_line_coordinate_indicators()

    def _start(self):
        """
        Subclass can override this method to define some behavior before continuous measurement starts.
        """
        pass

    def _end(self):
        """
        Subclass can override this method to define some behavior before continuous measurement ends.
        """
        pass

    def _thread_main(self):
        """
        This method is called by the measurement thread.
        Reads continuous measurement results and updates indicators.
        """
        self._read_results()
        self._update_line_coordinate_indicators()

    def _read_results(self):
        """
        Subclass should override this method to implement retrieving the touch events from the device
        and placing the results in self.results. This method is called once from the thread that is launched at
        measurement start. This function should return only when sufficient amount of data has been collected.
        """
        pass

    def _update_line_coordinate_indicators(self):
        """
        Pass result touch event coordinates to GUI indicators.
        """
        if self.results:
            self.indicators.X = self.results[-1][0][0]
            self.indicators.Y = self.results[-1][0][1]
        else:
            self.indicators.X = '-'
            self.indicators.Y = '-'

    def parse_data(self):
        """
        Get valid touch events from all recorded events.
        :return: List of events.
        """
        results = self.results
        touchlist = []

        if len(results) == 0:
            return touchlist

        for cline_data in results:
            if "OK" not in cline_data:
                continue

            for point in range(cline_data.index("OK")):  # Read all data points before "OK"
                if len(cline_data[point]) > 9:
                    touchlist.append([cline_data[point][0], cline_data[point][1],
                                      cline_data[point][2], cline_data[point][3],
                                      cline_data[point][4], cline_data[point][5],
                                      cline_data[point][6], cline_data[point][7],
                                      cline_data[point][8], cline_data[point][9]])
                else:
                    touchlist.append([cline_data[point][0], cline_data[point][1],
                                      cline_data[point][2], cline_data[point][3],
                                      cline_data[point][4], cline_data[point][5],
                                      cline_data[point][6], cline_data[point][7],
                                      cline_data[point][8]])

        return touchlist
