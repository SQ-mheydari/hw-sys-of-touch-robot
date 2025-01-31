from tntserver.Nodes.TnT.Camera import *
from tntserver.Nodes.TnT.Robot import *
from tntserver.Nodes.Node import *
from tntserver.Nodes.TnT.Detector import Detector
from tntserver.Nodes.TnT.Detectors import Detectors
from tntserver.Nodes.TnT.Images import Images
from tntserver.drivers.cameras.camera_test import CameraTestStub
from tntserver.drivers.cameras.camera import sort_parameters
from tests.test_tnt_robot_node import *
import math
import cv2
import json
import numpy as np
from PIL import Image
import os
import pytest
import time
import threading


class WfileStub:
    """
    Stub used by HttpHandlerStub
    """
    def __init__(self):
        self.data = None

    def write(self, data):
        self.data = data


class HttpHandlerStub:
    """
    Stub for test get_mjpeg_stream()
    """
    def __init__(self):
        self.wfile = WfileStub()

    def send_response(self, code):
        pass

    def send_header(self, type, details):
        pass

    def end_headers(self):
        pass


def init_camera():
    """
    Inits a Camera object with test driver
    :return: Camera object
    """
    camera = Camera("Camera1")
    camera._init(driver="test")

    return camera


def calibrate_camera(camera):
    # Put some calibration data.
    camera.calibration = {
        "intrinsic": [[30000.0, 0.0, 1500.0], [0.0, 30000.0, 1000.0], [0.0, 0.0, 1.0]],
        "ppmm": 30.0,
        "dist_coeffs": [[-25.0], [700.0], [-0.01], [-0.01], [3.0]]
    }

def init_robot(camera):
    """
    Initialize robot node with sensible arguments.
    :return: Robot node object
    """

    robot = Robot("Robot1")
    robot._init(
        driver="golden",
        host="127.0.0.1",
        port=4001,
        model="3axis",
        simulator=True,
        speed=200,
        acceleration=400,
        program_arguments=ProgramArguments()
    )
    root = Node("root")
    Node.root = root
    root.add_child(robot)

    tool = Tool("tool1")
    mount = Mount("tool_mount")
    mount.mount_point = "tool1"
    mount.add_child(tool)
    robot.add_child(mount)

    tip = Tip('tip1')
    tool.add_child(tip)

    if camera:
        mount_camera = Mount("camera_mount")
        mount_camera.mount_point = "camera"
        mount_camera.add_child(camera)
        robot.add_child(mount_camera)

    return robot


def test_camera_driver():
    """
    Test if exception would raise when invalid driver type
    :return:
    """
    camera = Camera("camera_test")
    with pytest.raises(Exception):
        camera._init(driver="xyz")


