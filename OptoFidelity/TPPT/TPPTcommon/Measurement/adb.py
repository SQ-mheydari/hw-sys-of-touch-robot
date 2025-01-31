import logging
import struct
import subprocess
import threading
import time
import re

# Base.py exists in TPPT/TPPTcommon/Measurement/
from TPPTcommon.Measurement.Base import *


# Version number of this driver.
__version__ = "0.3.0"

log = logging.getLogger(__name__)

# Path to adb.exe. You should add the location of adb.exe to system path variable and it would be found.
# If this is not feasible or preferred for some reason, you can modify ADB_PATH, e.g., ADB_PATH = "C:\\Android\\adb.exe"
ADB_PATH = "adb"
# Touch event type codes used in the rest of the system
ACTION_TOUCH_DOWN = 0
ACTION_LIFT_OFF = 1
ACTION_MOVE = 2

"""
Information and samples of adb getevent outputs from a smart phone that this driver works with

Links to Android website:
- Specification of the events at https://source.android.com/devices/input/touch-devices
- See also https://source.android.com/devices/input/getevent

adb exec-out evtest /dev/input/event3
Input driver version is 1.0.1
Input device ID: bus 0x18 vendor 0xdead product 0xbeef version 0x28bb
Input device name: "device"
Supported events:
  Event type 0 (EV_SYN)
  Event type 1 (EV_KEY)
  Event type 3 (EV_ABS)
    Event code 47 (ABS_MT_SLOT)
      Value      0
      Min        0
      Max       15
    Event code 48 (ABS_MT_TOUCH_MAJOR)
      Value      0
      Min        0
      Max      255
    Event code 50 (ABS_MT_WIDTH_MAJOR)
      Value      0
      Min        0
      Max      255
    Event code 53 (ABS_MT_POSITION_X)
      Value      0
      Min        0
      Max      480
    Event code 54 (ABS_MT_POSITION_Y)
      Value      0
      Min        0
      Max      960
    Event code 57 (ABS_MT_TRACKING_ID)
      Value      0
      Min        0
      Max      255
Properties:
  Property type 1 (INPUT_PROP_DIRECT)
Testing ... (interrupt to exit)
Event: time 1633561619.1633561619, type 3 (EV_ABS), code 57 (ABS_MT_TRACKING_ID), value 0
Event: time 1633561619.1633561619, type 3 (EV_ABS), code 53 (ABS_MT_POSITION_X), value 239
Event: time 1633561619.1633561619, type 3 (EV_ABS), code 54 (ABS_MT_POSITION_Y), value 600
Event: time 1633561619.1633561619, type 3 (EV_ABS), code 48 (ABS_MT_TOUCH_MAJOR), value 25
Event: time 1633561619.1633561619, type 3 (EV_ABS), code 50 (ABS_MT_WIDTH_MAJOR), value 25
Event: time 1633561619.1633561619, -------------- SYN_REPORT ------------
"""


class Driver(DriverBase):
    def __init__(self, **kwargs):
        """
        This function is called already when the "Load Script" button is pressed.
        """
        super().__init__()

        self.driver_name = "adb"

        self.adb = None

        devices = self.get_devices()
        default_device = devices[0] if devices else ""

        self.controls = [dict(name="device", default_value=default_device,
                              info=dict(label="ADB device", tooltip="Which ADB device connected to the PC to use.",
                                        items=devices)),
                         dict(name="input_dev", default_value="event0",
                              info=dict(label="Input device", tooltip="Which device under /dev/input/ is used.")),
                         dict(name="command", default_value="shell",
                              info=dict(label="Command", tooltip="Which ADB command to use.",
                                        items=["shell", "exec_out"])),
                         dict(name="program", default_value="evtest",
                              info=dict(label="Program", tooltip="Program used to get input events.",
                                        items=["evtest", "getevent"]))
        ]

    def get_devices(self):
        """
        Get list of ADB device names connected to the PC.
        """
        devices = []

        path = [ADB_PATH, "devices"]
        result = subprocess.run(path, capture_output=True)

        for line in result.stdout.decode("ascii").splitlines():
            if line == "List of devices attached":
                continue

            if line:
                devices.append(line.split("\t")[0])

        return devices

    def init_at_test_start(self, active_dut, **kwargs):
        """
        This function is called when the "Run Test" button is pressed.
        """
        width = active_dut.controls.dut_resolution[0]
        height = active_dut.controls.dut_resolution[1]

        self.adb = Adb(width, height, active_dut.controls.device, active_dut.controls.command,
                       active_dut.controls.program, active_dut.controls.input_dev)
        self.adb.start_process()

    def close_at_test_finish(self, **kwargs):
        """
        This function is called when the "Stop" button is pressed when test is running.
        """
        self.adb.stop_process()

    def get_device_resolution(self, dut_node):
        # Not possible to get proper value.
        raise Exception("ADB driver does not support getting device resolution.")


