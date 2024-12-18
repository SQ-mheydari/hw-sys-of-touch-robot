import time

import numpy as np

from tntserver.drivers.cameras.camera import CameraFrame


class CameraTestStub:
    """
    Stub for camera driver that is used in Camera unit testing
    """

    def __init__(self):
        """
        Init function that sets dummy values for some needed parameters
        """
        self.gain = 20
        self.exposure = 0.1
        self.exposure_min = 0.0001
        self.exposure_max = 0.1
        self.width = 1024
        self.height = 768
        self.sensor_width = 10.24
        self.sensor_height = 7.68

        # Static image returned by capture_image().
        # The image is modulated by exposure value.
        self.camera_image = None

        # Set default camera image.
        self.set_asymmetric_test_pattern_rgb_image()

        # set parameters
        self.parameters = dict()
        self.parameters['gain'] = self.gain
        self.parameters['exposure'] = self.exposure
        self.parameters['exposure_min'] = self.exposure_min
        self.parameters['exposure_max'] = self.exposure_max
        self.parameters['width'] = self.width
        self.parameters['height'] = self.height
        self.parameters['sensor_width'] = self.sensor_width
        self.parameters['sensor_height'] = self.sensor_height

    def open(self):
        """
        Stub for open()
        """
        pass

    def close(self):
        """
        Stub for close()
        """
        pass

    def capture_image(self):
        """
        Stub for capture_image
        :return: a image with asymmetric colored pattern
        """

        # Scale image by exposure so that exposure_max corresponds to unchanged image.
        scale = min(self.exposure / self.exposure_max, 1.0)

        scaled_image = np.array(self.camera_image * scale, dtype=np.uint8)

        return scaled_image

    @property
    def resolution(self):
        """
        Stub for resolution
        :return: width and height dummy values
        """
        return self.width, self.height

    @property
    def sensor_size(self):
        """
        Stub for sensor_size
        :return: sensor width and height dummy values
        """
        return self.sensor_width, self.sensor_height

    def set_asymmetric_test_pattern_rgb_image(self):
        """
        Generate a asymmetric pattern to image
        :return:
        """
        # Creating white RGB image
        img = np.ones((self.height, self.width, 3), dtype=np.uint16) * 255
        # generating a asymmetric pattern to image
        for x in range(0, self.height, 10):
            for y in range(0, self.width, 10):
                img[x, y] = (int(round(x / self.height * 255)), int(round(y / self.width * 255)),
                             int(round((x + y) / (self.height + self.width) * 255)))

        self.camera_image = img

    def set_white_rgb_image(self):
        """
        Set a white rgb image to camera_image
        :return:
        """
        self.camera_image = np.ones((self.height, self.width, 3), dtype=np.uint16) * 255

    def get_parameters(self, params):
        """
        Stub for get_parameters().
        :param params: dict indicates which parameters are retrieved
        :return: dict of parameters
        """
        ret_params = {}
        for param in params:
            if param in self.parameters.keys():
                ret_params[param] = self.parameters[param]

        return ret_params

    def set_parameters(self, params):
        """
        Stub for set_parameters()
        :param params: dict of parameters to be set
        :return:
        """
        for param in params:
            if param in self.parameters.keys():
                self.parameters[param] = params[param]

        self.gain = self.parameters['gain']
        self.exposure = self.parameters['exposure']
        self.width = self.parameters['width']
        self.height = self.parameters['height']
        self.sensor_width = self.parameters['sensor_width']
        self.sensor_height = self.parameters['sensor_height']

    def start_continuous(self, callback=None, trigger_type='SW'):
        """
        Stub function, start continous frame capture based on either camera's internal timer or external HW trigger
        :param callback: function to call for each captured image. if None, uses driver's default callback
        :param trigger_type: either 'SW', 'HW' or 'HWBurst'.
        :return:
        """

        # Spew out some blank frames to test the blinking detection.
        if callback is not None:
            for _ in range(10):
                img = CameraFrame(np.zeros((self.height, self.width, 3), dtype=np.uint8), time.time())
                callback(img, None)
                time.sleep(0.1)

    def stop_continuous(self):
        """
        Stub function, stop continuous capture that was started by start_continuous()
        :return:
        """
        pass

    def get_image_from_buffer(self, timeout):
        """
        Stub for get_image_from_buffer()
        :param timeout: timeout for drive getting data
        :return: np.ndarray of image
        """
        return self.capture_image()