def test_get_still():
    """
    Test for still(). Compares images from CameraTestStub directly
    with the one obtained through Camera object with different types
    of parametrization
    :return:
    """
    camera = init_camera()

    # TODO if test performance becomes an issue, the reference picture could probably be smaller

    # ------------------------------------------
    # Default values (Rotate: False, flipx: False, flipy: False)
    ref_img = CameraTestStub().capture_image()
    t, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20)
    assert t == "raw"
    assert np.allclose(ref_img, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: False, flipx: False, flipy: False
    ref_img = CameraTestStub().capture_image()
    t, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20,
                              rotate90=False, flipx=False, flipy=False)
    assert t == "raw"
    assert np.allclose(ref_img, img)

    # zoom_test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, zoom=3,
                              rotate90=False, flipx=False, flipy=False)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[256:513, 342:683]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 200, 300
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=False, flipy=False)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                       rotate90=False, flipx=False, flipy=False, **kwargs)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=False, flipy=False, **kwargs)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=False, flipy=False)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                            rotate90=False, flipx=False, flipy=False, **kwargs)
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                       rotate90=False, flipx=False, flipy=False, **kwargs)
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: False, flipx: False, flipy: True
    ref_img = CameraTestStub().capture_image()
    ref_img = np.flipud(ref_img)
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20,
                              rotate90=False, flipx=False, flipy=True)
    assert np.allclose(ref_img, img)

    # zoom test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, zoom=3,
                              rotate90=False, flipx=False, flipy=True)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[256:513, 342:683]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 200, 300
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=False, flipy=True)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=False, flipy=True, **kwargs)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=False, flipy=True, **kwargs)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=False, flipy=True)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=False, flipy=True, **kwargs)
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=False, flipy=True, **kwargs)
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: False, flipx: True, flipy: False
    ref_img = CameraTestStub().capture_image()
    ref_img = np.fliplr(ref_img)
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20,
                              rotate90=False, flipx=True, flipy=False)
    assert np.allclose(ref_img, img)

    # zoom test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, zoom=3,
                              rotate90=False, flipx=True, flipy=False)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[256:513, 342:683]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 200, 300
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=True, flipy=False)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=True, flipy=False, **kwargs)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=True, flipy=False, **kwargs)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=True, flipy=False)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=True, flipy=False, **kwargs)
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=True, flipy=False, **kwargs)
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: False, flipx: True, flipy: True
    ref_img = CameraTestStub().capture_image()
    ref_img = np.fliplr(ref_img)
    ref_img = np.flipud(ref_img)
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20,
                              rotate90=False, flipx=True, flipy=True)
    assert np.allclose(ref_img, img)

    # zoom test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, zoom=3,
                              rotate90=False, flipx=True, flipy=True)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[256:513, 342:683]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 200, 300
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=True, flipy=True)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=True, flipy=True, **kwargs)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=False, flipx=True, flipy=True, **kwargs)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=True, flipy=True)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=True, flipy=True, **kwargs)
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=False, flipx=True, flipy=True, **kwargs)
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: True, flipx: False, flipy: False
    ref_img = CameraTestStub().capture_image()
    ref_img = np.rot90(ref_img, 1)
    t, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20,
                              rotate90=True, flipx=False, flipy=False)
    assert t == "raw"
    assert np.allclose(ref_img, img)

    # zoom_test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, zoom=3,
                              rotate90=True, flipx=False, flipy=False)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[342:683, 256:513]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 300, 200
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=False, flipy=False)
    # since there is rotation we need to change width and height with each other
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=False, flipy=False, **kwargs)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=False, flipy=False, **kwargs)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=False, flipy=False)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=False, flipy=False, **kwargs)
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=False, flipy=False, **kwargs)
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: True, flipx: False, flipy: True
    ref_img = CameraTestStub().capture_image()
    ref_img = np.flipud(ref_img)
    ref_img = np.rot90(ref_img, 1)
    t, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20,
                              rotate90=True, flipx=False, flipy=True)
    assert t == "raw"
    assert np.allclose(ref_img, img)

    # zoom_test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, zoom=3,
                              rotate90=True, flipx=False, flipy=True)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[342:683, 256:513]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 300, 200
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=False, flipy=True)
    # since there is rotation we need to change width and height with each other
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=False, flipy=True, **kwargs)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=False, flipy=True, **kwargs)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=False, flipy=True)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=False, flipy=True, **kwargs)
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=False, flipy=True, **kwargs)
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    #-------------------------------------------
    # Rotate: True, flipx: True, flipy: False
    ref_img = CameraTestStub().capture_image()
    ref_img = np.fliplr(ref_img)
    ref_img = np.rot90(ref_img, 1)
    t, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20,
                              rotate90=True, flipx=True, flipy=False)
    assert t == "raw"
    assert np.allclose(ref_img, img)

    # zoom_test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, zoom=3,
                              rotate90=True, flipx=True, flipy=False)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[342:683, 256:513]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 300, 200
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=True, flipy=False)
    # since there is rotation we need to change width and height with each other
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=True, flipy=False, **kwargs)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=True, flipy=False, **kwargs)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=True, flipy=False)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=True, flipy=False, **kwargs)
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=True, flipy=False, **kwargs)
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: True, flipx: True, flipy: True
    ref_img = CameraTestStub().capture_image()
    ref_img = np.fliplr(ref_img)
    ref_img = np.flipud(ref_img)
    ref_img = np.rot90(ref_img, 1)
    t, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20,
                              rotate90=True, flipx=True, flipy=True)
    assert t == "raw"
    assert np.allclose(ref_img, img)

    # zoom_test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, zoom=3,
                              rotate90=True, flipx=True, flipy=True)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[342:683, 256:513]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 300, 200
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=True, flipy=True)
    # since there is rotation we need to change width and height with each other
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=True, flipy=True, **kwargs)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, width=width, height=height,
                              rotate90=True, flipx=True, flipy=True, **kwargs)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=True, flipy=True)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    kwargs = {'interpolation': INTERPOLATION_NEAREST}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=True, flipy=True, **kwargs)
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    kwargs = {'interpolation': INTERPOLATION_LINEAR}
    _, img = camera.get_still(filetype="none", undistorted=False, exposure=5, gain=20, scaling=0.25,
                              rotate90=True, flipx=True, flipy=True, **kwargs)
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------


