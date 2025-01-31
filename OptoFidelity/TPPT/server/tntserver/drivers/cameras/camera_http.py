import cv2
import numpy as np
import base64

import tntserver.globals

from tntserver.drivers.cameras.camera import Camera
import urllib.request



class Camera_Http(Camera):
    """
    Camera "driver" to fetch images from HTTP source
    Convenience driver if camera and driver are on another computer.
    uri style: http://address/photo?exposure=1
    """
    def __init__(self, url:str, **kwargs):
        super().__init__()
        self._url = url

    def _open(self):
        pass

    def _close(self):
        pass

    def _capture_image(self):
        url = "{}/photo?exposure={}".format(self._url, self.exposure)
        data = urllib.request.urlopen(url).read()
        image = cv2.imdecode(np.asarray(bytearray(data), dtype=np.uint8), flags=0)

        return image

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



