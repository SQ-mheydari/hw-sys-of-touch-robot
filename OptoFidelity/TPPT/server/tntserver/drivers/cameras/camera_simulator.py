import logging

import tntserver.globals
from tntserver.drivers.cameras.camera import Camera
import queue
import time
import threading
import numpy as np
import cv2

log = logging.getLogger(__name__)


class Yasler_image_stub(np.ndarray):
    """
    Used in simulator hsup camera
    """

    def __new__(cls, image, timestamp=None, exposure=None, offset_x=None, offset_y=None, countervalue=None):
        """Constructor.
        Args:
            image: Image as numpy.array.
            timestamp: Timestamp in seconds. Absolute time from camera powering.
            exposure: Exposure in microseconds.
            offset_x: Offset of the image in X direction.
            offset_y: Offset of the image in Y direction.
            countervalue: Camera's internal counter value for the image for debugging purposes.
        """
        obj = np.asarray(image).view(cls)
        obj.timestamp = timestamp
        obj.exposure = exposure
        obj.offset = {}
        obj.offset[0] = offset_x
        obj.offset[1] = offset_y
        obj.counter_value = countervalue
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.timestamp = getattr(obj, 'timestamp', None)
        self.exposure = getattr(obj, 'exposure', None)
        self.offset = getattr(obj, 'offset', None)
        self.counter_value = getattr(obj, 'counter_value', None)

    def bgr(self):
        return np.array(self)

    def mono(self):
        return cv2.cvtColor(self.bgr(), cv2.COLOR_BGR2GRAY)