def test_rotate_target_image_to_camera():
    """
    Test rotate_target_image_to_camera()
    :return:
    """
    def check_rotated(angle, margin):
        target_width = 10
        target_height = 15
        ppmm = 12

        num_pixels_x = 800
        num_pixels_y = 600

        pos_x = target_width/2
        pos_y = -target_height/2
        target_frame = robotmath.xyz_euler_to_frame(pos_x, pos_y, 0, 180, 0, 180 - angle)

        # Black image.
        img = np.zeros((num_pixels_y, num_pixels_x, 3), dtype=np.uint8)

        # Scaled direction vector along DUT x-axis.
        dirx_x = math.cos(math.radians(angle)) * target_width * ppmm
        dirx_y = math.sin(math.radians(angle)) * target_width * ppmm

        # Scaled direction vector along DUT y-axis.
        diry_x = math.cos(math.radians(angle + 90)) * target_height * ppmm
        diry_y = math.sin(math.radians(angle + 90)) * target_height * ppmm

        pos_x = -pos_x * ppmm + num_pixels_x // 2
        pos_y = pos_y * ppmm + num_pixels_y // 2

        # Draw filled white rectangle that represents DUT image in camera view.
        contours = np.array([
            [round(pos_x), round(pos_y)],
            [round(pos_x + dirx_x), round(pos_y + dirx_y)],
            [round(pos_x + dirx_x + diry_x), round(pos_y + dirx_y + diry_y)],
            [round(pos_x + diry_x), round(pos_y + diry_y)]
        ])
        cv2.fillPoly(img, pts=[contours], color=(255, 255, 255))

        # Draw filled circles with distinct colors to three corners.
        cv2.circle(img, (int(round(pos_x)), int(round(pos_y))), radius=3, color=(255, 0, 0), thickness=-1)
        cv2.circle(img, (int(round(pos_x + dirx_x)), int(round(pos_y + dirx_y))), radius=3, color=(0, 255, 0), thickness=-1)
        cv2.circle(img, (int(round(pos_x + diry_x)), int(round(pos_y + diry_y))), radius=3, color=(0, 0, 255), thickness=-1)

        #cv2.imshow('image', img)
        #cv2.waitKey(0)

        img_rotated = rotate_target_image_to_camera(img, target_frame, target_width, target_height, ppmm, margin)

        shape = img_rotated.shape

        #cv2.imshow('image', img_rotated)
        #cv2.waitKey(0)

        assert shape[0] == (target_height + margin * 2) * ppmm
        assert shape[1] == (target_width + margin * 2) * ppmm

        margin_px = margin * ppmm

        corner1 = img_rotated[margin_px, margin_px]
        corner2 = img_rotated[margin_px, -margin_px - 1]
        corner3 = img_rotated[-margin_px - 1, margin_px]

        # Make sure the colored corners are found at correct locations.
        assert corner1[0] == 255 and corner1[1] == 0 and corner1[2] == 0
        assert corner2[0] == 0 and corner2[1] == 255 and corner2[2] == 0
        assert corner3[0] == 0 and corner3[1] == 0 and corner3[2] == 255

    # Test image rotation with multiple angles.
    for angle in [-90, 0, 45, 90, 180]:
        for margin in [0, 1]:
            check_rotated(angle, margin)


