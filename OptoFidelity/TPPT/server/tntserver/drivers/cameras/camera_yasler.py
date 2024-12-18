import numpy as np
import threading
import yasler
from tntserver.drivers.cameras.camera import Camera, sort_parameters

import logging
log = logging.getLogger(__name__)


def api_locker(func):
    """
    Function decorator for ensuring camera resource is accessed from one source at a time.
    :param func: Function to decorate.
    :return: Decorated function.
    """
    def wrapper(*args, **kwargs):
        with args[0].api_lock:  # first argument is reference to caller object instance
            # Log decorated function name and arguments here if needed.
            output = func(*args, **kwargs)

        return output
    return wrapper


class Camera_Yasler(Camera):

    def __init__(self, camtype, inter_packet_delay=None, packet_size=None, **kwargs):

        self.camtype = camtype.lower()
        name = kwargs.get('name', None)
        serial_number = kwargs.get('serial_number', None)
        ip_address = kwargs.get('ip_address', None)
        max_queue_size = kwargs.get('max_queue_size', 1)

        # In order to successfully write parameters the order has to be correct for certain interdependent ones.
        self.param_prioritization = ["binning_horizontal", "binning_vertical", "image_width",
                                     "image_height", "offset_x", "offset_y"]

        # Don't allow infinite queue size
        if max_queue_size < 1:
            raise Exception("Invalid queue size {}. Value must be at least 1.".format(max_queue_size))

        # initialize class and open connection to camera
        if self.camtype == 'usb':
            if serial_number is None:
                log.warning("Camera argument 'serial_number' not specified. Camera is selected randomly.")

            self._yasler = Yasler_USB(name=name, serial_number=serial_number, max_queue_size=max_queue_size)
        elif self.camtype == 'gige':
            if ip_address is None:
                log.warning("Camera argument 'ip_address' not specified. Camera is selected randomly.")

            self._yasler = Yasler_GigE(name=name, ip_address=ip_address, serial_number=serial_number, max_queue_size=max_queue_size)
        try:
            self.open()
        except Exception as e:
            log.error("Unable to open connection to camera. Please check USB / ethernet connection. "
                      "Low level error message: " + str(e))

        # if given, set GigE transport layer parameters here, because they are usually only set once during init
        if inter_packet_delay is not None:
            self._yasler.inter_packet_delay = inter_packet_delay
        if packet_size is not None:
            self._yasler.packet_size = packet_size

        self._exposure = None
        self._exposure_max = None
        self._exposure_min = None
        self._gain = None

        self.api_lock = threading.Lock()
        super().__init__()
        self.exposure = 0.005  # set a reasonable exposure value after superclass init

        # set binning mode to additive
        if 'binning_horizontal_mode' in kwargs:
            self._yasler.cam.binning_horizontal_mode = kwargs['binning_horizontal_mode']

        if 'binning_vertical_mode' in kwargs:
            self._yasler.cam.binning_vertical_mode = kwargs['binning_vertical_mode']

        # set pixel format if given
        if 'pixel_format' in kwargs:
            self._yasler.cam.pixel_format = kwargs['pixel_format']

    def open(self):
        if not self._camera_open:
            self._yasler.cam.open()

    def close(self):
        """
        Generally, there is really no need to close the connection with the camera once initialized. In many legacy
        camera drivers close() is used to stop frame acquisition. This is because open() has been used to start the
        camera frame acquisition. With yasler, the user does not need to directly control the internal grabbing loop
        of the camera.
        :return: None.
        """
        pass

    def _cam_has_attr(self, name):
        """
        Yasler has a bug where PylonError is raised if
        attribute does not exist. This is a convenience method to
        check if attribute exists.
        :param name: Attribute name.
        :return: True if exists.
        """
        try:
            return hasattr(self._yasler.cam, name)
        except yasler.PylonError:
            # PylonError is considered here as "does not have the attribute".
            pass

        return False

    @api_locker
    def _set_parameters(self, params):
        """
        Set camera parameters.
        :param params: Parameter dictionary.
        :return: Nothing.
        """
        if not self._camera_open:
            raise Exception("Camera connection not open, unable to set parameters")

        params_list = sort_parameters(params, self.param_prioritization)

        errors = "" # Collecting all the errors in one message.
        for param in params_list:
            try:
                name, value = param[0], param[1]
                if hasattr(self._yasler, name):
                    setattr(self._yasler, name, value)
                elif self._cam_has_attr(name):
                    setattr(self._yasler.cam, name, value)
            except Exception as e:
                errors += "Failed to set parameter '{}' value to {} with error: {} \n".format(name, value, str(e))

        if len(errors) != 0:
            log.error("Errors in writing parameter values: {}".format(errors))
            raise Exception(errors)

    def _get_parameters(self, params):
        """
        Get given set of parameters from camera. Input dict indicates which parameters are retrieved.
        :param params: Parameters to retrieve as list of strings.
        :return: Dictionary of requested parameters and their values.
        """
        if not self._camera_open:
            raise Exception("Camera connection not open, unable to get parameters")
        ret_params = {}

        for param in params:
            # Set None as default value in case parameter is not found.
            ret_params[param] = None

            try:
                if hasattr(self._yasler, param):
                    ret_params[param] = getattr(self._yasler, param)
                elif self._cam_has_attr(param):
                    ret_params[param] = getattr(self._yasler.cam, param)
            except Exception as e:
                log.error("Failed to get parameter {}".format(param))
                raise

        return ret_params

    @api_locker
    def _capture_image(self):
        """
        Capture one frame.
        :return: Captured frame as NumPy array.
        """

        # If grabbing is on due to continuous capture take image from capture queue.
        if self._yasler.cam.is_grabbing():
            image = self._yasler.cam.wait_for_image()
        else:
            image = self._yasler.cam.take_still(trigger_timeout=1000)

        # TODO: Handle other image formats than uint8.
        return np.array(image, dtype=np.uint8, copy=False)

    @api_locker
    def start_continuous(self, callback=None, trigger_type='SW'):
        """
        Start continous frame capture based on either camera's internal timer or external HW trigger
        :param callback: function to call for each captured image. if None, uses yasler's default callback
        :param trigger_type: either 'SW', 'HW' or 'HWBurst'.
        :return:
        """
        self._yasler.cam.start_continuous(callback=callback, trigger_type=trigger_type)

    @api_locker
    def get_image_from_buffer(self, timeout=1):
        """
        Get image from yasler internal buffer
        - Image acquisition must be started elsewhere (this function will not trigger the camera for you)
        - Can be used e.g. with: start_continuous(callback=None, trigger_type=None)
        in this case there is a separate thread that is constantly filling the buffer with fresh images

        :param timeout: Time to wait for image to appear in buffer. After timeout queue.Empty is raised.
        :return: Captured frame as numpy array.
        """

        # TODO: Handle other image formats than uint8.
        return np.array(self._yasler.cam.wait_for_image(timeout=timeout), dtype=np.uint8, copy=False)

    @api_locker
    def stop_continuous(self):
        """
        Stop continuous grabbing and reset capture callback to use the internal image queue.
        """
        self._yasler.cam.stop_continuous()

    @api_locker
    def stop_grabbing(self):
        """
        Stop continuous grabbing but leave the capture callback as it was set in start_continuous().
        """
        self._yasler.cam.stop_grabbing()

    @api_locker
    def burst(self, n=1, trigger_type='SW'):
        return self._yasler.cam.burst(amount=n, trigger_type=trigger_type)

    def activate_chunkdata(self):
        self._set_parameters(params={'chunk_mode_active': True})

    def deactivate_chunkdata(self):
        self._set_parameters(params={'chunk_mode_active': False})

    @api_locker
    def set_countervalue_chunkdata(self, enabled=True):
        self._yasler.set_countervalue_chunkdata(enabled)

    def set_exposure_chunkdata(self, enabled=True):
        try:
            # values must be set sequentially
            self._set_parameters(params={'chunk_selector': 'ExposureTime'})
            self._set_parameters(params={'chunk_enable': enabled})
        except yasler.BaslerError:
            log.warning("Unable to enable exposure time chunk data for captured images.")

    @api_locker
    def set_burst_frame_count(self, amount=1):
        self._yasler.set_burst_frame_count(amount)

    @property
    def _camera_open(self):
        return self._yasler.cam.is_open()

    @property
    def exposure(self):
        if self._camera_open:
            self._exposure = self._yasler.exposure / 1e6  # microseconds to seconds
        return self._exposure

    @exposure.setter
    def exposure(self, value):
        exposure_us = value * 1000000.0  # seconds to microseconds
        self._exposure = value
        if self._camera_open:
            self._yasler.exposure = exposure_us

    @property
    def exposure_max(self):
        if self._camera_open:
            self._exposure_max = self._yasler.exposure_max / 1e6  # microseconds to seconds
        return self._exposure_max

    @property
    def exposure_min(self):
        if self._camera_open:
            self._exposure_min = self._yasler.exposure_min / 1e6  # microseconds to seconds
        return self._exposure_min

    @property
    def gain(self):
        if self._camera_open:
            self._gain = self._yasler.gain
        return self._gain

    @gain.setter
    def gain(self, value):
        self._gain = value
        if self._camera_open:
            self._yasler.gain = value

    @property
    def resolution(self):
        return self._yasler.cam.image_width, self._yasler.cam.image_height

    @resolution.setter
    def resolution(self, width=None, height=None):
        # this sets the camera image acquisition area directly onto the Basler camera
        if width is not None:
            self._yasler.cam.image_width = width
        if height is not None:
            self._yasler.cam.image_height = height

    @property
    def sensor_size(self):
        w, h = self.resolution
        pw, ph = self.pixel_size
        return w * pw, h * ph

    @property
    def pixel_size(self):
        # TODO: can we read this from device info or similar?
        return 0.0048, 0.0048

    @property
    def tickfrequency(self):
        return self._yasler.tickfrequency

    @property
    def frame_rate(self):
        return self._yasler.frame_rate

    @property
    def resulting_frame_rate(self):
        return self._yasler.resulting_frame_rate

    @property
    def readout_time(self):
        return self._yasler.readout_time

    @api_locker
    def set_fast_readout_mode(self):
        self._yasler.set_fast_readout_mode()

    @api_locker
    def set_normal_readout_mode(self):
        self._yasler.set_normal_readout_mode()

    @api_locker
    def set_mode(self, mode):
        if mode == 'HW':
            self._yasler.cam.set_mode(yasler.AcquireMode.HWTriggered)
        elif mode == 'HWBurst':
            self._yasler.cam.set_mode(yasler.AcquireMode.HWTriggeredBurst)
        else:
            self._yasler.cam.set_mode(yasler.AcquireMode.SWTriggered)