class Camera_Simulator(Camera):
    def __init__(self, **kwargs):

        self.name = None
        # parameters intended to be set
        exposure = 0.05

        # Simulate hsup camera parameters
        self._simulated_params = {'exposure': exposure * 1e6,
                                  'exposure_max' : 0.1 * 1e6,
                                  'exposure_min' : 0.001 * 1e6,
                                  'image_height': 600,
                                  'image_width': 800,
                                  'frame_rate': 500,
                                  'frame_rate_enable': False,
                                  'binning_horizontal': 1,
                                  'binning_vertical': 1,
                                  'offset_x': 0,
                                  'offset_y': 0,
                                  'resulting_frame_rate': 500}

        self.is_open = False
        self._is_grabbing = False
        self.tickfrequency = 1
        self.camera_image = None
        self.max_queue_size = 1
        # use queue, otherwise hsup camera hangs
        self._queue = queue.Queue(maxsize=self.max_queue_size)
        self._callback = self._on_capture
        self.capture_thread = None

        # Do super-class init last, because it tries to set exposure and gain
        super().__init__()

    @property
    def resolution(self):
        img = self._capture_image()
        h, w = img.shape[:2]
        return w, h

    @property
    def sensor_size(self):
        w, h = self.resolution
        pw, ph = self.pixel_size
        return w * pw, h*ph

    @property
    def exposure(self):
        return self._simulated_params['exposure'] / 1e6  # microseconds to seconds

    @property
    def exposure_max(self):
        return self._simulated_params['exposure_max'] / 1e6

    @property
    def exposure_min(self):
        return self._simulated_params['exposure_min'] / 1e6

    @exposure.setter
    def exposure(self, value):
        self._simulated_params['exposure'] = value * 1e6  # seconds to microseconds

    @property
    def resulting_frame_rate(self):
        return self._simulated_params['resulting_frame_rate']

    @property
    def frame_rate(self):
        return self._simulated_params['frame_rate']

    @frame_rate.setter
    def frame_rate(self, value):
        self._simulated_params['frame_rate'] = value

    def _open(self):
        self.is_open = True

    def _close(self):
        self.is_open = False

    def _get_photo(self):
        img = tntserver.globals.simulator_instance.get_photo(camera_name=self.name)

        # Scale image colors by relative exposure.
        # Overbrighting determines how much the image from the 3D visualization is overbrightened at max exposure.
        # The value of this factor is not that important but it will make brightness behave more realistically.
        overbright_factor = 3.0
        brightness_scaling = overbright_factor * (self.exposure / self.exposure_max)

        # Make gain also affect perceived brightness. There is not max_gain property so use some sensible value.
        gain_factor = self.gain / 2.0
        brightness_scaling *= gain_factor

        # Scale image brightness in HSV space.
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        v = np.array(np.clip(v * brightness_scaling, 0, 255), dtype=np.uint8)
        final_hsv = cv2.merge((h, s, v))

        img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)

        return img

    def _capture_image(self):
        """
        Simulate yasler driver to use queue to avoid hsup camera hanging
        Returns: np.ndarray of image
        -------

        """
        self.flush()
        image = self._get_photo()
        # put image into queue
        self._on_capture(image, None)
        # get image from queue
        return self.wait_for_image()

    def _on_capture(self, image, error):
        """
        Simulate yasler driver to use queue to avoid hsup camera hanging
        Returns: none
        """
        # if we ran out of space, remove oldest image
        if self._queue.full():
            try:
                self._queue.get()
            except queue.Empty:
                pass

        # there is only one capture thread that is filling the queue
        # => it is not possible that someone else filled the queue again when we get here
        if image is not None:
            self._queue.put(image)
        else:
            self._queue.put(error)

    def _get_parameters(self, names: list):
        """
        read parameter values from driver
        :param names: list of strings containing parameters to be read
        :return: dictionary with parameter_name: value
        """
        parameters = {}
        for name in names:
            if name in self._simulated_params:
                if name == 'resulting_frame_rate':
                    if self._simulated_params['frame_rate_enable']:  # simulate enforcing camera framerate
                        parameters['resulting_frame_rate'] = self._simulated_params['frame_rate']
                    else:
                        parameters['resulting_frame_rate'] = 500
                else:
                    parameters[name] = self._simulated_params[name]
            elif hasattr(self, name):
                parameters[name] = getattr(self, name)
            else:
                log.warning("Parameter {} doesn't exist.".format(name))
        return parameters

    def _set_parameters(self, params):
        """
        Set camera parameters.
        :param params: Parameter dictionary.
        :return:
        """
        for param in params.keys():
            if param in self._simulated_params:
                self._simulated_params[param] = params[param]
            elif hasattr(self, param):
                setattr(self, param, params[param])

    def set_burst_frame_count(self, amount=1):
        pass

    def burst(self, n=1, trigger_type='SW'):
        pass

    def set_fast_readout_mode(self):
        pass

    def activate_chunkdata(self):
        self._set_parameters(params={'chunk_mode_active': True})

    def set_countervalue_chunkdata(self, enabled=True):
        pass

    def set_exposure_chunkdata(self, enabled=True):
        # values must be set sequentially
        self._set_parameters(params={'chunk_selector': 'ExposureTime'})
        self._set_parameters(params={'chunk_enable': enabled})

    def capture_thread_runner(self):
        """
        Called by start_continuous() to capture image and call callback
        References: none
        """
        while self._is_grabbing:
            img = self._get_photo()
            image = Yasler_image_stub(img, timestamp=time.time(), exposure=30, offset_x=0, offset_y=0)
            time.sleep(0.1)
            try:
                self._callback(image, None)
            except Exception as e:
                log.error('Call back fails: ' + str(e))

    def wait_for_image(self, timeout=None):
        """
        Get image from queue
        Returns: np.ndarray of image
        """
        img = self._queue.get(timeout=timeout)
        return img

    def flush(self):
        """
        Clear image queue
        Returns: none
        """
        self._queue = queue.Queue(maxsize=self.max_queue_size)

    def start_continuous(self, callback=None, trigger_type='SW'):
        """
        Start continuous capture. In case of hsup, called by start_measurement().
        Parameters
        ----------
        callback: callback method
        trigger_type: In case of simulation, it is always 'SW'

        Returns: none
        -------

        """
        self._is_grabbing = True
        if callback is not None:
            self._callback = callback
        self.capture_thread = threading.Thread(target=self.capture_thread_runner)
        self.capture_thread.start()

    def stop_continuous(self):
        """
        Stop continuous capture

        Returns: none
        -------

        """
        self._is_grabbing = False
        self._callback = self._on_capture
        if self.capture_thread.is_alive():
            self.capture_thread.join()

    def get_image_from_buffer(self, timeout=1):
        """
         Get image from queue
         :param timeout: Time to wait for image to appear in buffer. After timeout queue.Empty is raised.
         :return: np.ndarray of image
         """
        return self.wait_for_image(timeout=timeout)

    def _set_output_state(self, value):
        pass