def test_auto_exposure():
    """
    Test auto_exposure()
    :return:
    """
    camera = init_camera()

    # Use white image as camera image.
    camera._driver.set_white_rgb_image()

    exposure = camera.auto_exposure(starting_exposure=0.7, undistorted=False)

    # Test camera has fully white image at maximum exposure. Make sure that auto-exposure produces roughly this value.
    # Auto-exposure aims to find exposure where image is not highly over or underexposed. With white input image it
    # produces roughly the exposure that gives fully white output image.
    # There could be a more realistic input image but this test makes sure the code runs without errors and produces
    # at least sensible result.
    assert abs(exposure - camera._driver.exposure_max) < 0.01


def test_numpy_array_to_bytes():
    """
    Test numpy_array_to_bytes()
    :return:
    """
    a = np.ones((100, 80, 3), dtype=np.uint16) * 255
    b = numpy_array_to_bytes(a)
    assert isinstance(b, bytes)


def test_image_data_to_http_response():
    """
    Test image_data_to_http_response()
    :return:
    """
    data = np.ones((100, 80, 3), dtype=np.uint16) * 255
    # none
    t, img_rsps = image_data_to_http_response('none', data)
    assert t == 'raw'
    assert np.allclose(img_rsps, data)

    # jpg
    # jpg is such format that after encode and decode, it is not the same
    img = Image.open(os.path.join(os.getcwd(), 'tests', 'images', 'logo.jpg'))
    data_jpg = np.array(img)
    t, img_rsps = image_data_to_http_response('jpg', data_jpg)
    assert t == 'image/jpeg'
    assert isinstance(img_rsps, np.ndarray)

    # png
    img = Image.open(os.path.join(os.getcwd(), 'tests', 'images', 'png_test.png'))
    data_png = np.array(img)
    t, img_rsps = image_data_to_http_response('png', data_png)
    assert t == 'image/png'
    img_dec = cv2.imdecode(img_rsps, -1)
    assert np.allclose(img_dec, data_png)

    # raw
    t, img_rsps = image_data_to_http_response('raw', data)
    assert t == 'text/string'
    assert img_rsps is not None

    # bytes
    t, img_rsps = image_data_to_http_response('bytes', data)
    assert t == 'application/octet-stream'
    assert img_rsps is not None

    # npy
    t, img_rsps = image_data_to_http_response('npy', data)
    assert t == 'image/npy'
    assert img_rsps is not None

    # wrong file type
    t, img_rsps = image_data_to_http_response('xyz', data)
    assert img_rsps is None