class Yasler_USB:

    def __init__(self, **kwargs):

        # replace possible None arguments with empty strings and convert others to strings
        for arg, val in kwargs.items():
            kwargs[arg] = '' if val is None else str(val)
        self.cam = yasler.Basler(type=yasler.CameraType.USB, **kwargs)
        self._gain = 0
        self._tickfrequency = 1e9  # tick frequency of timestamp clock

    def set_fast_readout_mode(self):
        self.cam.sensor_readout_mode = 'Fast'

    def set_normal_readout_mode(self):
        self.cam.sensor_readout_mode = 'Normal'

    def set_burst_frame_count(self, amount):
        self.cam.burst_frame_count = amount

    def set_countervalue_chunkdata(self, enabled):
        # values must be set sequentially
        self.cam.chunk_selector = 'CounterValue'
        self.cam.chunk_enable = enabled

    @property
    def exposure(self):
        return self.cam.exposure_time

    @exposure.setter
    def exposure(self, value):
        self.cam.exposure_time = max(self.cam.exposure_time_min, value)

    @property
    def exposure_max(self):
        return self.cam.exposure_time_max

    @property
    def exposure_min(self):
        return self.cam.exposure_time_min

    @property
    def gain(self):
        return self._gain

    @gain.setter
    def gain(self, value):
        self._gain = value

    @property
    def tickfrequency(self):
        return self._tickfrequency

    @property
    def resulting_frame_rate(self):
        return self.cam.resulting_frame_rate

    @property
    def frame_rate(self):
        return self.cam.frame_rate

    @frame_rate.setter
    def frame_rate(self, value):
        self.cam.frame_rate = value

    @property
    def readout_time(self):
        return self.cam.readout_time

    @property
    def inter_packet_delay(self):
        return 0

    @inter_packet_delay.setter
    def inter_packet_delay(self, value):
        pass

    @property
    def packet_size(self):
        return 0

    @packet_size.setter
    def packet_size(self, value):
        pass


