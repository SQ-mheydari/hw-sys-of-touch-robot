import cv2
import numpy as np
import time
import logging

log = logging.getLogger(__name__)


def sort_parameters(params, prior_list):
    """
    Sort parameters first based on a prioritized list of parameter names then the rest alphabetically.
    :param params: Dict of type {"param1_name": param1_value, "param2_name": param2_value}.
    :param prior_list: List of parameter names in the desired order.
    :return: List of type [["param1_name", param1_value ], ["param2_name", param2_value ]]
    """
    parameters = params.copy()  # Using copy to avoid messing up the given parameter list.
    final_list = []
    # Going through prioritized parameters and adding them to final_list in correct order.
    params_list = list(parameters.keys())
    for param in prior_list:
        if param in params_list:
            final_list.append([param, params[param]])
            # After parameter is added to final_list it will be deleted.
            del parameters[param]
    # The rest of the parameters will be written in alphabetical order to make sure
    # the order is always the same.
    params_list = sorted(list(parameters.keys()))
    for param in params_list:
        final_list.append([param, parameters[param]])

    return final_list


class CameraInfo():
    def __init__(self):
        self._pixel_width = 0
        self._pixel_height = 0
        self._focal_length = 0
        self._sensor_width = 0
        self._sensor_height = 0
        self.ppmm = 0

    def to_dict(self):
        return {"pixel_width": self.pixel_width,
                "pixel_height": self.pixel_height,
                "focal_length": self.focal_length,
                "sensor_width": self.sensor_width,
                "sensor_height": self.sensor_height}

    def from_dict(self, d):
        ci = CameraInfo()
        ci.pixel_width = d.get("pixel_width",   0)
        ci.pixel_height = d.get("pixel_height",  0)
        ci.focal_length = d.get("focal_length",  1)
        ci.sensor_width = d.get("sensor_width",  1)
        ci._sensor_height = d.get("sensor_height", 1)


    @property
    def pixel_width(self):
        return self._pixel_width

    @pixel_width.setter
    def pixel_width(self, value):
        self._pixel_width = value

    @property
    def pixel_height(self):
        return self._pixel_height

    @pixel_height.setter
    def pixel_height(self, value):
        self._pixel_height = value

    @property
    def focal_length(self):
        return self._focal_length

    @focal_length.setter
    def focal_length(self, value):
        self._focal_length = value

    @property
    def sensor_width(self):
        return self._sensor_width

    @sensor_width.setter
    def sensor_width(self, value):
        self._sensor_width = value

    @property
    def sensor_height(self):
        return self._sensor_height

    @sensor_height.setter
    def sensor_height(self, value):
        self._sensor_height = value


class Camera:
    def __init__(self):
        self.exposure = 0
        self.gain = 0

        # Typical camera pixel size is 2.2 um.
        self._pixel_size = (0.0022, 0.0022)

        self.retry_count = 10

    def open(self):
        self._open()

    def close(self):
        self._close()

    def capture_image(self):
        # Capturing images, especially with gige cameras, is not robust and image capture success depends on
        # many factors such as interpacket delay, packet size and CPU load.
        for _ in range(self.retry_count):
            try:
                image = self._capture_image()

                if image is None or len(image.shape) == 0:
                    return image

                return image
            except Exception as e:
                log.error("Could not capture image: {}. Retrying.".format(str(e)))

                # Wait for a while before retry to increase odds that the underlying problem goes away.
                time.sleep(0.1)

        raise Exception("Exceeded maximum image capture retry count {}.".format(self.retry_count))

    def set_parameters(self, params):
        """
        Set camera parameters.
        :param params: Parameter dictionary.
        :return: Nothing.
        """
        self._set_parameters(params)

    def get_parameters(self, params):
        """
        Get given set of parameters from camera. Input dict indicates which parameters are retrieved.
        :param params: Parameters to retrieve as list of strings.
        :return: Dictionary of requested parameters and their values.
        """
        return self._get_parameters(params)

    def set_output_state(self, value):
        """
        Set all camera digital outputs to some value.
        :param value: Boolean value.
        """
        return self._set_output_state(value)

    def _open(self):
        raise (Exception("camera driver must implement function _open"))

    def _close(self):
        raise (Exception("camera driver must implement function _close"))

    def _capture_image(self):
        raise (Exception("camera driver must implement function _capture_image"))

    def _set_parameters(self, params):
        raise Exception("camera driver must implement function _set_parameters")

    def _get_parameters(self, params):
        raise Exception("camera driver must implement function _get_parameters")

    def _set_output_state(self, value):
        raise Exception("camera driver must implement function _set_io")

    @property
    def pixel_size(self):
        return self._pixel_size

    @pixel_size.setter
    def pixel_size(self, pixel_size):
        self._pixel_size = pixel_size

    @property
    def resolution(self):
        raise(Exception("camera driver must implement resolution property"))

    @property
    def sensor_size(self):
        raise(Exception("camera driver must implement sensor_size property"))

    @property
    def exposure_min(self):
        raise (Exception("camera driver must implement exposure_min property"))

    @property
    def exposure_max(self):
        raise (Exception("camera driver must implement exposure_max property"))


class CameraFrame:
    """
    Class for storing captured frame from camera including timestamp.
    """

    def __init__(self, image: np.ndarray, timestamp: float = 0):
        # Should be BGR if color image to comply with opencv defaults.
        # If image is a view, make a copy.
        if image.base is not None:
            self.image = image.copy()
        self.image = image
        self.timestamp = timestamp

    def bgr(self) -> np.ndarray:
        """
        Return color version of image in BGR format.
        """
        shape = self.image.shape
        if len(shape) == 3 and shape[2] == 3:
            return self.image
        return cv2.cvtColor(self.image, cv2.COLOR_GRAY2BGR)

    def mono(self) -> np.ndarray:
        """
        Return grayscale version of image.
        """
        shape = self.image.shape
        if len(shape) == 3 and shape[2] == 3:
            return cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        return self.image