def test_image_transformations():
    """
    Test image_transformations()
    :return:
    """
    camera = init_camera()
    test_img = CameraTestStub().capture_image()

    # ------------------------------------------
    # Rotate: False, flipx: False, flipy: False
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=None, zoom=None, undistorted=None,
                                       interpolation=None)
    ref_img = test_img
    assert np.allclose(ref_img, img)

    # zoom_test
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=None, zoom=3, undistorted=None,
                                       interpolation=None)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[256:513, 342:683]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 200, 300
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)

    # ------------------------------------------

    # ------------------------------------------
    # Rotate: False, flipx: False, flipy: True
    ref_img = np.flipud(test_img)
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=None, zoom=None, undistorted=None,
                                       interpolation=None)
    assert np.allclose(ref_img, img)

    # zoom test
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=None, zoom=3, undistorted=None,
                                       interpolation=None)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[256:513, 342:683]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 200, 300
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: False, flipx: True, flipy: False
    ref_img = np.fliplr(test_img)
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=None, zoom=None, undistorted=None,
                                       interpolation=None)
    assert np.allclose(ref_img, img)

    # zoom test
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=None, zoom=3, undistorted=None,
                                       interpolation=None)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[256:513, 342:683]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 200, 300
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: False, flipx: True, flipy: True
    ref_img = np.fliplr(test_img)
    ref_img = np.flipud(ref_img)
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=None, zoom=None, undistorted=None,
                                       interpolation=None)
    assert np.allclose(ref_img, img)

    # zoom test
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=None, zoom=3, undistorted=None,
                                       interpolation=None)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[256:513, 342:683]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 200, 300
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=None,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=None,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 256, 192
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: True, flipx: False, flipy: False
    ref_img = np.rot90(test_img, 1)
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=None, zoom=None, undistorted=None,
                                       interpolation=None)
    assert np.allclose(ref_img, img)

    # zoom_test
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=None, zoom=3, undistorted=None,
                                       interpolation=None)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[342:683, 256:513]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # since there is rotation we need to change width and height with each other
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=None, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: True, flipx: False, flipy: True
    ref_img = np.flipud(test_img)
    ref_img = np.rot90(ref_img, 1)
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=None, zoom=None, undistorted=None,
                                       interpolation=None)
    assert np.allclose(ref_img, img)

    # zoom_test
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=None, zoom=3, undistorted=None,
                                       interpolation=None)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[342:683, 256:513]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # since there is rotation we need to change width and height with each other
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=None, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    #-------------------------------------------
    # Rotate: True, flipx: True, flipy: False
    ref_img = np.fliplr(test_img)
    ref_img = np.rot90(ref_img, 1)
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=None, zoom=None, undistorted=None,
                                       interpolation=None)
    assert np.allclose(ref_img, img)

    # zoom_test
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=None, zoom=3, undistorted=None,
                                       interpolation=None)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[342:683, 256:513]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # since there is rotation we need to change width and height with each other
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=True, flipy=None, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------

    # ------------------------------------------
    # Rotate: True, flipx: True, flipy: True
    ref_img = np.fliplr(test_img)
    ref_img = np.flipud(ref_img)
    ref_img = np.rot90(ref_img, 1)
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=None, zoom=None, undistorted=None,
                                       interpolation=None)
    assert np.allclose(ref_img, img)

    # zoom_test
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=None, zoom=3, undistorted=None,
                                       interpolation=None)
    # The image "zoom" values are gotten from a working piece of code and
    # work only for zoom=3 and not rotated image
    zoom_ref = ref_img.copy()
    zoom_ref = zoom_ref[342:683, 256:513]
    assert np.allclose(zoom_ref, img)

    # width and height test
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # since there is rotation we need to change width and height with each other
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(w_h_ref, img)

    # interpolation: nearest
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(w_h_ref, img)

    # interpolation: linear
    width, height = 300, 200
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=True,
                                       width=width, height=height, scaling=None, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    width, height = height, width
    w_h_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(w_h_ref, img)

    # scaling test
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_CUBIC)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_CUBIC)
    assert np.allclose(scaling_ref, img)

    # interpolation: nearest
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_NEAREST)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_NEAREST)
    assert np.allclose(scaling_ref, img)

    # interpolation: linear
    img = camera.image_transformations(image=test_img, flipx=True, flipy=True, rotate90=True,
                                       width=None, height=None, scaling=0.25, zoom=None, undistorted=None,
                                       interpolation=INTERPOLATION_LINEAR)
    # These values are obtained from working piece of code and only work if scaling is 0.25
    width, height = 192, 256
    scaling_ref = cv2.resize(ref_img.copy(), (width, height), interpolation=cv2.INTER_LINEAR)
    assert np.allclose(scaling_ref, img)
    # ------------------------------------------


def test_put_start_continuous():
    """
    Test put_start_continuous()
    :return:
    """
    camera = init_camera()
    # default parameters, undistorted = False
    camera.put_start_continuous()

    # undistorted: true
    camera = init_camera()
    camera.put_start_continuous(undistorted='true')

    # undistorted: false
    camera = init_camera()
    camera.put_start_continuous(undistorted='false')

    # undistorted: any
    camera = init_camera()
    camera.put_start_continuous(undistorted='xyz')

    # other parameters, undistorted=True
    camera = init_camera()
    camera.put_start_continuous(width=100, height=200, zoom=2, undistorted=True,
                                exposure=10, gain=20, scaling=0.3, interpolation=INTERPOLATION_LINEAR)


def test_put_stop_continuous():
    """
    Test put_stop_continuous()
    :return:
    """
    camera = init_camera()
    camera.put_stop_continuous()



def test_get_mjpeg_stream():
    """
    Test get_mjpeg_stream().
    - first call put_start_continuous()
    - Place get_mjpeg_stream() which runs in the loop to a thread, start the thread
    - wait for 3s
    - call put_stop_continuous() to stop the loop, and end the thread
    :return:
    """
    http_handler = HttpHandlerStub()
    camera = init_camera()
    camera.put_start_continuous()

    t = threading.Thread(target=camera.get_mjpeg_stream, args=(http_handler, ))
    t.start()
    time.sleep(3)
    camera.put_stop_continuous()
    data = http_handler.wfile.data
    assert data is not None
    assert isinstance(data, np.ndarray)