class Yasler_GigE:

    def __init__(self, **kwargs):
        # TODO: Why is this done? It's confusing and was hiding a bug related to "ip" argument.
        # replace possible None arguments with empty strings and convert others to strings
        for arg, val in kwargs.items():
            kwargs[arg] = '' if val is None else str(val)
        self.cam = yasler.Basler(type=yasler.CameraType.GigE, **kwargs)
        self._tickfrequency = 125e6  # tick frequency of timestamp clock

    @property
    def exposure(self):
        return self.cam.exposure_time_abs

    @exposure.setter
    def exposure(self, value):
        self.cam.exposure_time_abs = max(self.cam.exposure_time_abs_min, value)

    @property
    def exposure_max(self):
        return self.cam.exposure_time_abs_max

    @property
    def exposure_min(self):
        return self.cam.exposure_time_abs_min

    @property
    def gain(self):
        # The fact that gain actually calls gain_raw is legacy and should be eventually fixed
        # See Jira issue TOUCH5705-1046 for reference
        return self.cam.gain_raw - self.cam.gain_raw_min

    @gain.setter
    def gain(self, value):
        # The fact that gain actually calls gain_raw is legacy and should be eventually fixed
        # See Jira issue TOUCH5705-1046 for reference
        self.cam.gain_raw = self.cam.gain_raw_min + int(value)  # use actual minimum gain value from camera

    @property
    def tickfrequency(self):
        return self._tickfrequency

    @property
    def frame_rate(self):
        return self.cam.frame_rate_abs

    @frame_rate.setter
    def frame_rate(self, value):
        self.cam.frame_rate_abs = value

    @property
    def resulting_frame_rate(self):
        return self.cam.resulting_frame_rate_abs

    @property
    def readout_time(self):
        return self.cam.readout_time_abs

    @property
    def inter_packet_delay(self):
        return self.cam.inter_packet_delay

    @inter_packet_delay.setter
    def inter_packet_delay(self, value):
        self.cam.inter_packet_delay = value

    @property
    def packet_size(self):
        return self.cam.packet_size

    @packet_size.setter
    def packet_size(self, value):
        self.cam.packet_size = value

    def set_fast_readout_mode(self):
        pass

    def set_normal_readout_mode(self):
        pass

    def set_burst_frame_count(self, amount):
        self.cam.frame_count = amount

    def set_countervalue_chunkdata(self, enabled):

        # values must be set sequentially
        self.cam.chunk_selector = 'Framecounter'
        self.cam.chunk_enable = enabled


