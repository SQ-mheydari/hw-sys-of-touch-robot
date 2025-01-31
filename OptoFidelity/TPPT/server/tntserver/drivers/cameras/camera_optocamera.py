from tntserver.drivers.cameras.camera import Camera, sort_parameters
from optofidelity.camera.core import Camera as OptoCamera, CameraFrame, CameraType, CaptureError
from typing import Optional, Union, Tuple, Callable, List
from queue import Queue
import numpy as np
import atexit

import logging
log = logging.getLogger(__name__)


class Camera_Optocamera(Camera):
    """
    Class to control camera through Optocamera with any backend.
    """
    def __init__(self,
                 camtype: str,  # gige or usb
                 inter_packet_delay: Optional[int] = None,
                 packet_size: Optional[int] = None,
                 exposure_time: float = 0.005,
                 pixel_size: Optional[float] = None,
                 output_format: str = 'mono',  # mono, rgb or bgr. Only affects output, not camera settings
                 timestamp_tick_frequency: int = 1e9,
                 **kwargs) -> None:
        self.camtype = camtype.lower()
        self._camera_open = False
        self._format = output_format
        self._timestamp_tick_frequency = timestamp_tick_frequency

        name = kwargs.get('name', None)
        serial_number = kwargs.get('serial_number', None)
        ip_address = kwargs.get('ip_address', None)

        # In order to successfully write parameters the order has to be correct for certain interdependent ones.
        self.param_prioritization = ["binning_horizontal", "binning_vertical", "image_width",
                                     "image_height", "offset_x", "offset_y"]

        camera_type = CameraType.Any

        if self.camtype == 'usb':
            if serial_number is None:
                log.warning("Camera argument 'serial_number' not specified. Camera is selected randomly.")
            camera_type = CameraType.USB

        elif self.camtype == 'gige':
            if ip_address is None:
                log.warning("Camera argument 'ip_address' not specified. Camera is selected randomly.")
            camera_type = CameraType.GigE

        cameras = list(OptoCamera.discover(camera_type=camera_type,
                                           ip_address=ip_address,
                                           name=name,
                                           serial_number=serial_number))
        if len(cameras) < 1:
            log.error("Zero cameras found with given criteria ( "
                      "camtype={}, ip_address={}, "
                      "name={}, serial_number={} )".format(camtype, ip_address, name, serial_number))

        elif len(cameras) > 1:
            log.warning("Multiple cameras found with given criteria, selecting the first one")

        self._camera = cameras[0]

        try:
            self.open()
        except Exception as e:
            log.error("Unable to open connection to camera. Please check USB / ethernet connection. "
                      "Low level error message: " + str(e))

        # if given, set GigE transport layer parameters here, because they are usually only set once during init
        if inter_packet_delay is not None:
            self._camera.inter_packet_delay = inter_packet_delay

        if packet_size is not None:
            self._camera.packet_size = packet_size

        super().__init__()
        if pixel_size is not None:
            self._pixel_size = (pixel_size, pixel_size)

        # super sets the exposure to zero. Set the actual initial value here
        self.exposure = exposure_time

        # Queue for default continuous capture scheme.
        max_queue_size = kwargs.get('max_queue_size', 1)
        self._frame_queue = Queue(maxsize=max_queue_size)

        # Callback for continuous capture.
        self._callback = None

        # Close camera on application exit.
        atexit.register(self.close)

    @property
    def exposure(self) -> float:
        """Exposure in seconds"""
        if self._camera_open:
            return self._camera.exposure_time.value
        else:
            # Tnt gt seems to use 0 as some sort of default value for exposure - see parent class init
            return 0.0

    @exposure.setter
    def exposure(self, value: float):
        # Lets just not do anything if the camera is open
        if self._camera_open:
            exposure = min(max(self.exposure_min, value), self.exposure_max)
            self._camera.exposure_time = exposure

    @property
    def exposure_max(self) -> Union[float, None]:
        if self._camera_open:
            return self._camera.exposure_time.max
        else:
            return 0.0

    @property
    def exposure_min(self) -> Union[float, None]:
        if self._camera_open:
            return self._camera.exposure_time.min
        else:
            return 0.0

    @property
    def gain(self) -> float:
        if self._camera_open:
            return self._camera.gain.value
        else:
            # Tnt gt seems to use 0 as some sort of default value for gain - see parent class init
            return 0.0

    @gain.setter
    def gain(self, value: float):
        if self._camera_open:
            self._camera.gain = value

    @property
    def resolution(self) -> Tuple[int, int]:
        """
        x, y resolution in pixels
        """
        return self._camera.image_width.value, self._camera.image_height.value

    @resolution.setter
    def resolution(self, width: Optional[int] = None, height: Optional[int] = None):
        if width is not None:
            self._camera.image_width = width
        if height is not None:
            self._camera.image_height = height

    @property
    def tickfrequency(self) -> int:
        return self._camera.timestamp_tick_frequency

    @property
    def frame_rate(self) -> float:
        """
        Framerate setting in fps
        """
        if self.camtype == 'gige':
            return self._camera.get_float_parameter('AcquisitionFrameRateAbs')
        elif self.camtype == 'usb':
            return self._camera.get_float_parameter('AcquisitionFrameRate')

    @frame_rate.setter
    def frame_rate(self, value: float):
        if self.camtype == 'gige':
            self._camera.set_float_parameter('AcquisitionFrameRateAbs', value)
        elif self.camtype == 'usb':
            self._camera.set_float_parameter('AcquisitionFrameRate', value)

    @property
    def resulting_frame_rate(self) -> float:
        """
        Actual framerate in fps
        """
        if self.camtype == 'gige':
            return self._camera.get_float_parameter('ResultingFrameRateAbs')
        elif self.camtype == 'usb':
            return self._camera.get_float_parameter('ResultingFrameRate')

    @property
    def readout_time(self) -> float:
        if self.camtype == 'gige':
            return self._camera.get_float_parameter('ReadoutTimeAbs')
        if self.camtype == 'usb':
            return self._camera.get_float_parameter('SensorReadoutTime')

    @property
    def inter_packet_delay(self) -> int:
        if self.camtype == 'gige':
            return self._camera.inter_packet_delay.value

    @inter_packet_delay.setter
    def inter_packet_delay(self, value: int):
        if self.camtype == 'gige':
            self._camera.inter_packet_delay = value

    @property
    def packet_size(self) -> int:
        if self.camtype == 'gige':
            return self._camera.packet_size.value

    @packet_size.setter
    def packet_size(self, value: int):
        if self.camtype == 'gige':
            self._camera.packet_size = value

    @property
    def binning_horizontal(self) -> int:
        return self._camera.binning_horizontal.value

    @binning_horizontal.setter
    def binning_horizontal(self, value: int):
        self._camera.binning_horizontal = value

    @property
    def binning_vertical(self) -> int:
        return self._camera.binning_vertical.value

    @binning_vertical.setter
    def binning_vertical(self, value: int):
        self._camera.binning_vertical = value

    @property
    def image_width(self) -> int:
        """Image width in pixels"""
        return self._camera.image_width.value

    @image_width.setter
    def image_width(self, value: int):
        self._camera.image_width = value

    @property
    def image_height(self) -> int:
        """Image height in pixels"""
        return self._camera.image_height.value

    @image_height.setter
    def image_height(self, value: int):
        self._camera.image_height = value

    @property
    def offset_x(self) -> int:
        return self._camera.x_offset.value

    @offset_x.setter
    def offset_x(self, value: int):
        self._camera.x_offset = value

    @property
    def offset_y(self) -> int:
        return self._camera.y_offset.value

    @offset_y.setter
    def offset_y(self, value: int):
        self._camera.y_offset = value

    @property
    def sensor_size(self) -> Tuple[float, float]:
        w, h = self.resolution
        pw, ph = self.pixel_size
        return w * pw, h * ph

    @property
    def pixel_size(self) -> Tuple[float, float]:
        return self._pixel_size

    def open(self):
        """
        Opens connection to camera. Already called by init so calling this after camera class init should be
        unnecessary.
        """
        if not self._camera_open:
            self._camera.open()
        #if hasattr(self._camera, 'timestamp_tick_frequency') and self._camera.timestamp_tick_frequency is None:
        #    self._camera.timestamp_tick_frequency = self._timestamp_tick_frequency
        self._camera_open = True

    def close(self):
        """
        Closes connection to camera. It is not required to call this during program shutdown
        """
        if self._camera_open:
            self._camera.close()

        self._camera_open = False

    def _default_callback(self, cam: OptoCamera, frame: CameraFrame, error: CaptureError) -> bool:
        """
        Default capture callback that puts captured image to queue.
        """

        if frame is None and error is not None:
            log.error("Error when capturing frame: {}".format(str(error)))

            return True

        try:
            img = self.frame_to_array(self._format, frame)

            self._frame_queue.put(img, timeout=1.0)
        except Exception as e:
            log.error("Error when capturing frame: {}".format(str(e)))

        return True

    def start_continuous(self, callback: Optional[Callable[[np.ndarray, Exception], None]] = None,
                         trigger_type: str = 'SW'):
        """
        Start continuous capture with given trigger type and send image to callback function.
        :param callback: Callback function to call with image from camera
        :param trigger_type: trigger type to use in capturing: SW, HW or HWBurst
        """
        # Only set the callback if it is not None to allow pause/resume functionality
        # (related to stop_grabbing method)
        self._callback = callback if callback is not None else self._default_callback

        self._camera.start_acquisition(self._callback)

    def get_image_from_buffer(self, timeout: float = 1.0) -> np.array:
        """
        Get single image from currently ongoing acquisition process.
        Waits for the next frame to be ready.
        :param timeout: time in seconds after which queue.Empty is raised.
        :return: Image as numpy array.
        """
        return self._frame_queue.get(timeout=timeout)

    def stop_continuous(self):
        """
        Stop continuous grabbing and reset capture callback.
        """
        self._camera.stop_acquisition()
        self._callback = None

    def stop_grabbing(self):
        """
        Stop continuous grabbing but leave the capture callback as it was set in start_continuous().
        """
        self._camera.stop_acquisition()

    @staticmethod
    def frame_to_array(out_format: str, frame: CameraFrame):
        """
        Convert from OptoCameraFrame to numpy image
        """
        if out_format == 'mono':
            return frame.mono()
        elif out_format == 'rgb':
            return frame.rgb()
        elif out_format == 'bgr':
            return frame.bgr()
        else:
            raise TypeError('Unsupported image output format {}'.format(out_format))

    def _capture_image(self):
        """
        Capture one frame.
        :return: Captured frame as NumPy array.
        """
        # If there is callback for continuous capture, stop grabbing while capturing image.
        if self._callback is not None:
            self.stop_grabbing()

        frame = self._camera.capture_frame()

        # Restart acquisition.
        if self._callback is not None:
            self._camera.start_acquisition(self._callback)

        return Camera_Optocamera.frame_to_array(self._format, frame)

    def _set_parameters(self, params: dict):
        """
        Set camera parameters.
        :param params: Parameter dictionary.
        :return: Nothing.
        """
        if not self._camera_open:
            raise Exception("Camera connection not open, unable to set parameters")

        params_list = sort_parameters(params, self.param_prioritization)
        errors = ""  # Collecting all the errors in one message.
        name, value = None, None
        for param in params_list:
            try:
                name, value = param[0], param[1]
                if hasattr(self, name):
                    if name in ["exposure", "exposure_min", "exposure_max"]:
                        value *= 1e-6  # from us to s.
                    setattr(self, name, value)
            except Exception as e:
                errors += "Failed to set parameter '{}' value to {} with error: {} \n".format(name, value, str(e))

        if len(errors) != 0:
            log.error("Errors in writing parameter values: {}".format(errors))
            raise Exception(errors)

    def _get_parameters(self, params: List[str]):
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
                if hasattr(self, param):
                    ret_params[param] = getattr(self, param)

                if param in ["exposure", "exposure_min", "exposure_max"]:
                    ret_params[param] *= 1e6  # from s to us.
            except Exception as e:
                log.error("Failed to get parameter {}".format(param))
                raise

        return ret_params

    def _set_output_state(self, value: int):
        """
        Set all camera digital outputs to some value.
        :param value: Boolean value.
        """
        self._camera.set_int_parameter("UserOutputValueAll", value)