def test_put_move_with_robot():
    """
    Test put_move_with_robot(). Move the camera with robot to given frame.
    :return:
    """
    x, y, z = 120, 150, -5
    frame = [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]
    frame = np.matrix(frame)
    camera = init_camera()
    robot = init_robot(camera)
    camera.put_move_with_robot(frame=frame, context=None)

    position = robot.get_position()
    assert np.allclose(from_jsonout(position)['position']['x'], x)
    assert np.allclose(from_jsonout(position)['position']['y'], y)
    assert np.allclose(from_jsonout(position)['position']['z'], z)


def test_move_with_robot():
    """
    Test move_with_robot(). Move the camera with robot to given frame.
    :return:
    """
    x, y, z = 120, 150, -5
    frame = [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]
    frame = np.matrix(frame)
    camera = init_camera()
    robot = init_robot(camera)
    camera.move_with_robot(frame=frame, context=None, robot=robot)

    position = robot.get_position()
    assert np.allclose(from_jsonout(position)['position']['x'], x)
    assert np.allclose(from_jsonout(position)['position']['y'], y)
    assert np.allclose(from_jsonout(position)['position']['z'], z)


def test_put_move():
    """
    Test put_move(). Move camera to a given position
    :return:
    """
    x, y, z = 120, 150, -5
    camera = init_camera()
    robot = init_robot(camera)
    camera.put_move(x=x, y=y, z=z)

    position = robot.get_position()
    assert np.allclose(from_jsonout(position)['position']['x'], x)
    assert np.allclose(from_jsonout(position)['position']['y'], y)
    assert np.allclose(from_jsonout(position)['position']['z'], z)


def test_put_open():
    """
    Test put_open().
    :return:
    """
    camera = init_camera()
    camera.put_open()
    assert camera._camera_open is True


def test_put_close():
    """
    Test put_close()
    :return:
    """
    camera = init_camera()
    camera.put_close()
    assert camera._camera_open is False

def test_get_info():
    """
    Test get_info()
    :return:
    """
    camera = init_camera()
    camera_info = camera.get_info()

    assert from_jsonout(camera_info)['pixel_width'] == camera.pixel_width
    assert from_jsonout(camera_info)['pixel_height'] == camera.pixel_height
    assert from_jsonout(camera_info)['sensor_width'] == camera._driver.sensor_size[0]
    assert from_jsonout(camera_info)['sensor_height'] == camera._driver.sensor_size[1]


@pytest.mark.parametrize("as_string", [True, False])
def test_put_get_parameters(as_string):
    """
    Test put_parameters() and get_parameters()
    :return:
    """
    params = dict()
    params['gain'] = 25
    params['exposure'] = 0.11
    params['width'] = 562
    params['height'] = 384
    params['sensor_width'] = 12
    params['sensor_height'] = 10
    params['xxx'] = 0

    camera = init_camera()
    status = camera.put_parameters(params)
    assert from_jsonout(status)['status'] == 'ok'

    params_ret = dict()
    params_ret['gain'] = 0
    params_ret['exposure'] = 0
    params_ret['width'] = 0
    params_ret['height'] = 0
    params_ret['sensor_width'] = 0
    params_ret['sensor_height'] = 0
    params_ret['xxx'] = 0

    # get_parameters can take parameter as dict or JSON serialized string.
    if as_string:
        camera_parameters = camera.get_parameters(json.dumps(params_ret))
    else:
        camera_parameters = camera.get_parameters(params_ret)

    assert from_jsonout(camera_parameters)['params']['width'] == params['width']
    assert from_jsonout(camera_parameters)['params']['height'] == params['height']
    assert from_jsonout(camera_parameters)['params']['sensor_width'] == params['sensor_width']
    assert from_jsonout(camera_parameters)['params']['sensor_height'] == params['sensor_height']

    assert from_jsonout(camera_parameters)['status'] == 'ok'
    assert from_jsonout(camera_parameters)['params']['width'] == camera._driver.resolution[0]
    assert from_jsonout(camera_parameters)['params']['height'] == camera._driver.resolution[1]
    assert from_jsonout(camera_parameters)['params']['sensor_width'] == camera._driver.sensor_size[0]
    assert from_jsonout(camera_parameters)['params']['sensor_height'] == camera._driver.sensor_size[1]