class TapMeasurement(TapMeasurementBase):
    """
    Tap measurement.
    """

    def __init__(self, indicators, point, driver: Driver):
        super().__init__(indicators, point)
        self._adb = driver.adb

    def _start(self):
        # Clear any previous events in the buffer.
        self._adb.clear_event_buffer()

    def _end(self):
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            time.sleep(0.01)

            results = self._adb.get_touch_events()

            # Get the first event.
            if results:
                self.results = results[0]
                break

        self._update_tap_coordinate_indicators()


class ContinuousMeasurement(ContinuousMeasurementBase):
    """
    Continuous measurement.
    """

    def __init__(self, indicators, line, driver):
        super().__init__(indicators, line)
        self._adb = driver.adb
        self.event = threading.Event()

    def _start(self):
        # Clear any previous events in the buffer.
        self._adb.clear_event_buffer()

    def _end(self):
        self.event.set()

    def _read_results(self):
        # Wait until event is set.
        # Need to collect touch events also while waiting for the event because e.g.
        # jitter test is performing certain event filtering during the gesture.
        while not self.event.is_set():
            results = self._adb.get_touch_events()

            if results:
                self.results += results
                self._adb.clear_event_buffer()

            time.sleep(0.01)

        start_time = time.time()

        # Get events from buffer until timeout. Timeout used is in case there is delay in
        # event transfer.
        while time.time() - start_time < self.timeout:
            results = self._adb.get_touch_events()

            if results:
                self.results += results
                self._adb.clear_event_buffer()

            time.sleep(0.01)


