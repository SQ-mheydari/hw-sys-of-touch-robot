from . import camera
import logging
import platform
import time

# xiapi is a module that is loaded on demand.
xiapi = None

log = logging.getLogger(__name__)


class Camera_Ximea(camera.Camera):
    """
    TnT camera driver for Ximea USB camera
    Uses Ximea Python API instead of modified OpenCV
        so works with standard OpenCV installations

    Camera serial number can be found with XiCamTool by getting camera info
    """
    def __init__(self, serial_number, **kwargs):
        """
        Initializes the camera
        :param serial_number: camera serial number which is unique for each camera
        """

        # Mac / Windows driver
        p = platform.platform()

        global xiapi

        if xiapi is None:
            if "Darwin" in p:
                from .ximea import MacOS as ximea
                from .ximea.MacOS import xiapi as xiapi_macos
                xiapi = xiapi_macos
            else:
                from .ximea import windows as ximea
                from .ximea.windows import xiapi as xiapi_windows
                xiapi = xiapi_windows

        super().__init__()
        self.driver = None

        # create camera instance
        log.info("open camera serial number {}".format(serial_number))
        try:
            self.driver = xiapi.Camera(serial_number)
        except Exception as e:
            log.error("could not create camera : {}".format(e))
            raise (Exception("no ximea found with serial number {}".format(serial_number)))

        # open the camera for driver functions to work
        log.info("Opening Ximea serial number {}".format(serial_number))
        while True:
            try:
                self.driver.open_device_by_SN(str(serial_number))
                break
            except Exception as e:
                time.sleep(1)
        log.info("Opened Ximea serial number {}".format(serial_number))

        self._serial_number = serial_number

    def _open(self):
        self.driver.enable_auto_wb()
        # self.driver.enable_aeag()

        self.driver.set_imgdataformat('XI_RGB24')
        self.driver.set_limit_bandwidth(150)

        try:
            self.driver.start_acquisition()
        except:
            pass


    def _close(self):
        return

    def _capture_image(self):
        # downsampling is possible
        # v = self.driver.get_downsampling()
        # self.driver.set_downsampling('XI_DWN_2x2')
        # Sometimes exception occurs even set exposure_min to exposure, so add exception handling
        try:
            self.driver.set_exposure(int(self.exposure * 1000000.0))
            self.driver.set_gain(self.gain)
        except Exception as e:
            log.exception(e)

        img = xiapi.Image()
        self.driver.get_image(img, timeout=1000000)
        image = img.get_image_data_numpy()

        return image

    def get_image_from_buffer(self, timeout):
        """
        Function with this name is needed for mjpeg video streaming. For Ximea camera
        there is no difference between normal image capture and streamed image capture.
        :param timeout: not used
        """
        return self._capture_image()

    def start_continuous(self, callback=None, trigger_type='SW'):
        """
        Stub function for mjpeg streaming compatibility. For Ximea cameras there is no difference
        between normal and streamed capture. Also, the camera does not provide trigger options.
        :param callback: not used
        :param trigger_type: not used
        """
        pass

    def stop_continuous(self):
        """
        Stub function for mjpeg streaming compatibility.
        """
        pass

    def update_parameters(self):
        """
        Fetch the latest parameters from Ximea driver.
        :return: dict of updated parameters
        """
        parameters = {}
        try:
            parameters['gain'] = self.driver.get_gain()
            parameters['gain_max'] = self.driver.get_gain_maximum()
            parameters['gain_min'] = self.driver.get_gain_minimum()
            parameters['exposure'] = self.driver.get_exposure()
            parameters['exposure_max'] = self.driver.get_exposure_maximum()
            parameters['exposure_min'] = self.driver.get_exposure_minimum()
        except Exception as e:
            log.error("Failed to get parameters")
            raise e
        return parameters

    def _get_parameters(self, params):
        """
        Get given set of parameters from camera. Input dict indicates which parameters are retrieved.
        :param params: Parameters to retrieve as list of strings.
        :return: Dictionary of requested parameters and their values.
        """
        params_fetched = self.update_parameters()
        ret_params = {}
        for param in params:
            if param in params_fetched.keys():
                ret_params[param] = params_fetched[param]
        return ret_params

    @property
    def resolution(self):
        w = self.driver.get_width()
        h = self.driver.get_height()
        return w, h

    @property
    def sensor_size(self):
        w, h = self.resolution
        pw, ph = self.pixel_size
        return w * pw, h*ph

    @property
    def exposure_max(self):
        """
        Maximum exposure value.
        :return: Maximimum exposure value in seconds.
        """
        return self.driver.get_exposure_maximum()/1e6

    @property
    def exposure_min(self):
        """
        Minimum exposure value.
        :return: Minimum exposure value in seconds.
        """
        return self.driver.get_exposure_minimum()/1e6