def test_put_get_parameter():
    """
    Test put_parameter() and get_parameter()
    :return:
    """
    name = 'sensor_width'
    value = 15

    camera = init_camera()
    status = camera.put_parameter(name=name, value=value)
    assert from_jsonout(status)['status'] == 'ok'

    param = camera.get_parameter('sensor_width')
    assert from_jsonout(param)['status'] == 'ok'
    assert from_jsonout(param)['params']['sensor_width'] == value


def test_get_set_calibration():
    """
    Test calibration property, get and set
    :return:
    """

    calibration = dict()
    calibration['intrinsic'] = ((7380.366868530238, 0, 960), (0, 7441.618372631399, 720), (0, 0, 1))
    calibration['dist_coeffs'] = (-1.810908255526416,
                                  -271.82553691759125,
                                  -0.003216593906644989,
                                  -0.0029508830788391406,
                                  9114.929380107575
                                  )
    calibration['ppmm'] = 11.140556869215825

    camera = init_camera()
    camera.calibration = calibration

    calibration_ret = camera.calibration
    assert calibration_ret['intrinsic'] == calibration['intrinsic']
    assert calibration_ret['dist_coeffs'] == calibration['dist_coeffs']
    assert calibration_ret['ppmm'] == calibration['ppmm']


def test_get_focus_height():
    """
    Test get_focus_height() with and without tip attached
    :return:
    """
    camera = init_camera()
    # no tip attached, robot in home position
    robot = init_robot(camera)
    x, y, z = 120, 150, 50
    camera.frame = robotmath.xyz_to_frame(x, y, z)
    focus_height = camera.get_focus_height()
    assert np.allclose(float(from_jsonout(focus_height)), z)

    # no tip attached, robot in different position
    robot_frame = robotmath.xyz_to_frame(x, y, -5)
    robot.move_frame(robot_frame, robot.object_parent)
    focus_height = camera.get_focus_height()
    assert np.allclose(float(from_jsonout(focus_height)), z)

    # tip attached, robot in home position
    robot.put_home()
    tip_length = 5
    tip1 = robot.find('tool_mount').find('tool1').find('tip1')
    tip1.frame = robotmath.xyz_to_frame(0, 0, tip_length)
    focus_height = camera.get_focus_height()
    assert np.allclose(float(from_jsonout(focus_height)), abs(z - tip_length))


def test_get_detect_icon():
    pass # todo later, there is other ticket to make test detector stub TOUCH5705-346


def test_get_read_text():
    pass # todo later, there is other ticket to make test detector stub TOUCH5705-346


def test_put_auto_exposure():
    """
    Test put_auto_exposure()
    :return:
    """
    camera = init_camera()

    # Use white image as camera image.
    camera._driver.set_white_rgb_image()

    exposure = camera.put_auto_exposure(starting_exposure=0.7, undistorted=False)

    # Test camera has fully white image at maximum exposure. Make sure that auto-exposure produces roughly this value.
    # Auto-exposure aims to find exposure where image is not highly over or underexposed. With white input image it
    # produces roughly the exposure that gives fully white output image.
    # There could be a more realistic input image but this test makes sure the code runs without errors and produces
    # at least sensible result.

    # Check return format
    assert exposure[0] == 'application/json'
    assert isinstance(exposure[1], bytes)
    assert abs(float(from_jsonout(exposure)) - camera._driver.exposure_max) < 0.01


def test_camera_properties():
    camera = init_camera()

    exposure = camera.exposure
    exposure -= 0.05

    camera.exposure = exposure
    assert camera.exposure == pytest.approx(exposure)

    gain = camera.gain
    gain += 0.1

    camera.gain = gain
    assert camera.gain == pytest.approx(gain)