class TouchEvent:
    """
    A structure to describe a single touch event.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.has_changed = False
        self.x = None
        self.y = None
        self.pressure = None
        self.action = None
        self.tracking_id = None
        self.finger_id = None

    def all_have_values(self):
        """
        Checks if all the object variables have values (except has_changed). If value is lacking
        it might indicate that there is an issue with initialisation of the slot data
        :return: True if all the variables have values, False if they don't
        """
        # The DUT might not have (but can have) pressure field so we need give it a value
        # if there is none to avoid issues with legacy code
        if self.pressure is None: self.pressure = 0

        if self.x is not None and self.y is not None and self.action is not None \
                and self.tracking_id is not None and self.finger_id is not None:
            return True
        else:
            return False

    @staticmethod
    def create_touch_event(touchevent, timestamp):
        '''
        Formats data from touchevent data container to the legacy format of the system
        :param touchevent: instance of TouchEvent, "data container"
        :param timestamp: we give timestamp separately so that we don't need to update it all the
        time to the data container. This works because the timestamp is given in the beginning of all the lines
        :return: formatted list
        '''
        # Generate a python list with the following elements to comply with the data formats that has been used:
        # 0: (468.4131,1017.48047,0.50390625,0,0,508350234,0,0.0,0.0,0.0)
        # 1: 'OK'
        # 2: ''
        try:
            if touchevent.all_have_values():
                touch_event = [
                    (touchevent.x, touchevent.y, touchevent.pressure, touchevent.finger_id,
                     0, timestamp, touchevent.action, 0.0, 0.0, 0.0), "OK", ""]

                return touch_event
            else:
                log.error("Adb driver create_touch_event: Touch event missing data. Not sending data")
                return None
        except:
            log.error(
                "Adb driver create_touch_event: Something wrong with the touch event object. Not sending data")
            return None


class Adb:
    """
    Class for managing touch event collection via ADB.
    """

    def __init__(self, display_width, display_height, device, command, program, event_id, process_path=None):
        """
        Constructor.
        """
        # Process path can be used to run custom application instead of ADB for testing purposes.
        self._process_path = process_path

        # The name of the ADB device to use.
        self.device = device

        # The ADB command to use when calling evtest.
        self.command = command

        # The program used to read input events.
        self.program = program

        # The event ID we are tracking with adb.
        self._event_id = event_id

        # Display settings. These are needed to convert touch panel coordinates to pixel coordinates.
        self._display_width = display_width
        self._display_height = display_height

        # Temporary log buffer where log data is collected as it is received.
        self._touch_event_buffer_tmp = []

        # Thread for touch event collection.
        self._touch_event_thread = None

        # Process for touch event collection. This is run in the touch event thread.
        self._touch_event_process = None

        # List of available touch events for tools. It contains touchevent instances per slot id. The system
        # reuses old values with same slot id (if not changed), so this cannot be emptied between measurements.
        self._slot_data_cache = {}

        # Ensuring finger ids are not reused, this is reset for every recording.
        self._next_finger_id = None

        # All the values are connected to current slot id and the slot id is not given unless it changes.
        self._current_slot_id = None

        # Bookkeeping of which slot ids are active.
        self._active_slot_ids = set()

        # We need to know the previous event to handle SLOT case correctly.
        self._previous_event = None

        # Is touch event collection initialized? The first lines received via ADB + evtest contain information
        # that is needed to parse the touch events that follow.
        self._initialized = False

        # Min and max values for ABS_MT_POSITIONS (multitouch) or ABS_X and ABS_Y (stylus), used for calculating the
        # correct coordinates.
        self._min_x = None
        self._max_x = None
        self._min_y = None
        self._max_y = None

        # Is the device a multitouch device, this is determined in the initialization phase from the available event
        # types. See section Touch Device Classification: https://source.android.com/devices/input/touch-devices
        self._multitouch = False

    def parse_event(self, line: str):
        """
        Parses one line that is received from dut via adb.
        :param line: Line parsed from response.
        :return: List of touch events that have changed between SYN_REPORT events.
        """
        touch_events = []

        if len(line) == 0:
            return touch_events

        if self.program == "evtest":
            timestamp, event, value = parse_evtest_event_string(line)
        elif self.program == "getevent":
            timestamp, event, value = parse_getevent_event_string(line)
        else:
            raise NotImplementedError

        timestamp = str(timestamp * 1000)  # seconds -> milliseconds

        if len(self._active_slot_ids) == 0:
            # There are no active slot_ids so the new touch will
            # get slot 0 by default without "ABS_MT_SLOT" field
            self._current_slot_id = 0
            self._active_slot_ids.add(self._current_slot_id)

        if self._current_slot_id not in self._slot_data_cache:
            # there is no data yet for the specific slot
            # creating a placeholder in the tool tracking list
            self._slot_data_cache[self._current_slot_id] = TouchEvent()

        if event == "ABS_MT_TRACKING_ID":
            # ABS_MT_TRACKING_ID  reports the tracking id of the tool. However, we have our own finger_id we track
            # and SLOT is used to cache the events, so we use tracking id to denote touch downs and lift offs.
            # If tracking id is given non-negative value, it means that a new device has touched to screen
            # value -1 means lift off

            if value != -1:  # there is a new tool touching the screen
                # Setting the new values for current slot_id
                self._slot_data_cache[self._current_slot_id].finger_id = self._next_finger_id
                self._next_finger_id += 1
                self._slot_data_cache[self._current_slot_id].action = ACTION_TOUCH_DOWN
                self._slot_data_cache[self._current_slot_id].tracking_id = value

            else:  # value == -1 -> finger has gotten up
                assert value == -1
                self._slot_data_cache[self._current_slot_id].action = ACTION_LIFT_OFF
                # The touch event is ready and will be passed forward
                self._active_slot_ids.remove(self._current_slot_id)

        elif event == "BTN_TOUCH":
            if not self._multitouch:
                if value == 1:
                    self._slot_data_cache[self._current_slot_id].finger_id = 0
                    self._slot_data_cache[self._current_slot_id].action = ACTION_TOUCH_DOWN
                    self._slot_data_cache[self._current_slot_id].tracking_id = 0
                elif value == 0:
                    self._slot_data_cache[self._current_slot_id].action = ACTION_LIFT_OFF
                    self._active_slot_ids.remove(self._current_slot_id)

        elif event == "ABS_MT_SLOT":
            # ABS_MT_SLOT is used to separate different tools touching the screen (MT = multitouch)
            # The data is cached per slot id and is reused even if the tool has changed. The cached data
            # is emptied only during reboot.

            # SLOT might be the very first field we get if already during the first timestamp there are two
            # tools touching the screen and in that case we need to do things differently
            if value not in self._slot_data_cache:
                self._current_slot_id = value
                self._slot_data_cache[self._current_slot_id] = TouchEvent()

            # It is possible that we get data only from one of the active slots for many timestamps.
            # In that case, we need to set the SLOT.has_changed flag here if the slot data has changed between
            # SYN_REPORT and SLOT
            if self._previous_event != "SYN_REPORT":
                self._slot_data_cache[self._current_slot_id].has_changed = True

            # Always when we get the slot id information, we are going the get data connected to the id
            self._current_slot_id = value
            self._slot_data_cache[self._current_slot_id].has_changed = True
            self._active_slot_ids.add(value)

        if event == "ABS_MT_POSITION_X" or event == "ABS_X":
            # From https://source.android.com/devices/input/touch-devices:
            #     displayX = (x - minX) * displayWidth / (maxX - minX + 1)
            x_pixels = (value - self._min_x) * self._display_width / (self._max_x - self._min_x + 1)

            self._slot_data_cache[self._current_slot_id].x = x_pixels

        elif event == "ABS_MT_POSITION_Y" or event == "ABS_Y":
            # From https://source.android.com/devices/input/touch-devices:
            #     displayY = (y - minY) * displayHeight / (maxY - minY + 1)
            y_pixels = (value - self._min_y) * self._display_height / (self._max_y - self._min_y + 1)

            self._slot_data_cache[self._current_slot_id].y = y_pixels

        elif event == "ABS_MT_PRESSURE":
            # Store pressure value as decimal value
            pressure = value
            self._slot_data_cache[self._current_slot_id].pressure = pressure

        elif event == "SYN_REPORT":
            # SYN_REPORT indicates that all the data for current timestamp is given

            # If we only have something to report from one of the slots for many timestamps
            # in a row, we need to set the slot_data.has_changed flag here to send the correct data
            self._slot_data_cache[self._current_slot_id].has_changed = True

            # Send all the data for the slots that have changed during current timestamp and
            # take the slot_data.has_changed flags away. It is also the best to set the action to
            # ACTION_MOVE here so that touch down and lift off occur only once.
            for slot_data in self._slot_data_cache.values():
                if slot_data.has_changed:
                    touch_event = TouchEvent.create_touch_event(slot_data, timestamp)

                    if touch_event is not None:
                        touch_events.append(touch_event)

                    slot_data.has_changed = False
                    slot_data.action = ACTION_MOVE

        self._previous_event = event

        return touch_events

    def _run_process(self, exe):
        """
        Run the ADB subprocess and yield response strings.
        :param exe: Description of the executable.
        """
        p = subprocess.Popen(exe, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log.debug("Subprocess (PID={}) started for command: {}".format(p.pid, exe))

        self._touch_event_process = p

        try:
            # p.poll returns None if the process is still running so we can use it
            # to stop reading lines after the process is finished.
            running = None
            while running is None:
                running = p.poll()  # This blocks until subprocess has something to return
                line = p.stdout.readline()
                # TODO: Handle empty data somehow by maybe quiting after 5 empty lines etc.
                yield line
        except ValueError as e:
            log.debug("Subprocess (PID={}) closed for command: {}".format(p.pid, exe))

    def _touch_event_process_run(self):
        """
        Run touch event process, handle initialization and collect touch events to buffer.
        """
        try:
            # Collect process response lines at initialization phase.
            init_lines = []

            if self._process_path is None:
                if self.program == "evtest":
                    path = [ADB_PATH, "-s", self.device, self.command, self.program, "/dev/input/" + self._event_id]
                elif self.program == "getevent":
                    self._initialize_getevent()
                    path = [ADB_PATH, "-s", self.device, self.command, self.program, "-lt", "/dev/input/" + self._event_id]
                else:
                    raise NotImplementedError
            else:
                path = self._process_path

            for s in self._run_process(path):
                s = s.decode("ascii")

                # If already initialized, parse events from process responses.
                if self._initialized:
                    touch_data = self.parse_event(s)

                    for data_set in touch_data:
                        self._touch_event_buffer_tmp.append(data_set)
                else:
                    # If not yet initialized, collect process responses until "Testing" is found indicating
                    # that all init lines have been collected and touch events are reported next.
                    if s.startswith("Testing"):
                        self._initialize_evtest(init_lines)
                    else:
                        init_lines.append(s)
        except Exception:
            # Handle all exceptions and log them because exceptions are not propagated to the main thread.
            log.exception("Error in handling touch events.")

    def _initialize_getevent(self):
        """
        Initialize data collection by parsing minimum and maximum coordinate values from the output of calling getevent
        with the -p flag.
        """
        path = [ADB_PATH, "-s", self.device, self.command, self.program, "-lp", "/dev/input/" + self._event_id]
        init_lines = [s.decode("ascii") for s in self._run_process(path)]

        self._min_x, self._max_x, self._min_y, self._max_y, self._multitouch = parse_getevent_init_lines(init_lines)

        log.info("Initialized ADB getevent (min x: {}, max x: {}, min y: {}, max y: {}.".
                 format(self._min_x, self._max_x, self._min_y, self._max_y))

        self._initialized = True

    def _initialize_evtest(self, init_lines):
        """
        Initialize data collection by parsing minimum and maximum coordinate values from lines
        printed by the process right after execution.
        :param init_lines: Lines of strings containing init data.
        """
        self._min_x, self._max_x, self._min_y, self._max_y, self._multitouch = parse_evtest_init_lines(init_lines)

        log.info("Initialized ADB evtest (min x: {}, max x: {}, min y: {}, max y: {}.".
                 format(self._min_x, self._max_x, self._min_y, self._max_y))

        self._initialized = True

    def start_process(self):
        """
        Start collection of touch events.
        The process should be explicitly stopped by calling stop_process() after test case is complete.
        """
        self._touch_event_buffer_tmp = []
        # finger_ids start from zero for each recording
        self._next_finger_id = 0

        if self._touch_event_thread is None:
            self._touch_event_thread = threading.Thread(target=self._touch_event_process_run)
            log.debug("Starting touch event thread name={}".format(self._touch_event_thread.name))
            self._touch_event_thread.start()
            log.debug("Started succesfully touch event thread name={}".format(self._touch_event_thread.name))

        # Since we are doing touch event process in different thread,
        # we need to check if it is running before continuing
        while self._touch_event_process is None:
            time.sleep(0.5)

    def get_touch_events(self):
        """
        Get touch events from the buffer.
        :return: List of events in TPPT list format.
        """
        buffer = self._touch_event_buffer_tmp.copy()

        return buffer

    def clear_event_buffer(self):
        """
        Clear the event buffer. This should be called before running the gesture.
        """
        self._touch_event_buffer_tmp.clear()

    def stop_process(self):
        """
        Stops the ADB process.
        """
        log.debug("Stop triggered for adb.exe processes.")

        # We have to kill both processes before communicate because communicate would get stuck
        # because stdout PIPE is not finished and communicate waits for that

        if self._touch_event_process is not None:
            log.debug("Killing touch event process.")
            self._touch_event_process.kill()

            self._touch_event_process.communicate()
            self._touch_event_process = None
            log.debug("Killed touch event process.")

        if self._touch_event_thread is not None:
            log.debug("Joining touch event thread.")
            self._touch_event_thread.join()
            self._touch_event_thread = None
            log.debug("Joined touch event thread.")


def parse_evtest_event_string(s: str):
    """
    Parse information from evtest event string.
    :param s: Event string.
    :return: timestamp, event_type, value.
    """
    if not s.startswith("Event"):
        return ""

    parts = s.split(",")

    timestamp = re.search(r"\d+\.\d+", parts[0]).group()
    timestamp = float(timestamp)

    if "SYN_REPORT" in parts[1]:
        return timestamp, "SYN_REPORT", 0
    else:
        event_type = re.search(r"\(.+\)", parts[2]).group()
        event_type = event_type[1:-1]  # Remove ()

        value = re.search(r"value [+-]*\d+", parts[3]).group()
        value = value.split()[1]

        return timestamp, event_type, int(value)


def parse_evtest_init_lines(init_lines: list):
    """
    Parse minimum and maximum touch coordinate values from init lines.
    :param init_lines: List of strings.
    :return: min_x, max_x, min_y, max_y, multitouch.
    """
    def parse_value(s):
        return int(s.split()[-1].strip())

    min_x = None
    max_x = None
    min_y = None
    max_y = None
    multitouch = False

    for i, line in enumerate(init_lines):
        if "ABS_MT_POSITION_X" in line or "ABS_X" in line:
            min_x = parse_value(init_lines[i + 2])
            max_x = parse_value(init_lines[i + 3])
        elif "ABS_MT_POSITION_Y" in line or "ABS_Y" in line:
            min_y = parse_value(init_lines[i + 2])
            max_y = parse_value(init_lines[i + 3])

        if "ABS_MT_POSITION_X" in line:
            multitouch = True

    return min_x, max_x, min_y, max_y, multitouch


def parse_getevent_event_string(s: str):
    """
    Parse information from getevent event string.
    :param s: Event string.
    :return: timestamp, event_type, value.
    """
    parts = s.split()

    timestamp = float(parts[1][:-1])  # timestamp in seconds
    event = parts[3]
    value = parts[4]

    if event.startswith("BTN"):
        # BTN_TOUCH uses values UP and DOWN, these correspond to 0 and 1.
        value = ["UP", "DOWN"].index(value)
    else:
        # Convert hexadecimal string into a signed integer.
        value = struct.unpack('>i', bytes.fromhex(value))[0]

    return timestamp, event, value


def parse_getevent_init_lines(init_lines: list):
    """
    Parse minimum and maximum touch coordinate values from init lines.
    :param init_lines: List of strings.
    :return: min_x, max_x, min_y, max_y, multitouch.
    """
    min_x = None
    max_x = None
    min_y = None
    max_y = None
    multitouch = False

    for line in init_lines:
        if "ABS_MT_POSITION_X" in line or "ABS_X" in line:
            min_x = int(re.search(r"min ([+-]*\d+)", line).group(1))
            max_x = int(re.search(r"max ([+-]*\d+)", line).group(1))
        elif "ABS_MT_POSITION_Y" in line or "ABS_Y" in line:
            min_y = int(re.search(r"min ([+-]*\d+)", line).group(1))
            max_y = int(re.search(r"max ([+-]*\d+)", line).group(1))

        if "ABS_MT_POSITION_X" in line:
            multitouch = True

    return min_x, max_x, min_y, max_y, multitouch
