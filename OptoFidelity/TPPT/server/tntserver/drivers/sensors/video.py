# -*- coding: utf-8 -*-
"""
OptoFidelity Video Multimeter API
Property of OptoFidelity

Adopted from VMM serial command Python wrapper
git@git.optofidelity.net:videomultimeter/vmm-serial-command-python-wrapper.git
"""
import datetime
import logging
import serial
import threading
import time

from functools import wraps

log = logging.getLogger(__name__)


def setup_logging():
    """
    Intended use for this method is for when running this script standalone
    :return: logger
    """
    import logging.handlers

    log_format = '%(asctime)s %(levelname)7s: %(threadName)10s %(name)10s -> %(funcName)20s %(lineno)5d - %(message)s'
    logging.basicConfig(level=logging.NOTSET, format=log_format)
    handler = logging.handlers.RotatingFileHandler('video_multimeter.log', maxBytes=10240000, backupCount=5)
    formatter = logging.Formatter(fmt=log_format)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    log = logging.getLogger(__name__)
    return log


def update_watchdog_timeout(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        args[0]._last_API_call_time = time.time()
        if args[0].verbose_debug_logging:
            log.debug("Update self._last_API_call_time to {}".format(args[0]._last_API_call_time))
        return f(*args, **kwargs)
    return wrapper


class VideoSensorSimulator:
    """
    Simulation class for VideoSensor, that mimics the serial communication protocol. No real functionality is
    implemented
    """

    def __init__(self):

        # Define some commands and their responses
        self._commands = {'GETSN\r': 'OK VM123456789 \n\r\x00',
                          'HOME\r': 'OK \n\r\x00',
                          'GETSTATE\r': 'OK bl_period:1234 enc_pos:567 \n\r\x00',
                          'OPEN': 'OK \n\r\x00',
                          'EXIT\r': 'OK \n\r\x00',
                          'SETCONFIG': 'OK \n\r\x00',
                          'GETCONFIG': 'OK \n\r\x00',
                          'GETAPPS\r': 'OK BACKLIGHT_INFO TRIGGER_CAMERA_ON_FRAMES \n\r\x00',
                          'GETBAT\r': 'OK 100 \n\r\x00',
                          'RESETENC\r': 'OK \n\r\x00'}

        self._params = {'synccamera': {'enc_threshold': 'OK 1234 \n\r\x00'}}

        self._hello_sent = False
        self._command_echo = None
        self._command_ret_value = None

    def flushInput(self):
        pass

    def flushOutput(self):
        pass

    def read_all(self):
        pass

    @staticmethod
    def response_generator(response_string):
        for ch in response_string:
            yield ch

    def write(self, data):
        cmd = data.decode().split(" ")[0]

        # Always echo back the received command first (except of course on the first command since reset)
        self._command_echo = self.response_generator(data.decode() + '\x00')

        if cmd in self._commands.keys():
            if not self._hello_sent:
                self._command_echo = self.response_generator('OptoFidelity Video Multimeter\n\r\x00')
                self._hello_sent = True

            self._command_ret_value = self.response_generator(self._commands[cmd])

            # Some extra functionality for reading config parameters
            if cmd == 'GETCONFIG':
                params = data.decode().split(" ")[1:]
                section = params[0]
                param_name = params[1][:-1]
                self._command_ret_value = \
                    self.response_generator('OK ' + self._params[section][param_name] + '     \x00')  # why the spaces?

            # Some extra functionality for writing config parameters
            elif cmd == 'SETCONFIG':
                params = data.decode().split(" ")[1:]
                section = params[0]
                param_name = params[1]
                param_value = params[2][:-1]
                if section not in self._params:
                    self._params[section] = {}
                if param_name not in self._params[section]:
                    self._params[section][param_name] = ''

                self._params[section][param_name] = param_value

        else:
            # Command was unknown
            self._command_ret_value = self.response_generator('E1 UNKNOWN COMMAND ' + cmd + '\n\r\x00')

    def read(self, size=1):
        # TODO: support reading more than one character byte at a time
        try:
            # First return characters from the command echo string. If it is exhausted, return characters from the
            # return value string
            return next(self._command_echo).encode("ascii")
        except StopIteration:
            try:
                return next(self._command_ret_value).encode("ascii")
            except StopIteration:
                # Return value is already sent, so signal an error state with an empty character
                return b''


class VideoSensor:
    """
    Class for Video Multimeter device.
    """
    def __init__(self, port='COM1', watchdog_enabled=True, verbose_debug_logging=False, simulation=False):
        # shared attributes
        self.apps = []
        self.verbose_debug_logging = verbose_debug_logging
        # Communication parameters for Video sensor
        self.vm_serial = None
        self.vm_serial_baud_rate = 115200
        self.port = port    # for reconnection purposes
        self.serial_timeout = 2
        self.serial_port_lock = threading.Lock()
        self.connect_vm_serial(port=port, simulation=simulation)
        # watchdog related
        self.watchdog_timeout = 10
        self.petting_the_dog_interval = 3  # resetting watchdog timer interval
        self._last_API_call_time = None
        self.keep_alive_thread_event = threading.Event()
        if watchdog_enabled:
            self.set_watchdog_timeout(timeout=self.watchdog_timeout)
            self.keep_alive_thread = threading.Thread(target=self.petting_the_dog_thread, daemon=True)
            self.keep_alive_thread_event.set()
            self.keep_alive_thread.start()  # Thread will run as long as even is set
            log.info("Watchdog for video sensor has been enabled with timeout of {} seconds.".format(self.watchdog_timeout))

    def close(self):
        """
        Stop petting_the_dog_thread and close serial connection
        :return: None
        """
        if self.keep_alive_thread_event.is_set():
            self.keep_alive_thread_event.clear()
        self.vm_serial.close()
        log.info("Closed video sensor connection.")

    def petting_the_dog_thread(self):
        """
        Pet the dog in defined intervals
        :return:
        """
        log.info('Petting THE DOG thread initialized.')
        while self.keep_alive_thread_event.is_set():
            if time.time() >= self._last_API_call_time + self.petting_the_dog_interval:
                self.pet_the_dog()
            time.sleep(1)
        log.info('Petting THE DOG thread exited at {}.'.format(datetime.datetime.now()))

    @update_watchdog_timeout
    def pet_the_dog(self):
        """
        Only purpose of this method is to reset watchdog timer, any API call should be fine
        but less resource intensive calls should be favoured.
        :return: None
        """
        self.write_to_vm('GETTIME\r', verbose_logging=self.verbose_debug_logging)

    def reconnect(self, timeout=10):
        """
        Trying to reconnect for couple of seconds. Method relies on video multimeter connecting
        to the same port that it was connected originally.
        #TODO: implement checking other COM ports for video multimeter
        :return: True if reconnected successfully, False otherwise
        """
        log.info("Trying to reconnect to video sensor for {} seconds.".format(timeout))
        t0 = time.time()
        while time.time() < t0 + timeout:
            try:
                self.connect_vm_serial(port=self.port)
                log.info("Reconnection was successful.")
                return True
            except Exception as e:
                log.exception(e)
                log.debug("Got exception while trying to reconnect.")
                time.sleep(1)   #TODO: Not sure if it's needed here, just a wild guess
        return False

    @update_watchdog_timeout
    def write_to_vm(self, data, verbose_logging=True):
        """
        Write a command in ASCII format to the device.
        :param data: Command to send as string.
        :return: Response from device to the sent command.
        """
        if verbose_logging:
            log.debug("Writing to videosensor: {}".format(data))
        try:
            with self.serial_port_lock:
                self.vm_serial.write(data.encode())
        except Exception as e:
            log.exception(e)
            if self.reconnect():
                return self.write_to_vm(data=data)
            else:
                raise CommunicationError("Writing data to video sensor failed. Please check that the video sensor USB "
                                         "cable is connected properly. Low level error message: " + str(e))
        # Read echoed message back
        echo_response = self.read_from_vm(verbose_logging=verbose_logging)
        # the very first command will always contain a hello string, regardless of command
        if echo_response == "OptoFidelity Video Multimeter\n\r\x00":
            self.read_from_vm(verbose_logging=verbose_logging)
            # send command again to get the real response
            with self.serial_port_lock:
                self.vm_serial.write(data.encode())
            self.read_from_vm(verbose_logging=verbose_logging)
        # Read response for command
        response = self.read_from_vm(verbose_logging=verbose_logging)
        if "OK" not in response:
            log.error("Received error {} for command input {}".format(response[:-6], data))
        return response

    def read_from_vm(self, end_character=b'\x00', verbose_logging=True):
        """
        Read response data from the device.
        :param end_character: End character that signifies end of transmission.
        :return: Received data decoded to a character string.
        """
        data = ""
        while True:
            try:
                with self.serial_port_lock:
                    character = self.vm_serial.read(size=1)
            except Exception as e:
                raise CommunicationError("Reading data from video sensor failed. Please check that the video sensor "
                                         "USB cable is connected properly. Low level error message: " + str(e))
            data += character.decode("ascii")
            # print(character)
            # Stop reading once the specific end character appears
            if character == end_character:
                break
            elif character == b'':
                raise CommunicationError("Reading data from video sensor failed. Please check that the video sensor "
                                         "USB cable is connected properly")
        end = min(data.find('\r'), data.find('\n'))

        # log only responses that don't contain the real name of the device
        if 'Multimeter' not in data and len(data) > 4 and verbose_logging:
            log.debug("Response from video sensor: {}".format(data[:end]))
        return data

    def connect_vm_serial(self, port, simulation=False):
        """
        Open connection to the device.
        :param port: Communications port as string, e.g. 'COM1'.
        :param simulation: If True, simulate serial port connection
        """
        try:
            if simulation:
                self.vm_serial = VideoSensorSimulator()
            else:
                self.vm_serial = serial.Serial(port, self.vm_serial_baud_rate,
                                               timeout=self.serial_timeout)
            self.vm_serial.flushInput()
            self.vm_serial.read_all()
            self.vm_serial.flushOutput()
            data = self.write_to_vm("GETSN\r")
            sn = data.split(" ")[1]
        except Exception as e:
            raise CommunicationError("Reading data from video sensor failed. Please check that the USB cable is "
                                     "connected properly. Low level error message: " + str(e))

        if sn is not None:
            log.debug("Connected to video sensor serial no: {}".format(sn[:-4]))
            self.write_to_vm("HOME\r")
        log.info("Connection to video sensor at port {} succeeded.".format(port))

    def disconnect_vm_serial(self):
        self.vm_serial.close()

    def go_to_home_page(self):
        return self.write_to_vm("HOME\r")

    def get_apps(self):
        """
        Get list of available applications.
        :return: Available of applications as string.
        """
        data = self.write_to_vm("GETAPPS\r")
        self.apps = data.split(" ")[1:]
        return self.apps

    def get_state(self):
        """
        Get state for encoder pulse count and backlight period.
        :return: Backlight period and encoder position as string, e.g. "OK bl_period:1234 enc_pos:567"
        """
        return self.write_to_vm("GETSTATE\r")

    def get_battery_status(self):
        """
        Get battery charge status in percentage.
        :return:
        """
        # Return value is "OK xxx \r\n" where xxx is battery level in percentage (0-100)
        status = self.write_to_vm("GETBAT\r").split(" ")
        return status[1]

    def get_charger_status(self):
        return self.write_to_vm("GETCHARG\r")

    def get_config_param(self, ini_section, param_name):
        """
        Read config parameter from internal ini-file.
        :param ini_section: Section of ini-file to access.
        :param param_name: Name within accessed section.
        :return: Parameter value.
        """
        response = self.write_to_vm(("GETCONFIG {} {}\r".format(ini_section, param_name)))[3:-6]
        return response

    def get_backlight_period_us(self, retry=False):
        """
        Read backlight scan period.
        :return: Detected backlight scan period in microseconds.
        """
        response = self.write_to_vm("GETSTATE\r")
        try:
            # return string will be e.g. "OK bl_period:1234 enc_pos:567"
            period_str = response.split(" ")[1]
            period = float(period_str[10:])
        except ValueError as e:
            # handle E1 UNKNOWN_COMMAND response
            # this happens when camera trigger application isn't in foreground
            log.exception(e)
            if "E1 UNKNOWN_COMMAND" in response and not retry:
                log.debug("Got response {}, opening backlight info and camera trigger applications then trying again.")
                self.go_to_home_page()
                self.open_backlight_info_app()
                self.open_camera_trigger_app()
                return self.get_backlight_period_us(retry=True)
        return period

    def get_encoder_value(self):
        """
        Read encoder pulse count.
        :return: Encoder pulse count.
        """
        response = self.write_to_vm("GETSTATE\r")
        # return string will be e.g. "OK bl_period:1234 enc_pos:567"
        enc_value_str = response.split(" ")[2]
        value = int(enc_value_str[8:-4])
        return value

    def set_config_param(self, ini_section, param_name, value):
        """
        Write config parameter value to internal ini-file.
        :param ini_section: Section of ini-file to access.
        :param param_name: Name within accessed section.
        :param value: Parameter value to write.
        :return: Response to write operation.
        """
        return self.write_to_vm(("SETCONFIG {} {} {}\r".format(ini_section, param_name, value)))

    def open_camera_trigger_app(self):
        """
        Start application "Trigger camera of frames".
        :return: Device response.
        """
        return self.open_application("TRIGGER_CAMERA_ON_FRAMES")

    def open_backlight_info_app(self):
        """
        Start application "Backlight info".
        :return: Device response.
        """
        return self.open_application("BACKLIGHT_INFO")

    def open_application(self, application):
        """
        Open application.
        :param application: Name of application to start.
        :return: Device response to command.
        """
        data = self.write_to_vm("OPEN {}\r".format(application))
        return data

    def exit_application(self):
        """
        Close currently running application.
        :return: Device response to command.
        """
        return self.write_to_vm("EXIT\r")

    def reset_encoder_value(self):
        """
        Reset internal encoder pulse counter value to 0.
        :return: Device response to command.
        """
        return self.write_to_vm("RESETENC\r")

    def set_encoder_trigger_threshold(self, value):
        """
        Set camera sync pulse generation threshold to a specific encoder value.
        :param value: Threshold value in encoder counts.
        :return: None.
        """
        return self.set_config_param(ini_section='synccamera', param_name='enc_threshold', value=value)

    def get_encoder_trigger_threshold(self):
        """
        Read current encoder pulse count threshold value for camera sync pulse generation.
        :return: Threshold value.
        """
        return int(self.get_config_param(ini_section='synccamera', param_name='enc_threshold'))

    def set_trigger_backlight_rising(self):
        """
        Set camera sync pulse triggering to continuous pulse output in sync with backlight. Start pulse generation when
        encoder count rises over currently set threshold value.
        :return: None.
        """
        self.set_config_param(ini_section='synccamera', param_name='enc_edge_trigger', value=0)

    def set_trigger_backlight_falling(self):
        """
        Set camera sync pulse triggering to continuous pulse output in sync with backlight. Start pulse generation when
        encoder count falls below currently set threshold value.
        :return: None.
        """
        self.set_config_param(ini_section='synccamera', param_name='enc_edge_trigger', value=1)

    def set_trigger_touch_start(self):
        """
        Set camera sync pulse triggering to single pulse output without regard to backlight. Generate one pulse when
        finger touches the DUT or other surface. In practice, this means that encoder count decreases below
        threshold value.
        :return: None.
        """
        self.set_config_param(ini_section='synccamera', param_name='enc_edge_trigger', value=2)

    def set_trigger_touch_end(self):
        """
        Set camera sync pulse triggering to single pulse output without regard to backlight. Generate one pulse when
        finger releases up from the DUT or other surface. In practice, this means that encoder count increases above
        threshold value.
        :return: None.
        """
        self.set_config_param(ini_section='synccamera', param_name='enc_edge_trigger', value=3)

    def set_trigger_mode_frames(self):
        """
        Set camera sync pulse generation based on detected frame changes. (Not in use)
        :return: None.
        """
        self.set_config_param(ini_section='synccamera', param_name='type', value=0)

    def set_trigger_mode_backlight(self):
        """
        Set camera sync pulse generation based on backlight period. Encoder count is not used.
        :return: None.
        """
        self.set_config_param(ini_section='synccamera', param_name='type', value=1)

    def set_trigger_mode_backlight_encoder(self):
        """
        Set camera sync pulse generation based on backlight taking into acount also encoder trigger type and threshold
        settings.
        :return: None.
        """
        self.set_config_param(ini_section='synccamera', param_name='type', value=2)

    def stop_measurement(self):
        self.write_to_vm('STOPMEAS\r')

    def start_measurement(self):
        self.write_to_vm('STARTMEAS\r')

    def set_watchdog_timeout(self, timeout: int):
        """
        There is no disable watchdog method exposed through control API at the moment
        :param timeout: timeout in seconds after which CPU will be reset
        :return: response
        """
        return self.write_to_vm('WATCHDOG {:d}\r'.format(timeout))


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class CommunicationError(Error):
    def __init__(self, message):
        self.message = message


if __name__ == "__main__":
    # init
    setup_logging()
    v = VideoSensor(port='COM13', watchdog_enabled=True)

    v.go_to_home_page()
    v.open_backlight_info_app()
    v.open_camera_trigger_app()
    # init
    for _ in range(3):
        log.info("Backlight period {}".format(v.get_backlight_period_us()))

    # test external trigger
    for _ in range(2):
        v.stop_measurement()    # stop sending trigger signal from the previous
        v.set_trigger_mode_backlight_encoder()
        v.set_trigger_backlight_falling()
        v.reset_encoder_value()
        # At this point video multimeter shouldn't be sending trigger signal
        # Uncomment line below to pause execution and verify video multimeters behavior
        # input("Trigger finger and verify that trigger signal is being sent, press ENTER to continue")

    # Test reconnection
    # stop keep_alive_thread and wait for video sensor to reboot
    v.keep_alive_thread_event.clear()
    # watchdog timer is set to 10 seconds by default
    time.sleep(17)  # after reboot it takes about 6-7 seconds for video multimeter to boot-up
    log.info("At this point connection should be severed")
    # at this moment connection is severed, reset_encoder_value should go through after reconnection succeeds
    v.reset_encoder_value()
    v.get_state()
    time.sleep(1)
    v.close()