def test_sort_parameters():
    parameters = {'exposure': 0.05,
                  'frame_rate_enable': True,
                  'image_width': 800,
                  'image_height': 600,
                  'offset_x': 16,
                  'offset_y': 16,
                  'binning_horizontal': 1,
                  'binning_vertical': 2}
    param_prioritization = ["offset_x", "offset_y", "binning_horizontal", "binning_vertical",
                            "image_width", "image_height"]
    ref_list = [['offset_x', 16], ['offset_y', 16], ['binning_horizontal', 1], ['binning_vertical', 2],
                ['image_width', 800], ['image_height', 600], ['exposure', 0.05], ['frame_rate_enable', True]]

    sorted_list = sort_parameters(parameters, param_prioritization)

    assert sorted_list == ref_list


class PyfreStub:
    def __init__(self):
        self.results = []

    def initialize_engine(self, license, version):
        pass

    @staticmethod
    def create_result(tl_x, tl_y, br_x, br_y, text, kind):
        return kind, (tl_x, tl_y, br_x, br_y), text

    def process_image(self, filename, language, **kwargs):
        return self.results

def create_ocr_nodes(parent):
    detectors = Detectors("detectors")
    parent.add_child(detectors)

    pyfre = PyfreStub()
    # Add some test data. This corresponds to page
    #   One   Two
    #   Three Four
    # To test that results are ordered correctly. Abbyy uses natural text ordering for results.
    pyfre.results.append(PyfreStub.create_result(12, 100, 110, 150, "Three", "Word"))
    pyfre.results.append(PyfreStub.create_result(10, 20, 100, 80, "One", "Word"))
    pyfre.results.append(PyfreStub.create_result(150, 22, 260, 81, "Two", "Word"))
    pyfre.results.append(PyfreStub.create_result(140, 100, 270, 150, "Four", "Word"))

    detector = Detector("abbyy")
    detectors.add_child(detector)
    detector._init(driver="Abbyy", license="SWED-1000-0003-0684-9595-9238", pyfre_driver=pyfre)


def test_read_text():
    """
    Test Camera.read_text() API method.
    Does not test OCR itself only data processing in between Abbyy and REST API.
    Note that the reference results used here are bound to the camera stub resolution.
    """
    camera = init_camera()

    calibrate_camera(camera)

    Node.root = Node("tnt")

    # Put Camera node in tree root -> camera_mount -> camera
    # and use some translation to simulate translated camera. This affects read_text() results.
    camera_mount = Node("camera_mount")
    camera_mount.frame = robotmath.xyz_to_frame(200, 300, -50)
    Node.root.add_child(camera_mount)
    camera_mount.add_child(camera)

    create_ocr_nodes(Node.root)

    results = camera.get_read_text()
    results = from_jsonout(results)

    assert len(results) == 4

    num_result_keys = 5

    result = results[0]
    assert result["text"] == "Three"
    assert result["type"] == "Word"
    assert np.allclose(result["box_px"], [12, 100, 110, 150])
    assert np.allclose(result["pose"], [215.03333333333333, 291.3666666666667])
    assert np.allclose(result["size_mm"], [3.2666666666666515, 1.6666666666666288])
    assert len(result.keys()) == num_result_keys

    result = results[1]
    assert result["text"] == "One"
    assert result["type"] == "Word"
    assert np.allclose(result["box_px"], [10, 20, 100, 80])
    assert np.allclose(result["pose"], [215.23333333333335, 288.8666666666667])
    assert np.allclose(result["size_mm"], [3.0000000000000284, 2.0])
    assert len(result.keys()) == num_result_keys

    result = results[2]
    assert result["text"] == "Two"
    assert result["type"] == "Word"
    assert np.allclose(result["box_px"], [150, 22, 260, 81])
    assert np.allclose(result["pose"], [210.23333333333335, 288.91666666666663])
    assert np.allclose(result["size_mm"], [3.666666666666657, 1.9666666666666401])
    assert len(result.keys()) == num_result_keys

    result = results[3]
    assert result["text"] == "Four"
    assert result["type"] == "Word"
    assert np.allclose(result["box_px"], [140, 100, 270, 150])
    assert np.allclose(result["pose"], [210.23333333333335, 291.3666666666667])
    assert np.allclose(result["size_mm"], [4.333333333333343, 1.6666666666666288])
    assert len(result.keys()) == num_result_keys




