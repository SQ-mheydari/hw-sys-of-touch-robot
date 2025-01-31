import logging
import time
import base64
from operator import add, sub
from typing import List, Optional, Dict, Tuple

import cv2
import toolbox

from tntserver import robotmath
from tntserver.drivers.cameras.camera import CameraFrame

log = logging.getLogger(__name__)
import numpy as np
from tntserver.Nodes.TnT.Gestures import Gestures
from tntserver.Nodes.Node import *
from tntserver.Nodes.TnT.Image import Image, search_text, find_objects, calculate_detection_result_coordinates, \
    convert_crop_to_pixels, image_data_to_http_response
from tntserver import files
from tntserver.Nodes.TnT.Camera import rotate_target_image_to_camera, numpy_array_to_bytes, per_pixel_maximum
from tntserver.Nodes.TnT import DeletableNode
from tntserver.Nodes.TnT.PhysicalButton import PhysicalButton
import json
import transformations as tr
from tntserver.surface import Surface

import scipy.interpolate


class Dut(DeletableNode):
    """
    TnT™ Compatible DUT resource
    Should work together with
    - TnT Sequencer
    - TnT Positioning Tool
    """

    def __init__(self, name):
        super().__init__(name)
        self._width = 0
        self._height = 0
        self._touch_distance = 0
        self._base_distance = 10
        self._tl = (0, 0, 0)
        self._tr = (0, 0, 0)
        self._bl = (0, 0, 0)
        self._data = {"screen_height": {"value" : "0"}, \
                      "screen_width": {"value" : "0"}, \
                      "image_height": {"value" : "0"}, \
                      "image_width" : {"value" : "0"}}
        self._surface = None
        self._svg = None
        self._svgregion = None
        self._svg_scale = [1, 1]
        self._resolution = None


    def _init(self, **kwargs):
        super()._init(**kwargs)

        # Assume that Dut node is parent of Duts node that determines which Gestures node is instantiated
        # as child of Dut node.
        gestures = self.parent.gestures_cls("gestures")
        self.add_child(gestures)
        gestures._init()

        # try to load svg
        # this is the only way for DUT to know if it has an svg shape descriptor or not.
        self._svgregion = None

        try:
            svg_data = files.read_data("dut_svg", self.name + ".svg")
            self.set_svg_data(svg_data)
        except FileNotFoundError:
            # if file not found, DUT has no svg shape descriptor.
            # raise error if svg parsing fails
            pass

    @json_out
    def get_self(self):
        orientation = self.frame_to_orientation_json(self.frame)

        properties = {
            "top_left" : self.tl,
            "top_right" : self.tr,
            "bottom_left" : self.bl,
            "orientation" : orientation,
            "touch_distance": self.touch_distance,
            "base_distance": self.base_distance,
            "width" : self.width,
            "height" : self.height,
            # For Sequencer compatibility we need to include relation
            "relation" : None,
            "data" : self._data,
            "svg_scale": self._svg_scale,
            "resolution": self.resolution
            }

        r = {
            "name" : self.name,
            "kind" : "dut",
            "type" : "Dut",
            "properties" : properties,
            }

        return r

    @json_out
    def get_position(self, **kwargs):
        x, y, z = robotmath.frame_to_xyz(self.frame)
        return {"x": x, "y": y, "z": z}

    @property
    def width(self):
        """
        DUT width in mm.
        """
        return self._width

    @width.setter
    def width(self, value):
        self._width = value

    #

    @property
    def height(self):
        """
        DUT height in mm.
        """
        return self._height

    @height.setter
    def height(self, value):
        self._height = value

    @property
    def svg_scale(self):
        """
        scale factors for SVG.
        """
        return self._svg_scale

    @svg_scale.setter
    def svg_scale(self, value):
        """
        set scale for SVG.
        """
        self._svg_scale = value

    @property
    @private
    def orientation(self):
        """
        Orientation of the DUT i.e. the basis vectors of DUT's transform matrix.
        Given as dictionary {'i': x_basis_vector, 'j': y_basis_vector, 'k': z_basis_vector}.
        """
        return self.frame_to_orientation_json(self.frame)

    @property
    @private
    def position(self):
        """
        Corner positions of the DUT in its relative coordinate system context.
        Property is in dictionary from {"top_left": top_left, "top_right": top_right,
        "bottom_left": bottom_left, "bottom_right": bottom_right}.
        DEPRECATED: Exists for client compatibility.
        """
        return {
            "top_left": self.tl,
            "top_right": self.tr,
            "bottom_left": self.bl,
            "bottom_right": self.br,
        }

    @property
    def tl(self):
        """
        Position of top left corner of the DUT.
        """
        # TODO: In TnT Client this is expected to be in form of list [x, y, z].
        return {"x": self._tl[0], "y": self._tl[1], "z": self._tl[2]}

    @tl.setter
    def tl(self, value):
        x = float(value["x"])
        y = float(value["y"])
        z = float(value["z"])
        self._tl = (x, y, z)
        self.calculate()

    @property
    @private
    def top_left(self):
        """
        Top left corner.
        DEPRECATED: Added for client compatibility.
        """
        return self.tl

    @top_left.setter
    def top_left(self, value):
        """
        Top left corner.
        DEPRECATED: Added for client compatibility.
        """
        self.tl = value

    @json_out
    def put_tl(self, x=None, y=None, z=None):
        if x is None:
            x = self._tl[0]
        if y is None:
            y = self._tl[1]
        if z is None:
            z = self._tl[2]
        x, y, z = float(x), float(y), float(z)
        self.tl = {"x": x, "y": y, "z": z}
        self.save()
    #

    # get_map_to and get_map_from added for sequence generator support.
    @json_out
    def get_map_to(self, x, y, z, tilt=0, azimuth=0, to_context='tnt'):
        from_pose = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)
        to_pose = self.translate(from_pose, Node.find(to_context))
        x, y, z, xr, yr, zr = robotmath.frame_to_xyz_euler(to_pose)
        retval = {}
        retval["x"] = x
        retval["y"] = y
        retval["z"] = z
        retval["tilt"] = yr
        retval["azimuth"] = -zr
        return retval

    #
    @json_out
    def get_map_from(self, x, y, z, tilt=0, azimuth=0, from_context='tnt'):
        from_pose = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)
        to_pose = robotmath.translate(from_pose, Node.find(from_context), self)
        x, y, z, xr, yr, zr = robotmath.frame_to_xyz_euler(to_pose)
        retval = {}
        retval["x"] = x
        retval["y"] = y
        retval["z"] = z
        retval["tilt"] = yr
        retval["azimuth"] = -zr
        return retval
    #

    @property
    def tr(self):
        """
        Position of top right corner of the DUT.
        """
        # TODO: In TnT Client this is expected to be in form of list [x, y, z].
        return {"x" : self._tr[0], "y" : self._tr[1], "z" : self._tr[2]}

    @tr.setter
    def tr(self, value):
        x = float(value["x"])
        y = float(value["y"])
        z = float(value["z"])
        self._tr = (x, y, z)
        self.calculate()

    @property
    @private
    def top_right(self):
        """
        Top right corner.
        DEPRECATED: Added for client compatibility.
        """
        return self.tr

    @top_right.setter
    def top_right(self, value):
        """
        Top right corner.
        DEPRECATED: Added for client compatibility.
        """
        self.tr = value

    @json_out
    def put_tr(self, x=None, y=None, z=None):
        if x is None:
            x = self._tr[0]
        if y is None:
            y = self._tr[1]
        if z is None:
            z = self._tr[2]
        x, y, z = float(x), float(y), float(z)
        self.tr = {"x": x, "y": y, "z": z}
        self.save()
    #

    @property
    def bl(self):
        """
        Position of bottom left corner of the DUT.
        """
        # TODO: In TnT Client this is expected to be in form of list [x, y, z].
        return {"x" : self._bl[0], "y" : self._bl[1], "z" : self._bl[2]}

    @bl.setter
    def bl(self, value):
        x = float(value["x"])
        y = float(value["y"])
        z = float(value["z"])
        self._bl = (x, y, z)
        self.calculate()

    @property
    @private
    def bottom_left(self):
        """
        Bottom left corner.
        DEPRECATED: Added for client compatibility.
        """
        return self.bl

    @bottom_left.setter
    def bottom_left(self, value):
        """
        Bottom left corner.
        DEPRECATED: Added for client compatibility.
        """
        self.bl = value

    @json_out
    def put_bl(self, x=None, y=None, z=None):
        if x is None:
            x = self._bl[0]
        if y is None:
            y = self._bl[1]
        if z is None:
            z = self._bl[2]
        x, y, z = float(x), float(y), float(z)
        self.bl = {"x": x, "y": y, "z": z}
        self.save()

    @property
    @private
    def br(self):
        """
        Position of bottom right corner of the DUT.
        This property can't be set. The value is calculated from tl, tr and bl.
        """

        # Copied from TnT Client.
        tl = [self.tl["x"], self.tl["y"], self.tl["z"]]
        tr = [self.tr["x"], self.tr["y"], self.tr["z"]]
        bl = [self.bl["x"], self.bl["y"], self.bl["z"]]
        tl_tr = map(sub, tr, tl)
        tl_bl = map(sub, bl, tl)
        br = map(add, tl, tl_tr)
        br = map(add, br, tl_bl)
        br = list(br)

        # TODO: In TnT Client this is expected to be in form of list [x, y, z].
        return {"x": br[0], "y": br[1], "z": br[2]}

    @property
    @private
    def bottom_right(self):
        """
        Bottom right corner.
        This property can't be set. The value is calculated from tl, tr and bl.
        DEPRECATED: Added for client compatibility.
        """
        return self.br

    @property
    def touch_distance(self):
        return self._touch_distance

    @touch_distance.setter
    def touch_distance(self, value):
        self._touch_distance = float(value)

    #

    @property
    def base_distance(self):
        """
        DUT base distance.
        """
        return self._base_distance

    @base_distance.setter
    def base_distance(self, value):
        self._base_distance = float(value)

    #

    @property
    def resolution(self):
        """
        DUT screen resolution.
        """
        return self._resolution

    @resolution.setter
    def resolution(self, value):
        """
        Set DUT screen resolution.
        :param value: List or tuple containing horizontal and vertical resolution.
        """
        if value is not None:
            self._resolution = [int(value[0]), int(value[1])]
        else:
            self._resolution = None

    def frame_to_orientation_json(self, frame):
        # TODO: Does not return JSON string and does not use frame parameter.
        ox = self.frame[0, 0:3].A1
        oy = self.frame[1, 0:3].A1
        oz = self.frame[2, 0:3].A1

        orientation = {
            "i" : [float(v) for v in ox],
            "j" : [float(v) for v in oy],
            "k" : [float(v) for v in oz]
            }
        return orientation

    def frame_to_position_xyz(self, frame):
        f = self.frame.A1
        return float(f[3]), float(f[7]), float(f[11])

    def calculate(self):
        if self._tl == self._tr or self._tl == self._bl or self._tr == self._bl:
            log.debug("Not calculating DUT frame until three corners are set")
            return
        try:
            self.frame = robotmath.three_point_frame(self._tl, self._tr, self._bl)
            self.width = float(np.linalg.norm(np.array(self._tr) - np.array(self._tl)))
            self.height = float(np.linalg.norm(np.array(self._bl) - np.array(self._tl)))
        except:
            log.info("could not calculate dut from corners {}, {}, {}".format(self._tl, self._tr, self._bl))
            self.frame = robotmath.identity_frame()
            self.width = 0
            self.height = 0
        else:
            log.info("dut calculated, origo={}, width={}, height={}".format(robotmath.frame_to_xyz(self.frame), self.width, self.height))

    def screenshot(self, camera: str, margin: int=0, offset: tuple=(0, 0),
                    exposure=None, gain=None) -> Image:
        """
        Take a picture of the DUT screen
        :param camera: TnT camera resource name
        :param margin: Define how much around the DUT display is included in the picture.
        :param offset: Take the picture with an offset from the DUT display center. (default (0, 0)).
        :param exposure: exposure in seconds. If not set, uses last exposure used.
        :param gain: gain value. If not set, uses last gain value used.
        :return: tntserver.Nodes.TnT.Image.Image
        """
        camera = Node.find(camera)
        context = self

        # Prepare robots for capturing image.
        for robot in Node.find_class("Robot"):
            robot.camera_capture_preparations(camera.name)

        # Find robot that is parent of camera. If such robot is found, camera can be moved by moving the robot.
        robot = camera.find_object_parent_by_class_name("Robot")

        # move to the center of the DUT if camera is a transform tree under Robot.
        if robot is not None:
            self.validate_orientation(robot)

            pose = robotmath.xyz_to_frame(self.width / 2 + offset[0], self.height / 2 + offset[1], 0)
            frame = robotmath.pose_to_frame(pose)
            camera.move_with_robot(frame, context, robot)

        # take image
        img = camera.still(undistorted=True, exposure=exposure, gain=gain)

        # Transform DUT frame to camera context.
        target_frame = robotmath.translate(self.frame, self.object_parent, camera)

        # Rotate image so that DUT in the image is aligned with the resulting image.
        img = rotate_target_image_to_camera(img, target_frame, self.width, self.height, camera.ppmm, margin)

        # If DUT resolution property is set, scale image to screen resolution.
        if self.resolution is not None:
            img = cv2.resize(img, tuple(self.resolution))

        images = Node.find("images")

        if images is None:
            raise Exception("Images node not found. Revise configuration.")

        # Add new image resource. Use None name to generate image name from current time.
        img_name = images.add(None)
        screenshot = Node.find(img_name)

        screenshot.set_data(img)
        screenshot.ppmm = camera.ppmm

        # If DUT resolution is set, update ppmm to match the screen.
        if self.resolution is not None:
            # Calculate ppmm in the x direction. This should not make a difference if the pixels are square.
            screenshot.ppmm = self.resolution[0] / self.width

        # Make screenshot image node the object child of DUT.
        # This allows tracking transformations between image and DUT.
        # Note that this connection is lost on server restart as image nodes are not stored in config.
        # TODO: I think instead of 1/ppmm it would make more sense to use self.width / screenshot.width.
        screenshot.frame = robotmath.scale_xyz_to_frame(1 / screenshot.ppmm, 1 / screenshot.ppmm, 1.0)
        self.add_object_child(screenshot)

        return screenshot

    @json_out
    def post_screenshot(self, camera_id="Camera1", crop_left=None, crop_upper=None, crop_right=None,
                          crop_lower=None, crop_unit=None, exposure=None, gain=None, offset_x=0, offset_y=0):
        """
        Take screenshot of DUT screen and save it as image. First moves robot so that camera is
        in the middle of the DUT.
        :param camera_id: Name of camera to take image with.
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        :param exposure: exposure in seconds. If not set, uses last exposure used.
        :param gain: gain value. If not set, uses last gain value used.
        :param offset_x: Take the picture with an offset in x from the DUT display center. (default is 0)
        :param offset_y: Take the picture with an offset in y from the DUT display center. (default is 0)
        :return: Image name.
        """
        screenshot = self.screenshot(camera_id, exposure=exposure, gain=gain, offset=(offset_x, offset_y))

        if crop_unit is not None:
            screenshot.crop(crop_left, crop_upper, crop_right, crop_lower, crop_unit)
            screenshot.save_image()

        return screenshot.name

    def get_still(self, camera_id="Camera1", filetype="jpg", exposure=None, gain=None, undistorted: bool = False,
                  duration: Optional[float] = None):
        """
        Takes a photo in DUT orientation. This function doesn't move the robot but only takes an image.
        You can use screenshot first to move the robot so that camera is in the middle of the DUT.
        :param camera_id: Name of camera to take image with.
        :param filetype: jpg, png, raw(np.array).
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :param undistorted: Indicates whether to use calibrated image.
        :param duration: Video capture duration in seconds. Per-pixel maximum will be taken over the video.
        :return: Image in DUT orientation.
        """

        # TODO: Parameter set for this function should probably be aligned with Camera.get_still().
        #       This was not originally done to avoid testing features that were not needed.

        camera = Node.find(camera_id)

        if duration is None:
            img = camera.still(undistorted=undistorted, exposure=exposure, gain=gain)
        else:
            frames = camera.record_video(duration, undistorted=undistorted, exposure=exposure, gain=gain)
            img = per_pixel_maximum(frames)

        # Transform DUT frame to camera context.
        target_frame = robotmath.translate(self.frame, self.object_parent, camera)

        # Rotate image so that DUT in the image is aligned with the resulting image.
        # Margin parameter is set to 0 because that has to be same as in screenshot when used from find_objects
        # to guarantee that images in screenshot and still match.
        img = rotate_target_image_to_camera(img, target_frame, self.width, self.height, camera.ppmm, margin=0)

        # If DUT resolution property is set, scale image to screen resolution.
        if self.resolution is not None:
            img = cv2.resize(img, tuple(self.resolution))

        t, img_as_http_response = image_data_to_http_response(filetype, img)
        return t, img_as_http_response

    def record_video(self, duration: float, crop_left: Optional[float] = None, crop_upper: Optional[float] = None,
                     crop_right: Optional[float] = None, crop_lower: Optional[float] = None,
                     crop_unit: Optional[str] = None, offset: Tuple[float, float] = (0, 0),
                     exposure: Optional[float] = None, gain: Optional[float] = None,
                     camera_id: str = "Camera1") -> Tuple[List[CameraFrame], Image]:
        """
        Record video from camera. Before the video capture is started screenshot() is called to do the same preparations
        for the robot as when taking a screenshot.

        :param duration: Video capture duration in seconds.
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        :param offset: Record video with an offset from the DUT display center.
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :param camera_id: Name of the camera that is being used. (default is Camera1)

        :return: List of captured images as CameraFrames, Image node containing the captured screenshot.
        """

        # Take screenshot to prepare robot for video capture
        screenshot = self.screenshot(camera_id, exposure=exposure, gain=gain, offset=offset)

        camera = Node.find(camera_id)
        images = camera.record_video(duration, exposure=exposure, gain=gain, target_context=self.name)

        ppmm = camera.ppmm
        width = self.width * ppmm
        height = self.height * ppmm

        # If DUT resolution property is set, scale images to screen resolution.
        if self.resolution is not None:
            images = [CameraFrame(image=cv2.resize(image.bgr(), tuple(self.resolution)),
                                  timestamp=image.timestamp) for image in images]

        # Crop images
        if crop_unit is not None:
            crop_left, crop_upper, crop_right, crop_lower \
                = convert_crop_to_pixels(crop_left, crop_upper, crop_right, crop_lower, width, height, ppmm, crop_unit)

            images = [CameraFrame(image=image.bgr()[crop_upper:crop_lower, crop_left:crop_right],
                                  timestamp=image.timestamp) for image in images]

        return images, screenshot

    @json_out
    def post_find_objects(self, filename, min_score=0.8, crop_left=None, crop_upper=None, crop_right=None,
                          crop_lower=None, crop_unit=None, exposure=None, gain=None, detector='halcon',
                          offset_x=0, offset_y=0, camera_id="Camera1", duration=None):
        """
        Find an object model (.shm) from the currently visible portion of the screen.

        :param filename: Name of the icon. This is the same as the icon filename without extension.
        :param min_score: Minimum accepted confidence score of result [0.0 .. 1.0] (default 0.8).
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :param detector: detector node to be used in object recognition
        :param offset_x: Take the picture with an offset in x from the DUT display center. (default is 0)
        :param offset_y: Take the picture with an offset in y from the DUT display center. (default is 0)
        :param camera_id: Name of the camera that is being used. (default is Camera1)
        :param duration: Video capture duration in seconds. Per-pixel maximum is taken over the video frames.
            If set to None only one screenshot is taken.
        :return: Dictionary with keys: "success", "screenshot", "results".

        Response body:
                success -- Always True
                results -- Array of Result objects
                screenshot -- Name of the screenshot

            Result object (dictionary):
                score -- Match score [0.0 .. 1.0]
                topLeftX_px -- Bounding box top left x coordinate in pixels
                topLeftY_px -- Bounding box top left x coordinate in pixels
                bottomRightX_px -- Bounding box bottom right x coordinate in pixels
                bottomRightY_px -- Bounding box bottom right y coordinate in pixels
                centerX_px -- Bounding box center x coordinate in pixels
                centerY_px -- Bounding box center y coordinate in pixels
                topLeftX -- Bounding box top left x coordinate in mm
                topLeftY -- Bounding box top left x coordinate in mm
                bottomRightX -- Bounding box bottom right x coordinate in mm
                bottomRightY -- Bounding box bottom right y coordinate in mm
                centerX -- Bounding box center x coordinate in mm
                centerY -- Bounding box center y coordinate in mm
                shape -- Name of the shape file
                scale -- Detected icon scale
                angle -- Detected icon angle
        """
        if duration is None:
            screenshot = self.screenshot(camera_id, exposure=exposure, gain=gain, offset=(offset_x, offset_y))

            if crop_unit is not None:
                screenshot.crop(crop_left, crop_upper, crop_right, crop_lower, crop_unit)
                screenshot.save_image()

            results = find_objects(image=screenshot.data, icon_name=filename, min_score=min_score, detector=detector)
        else:
            images, screenshot = self.record_video(duration, crop_left=crop_left, crop_upper=crop_upper,
                                                   crop_right=crop_right, crop_lower=crop_lower, crop_unit=crop_unit,
                                                   exposure=exposure, gain=gain, camera_id=camera_id,
                                                   offset=(offset_x, offset_y))

            max_frame = per_pixel_maximum(images)

            screenshot.set_data(max_frame)
            screenshot.save_image()

            results = find_objects(image=max_frame, icon_name=filename, min_score=min_score, detector=detector)

        # Transform results from pixels (image context) to mm (DUT context).
        calculate_detection_result_coordinates(results, screenshot)

        for result in results["results"]:
            # Margin value that allows some round-off errors but is not dangerous in most typical situations.
            margin = 10.0

            # Sanity check to make sure the detection coordinates are within DUT limits.
            if not self.is_point_inside(result["centerX"], result["centerY"], margin) or \
                    not self.is_point_inside(result["topLeftX"], result["topLeftY"], margin) or \
                    not self.is_point_inside(result["bottomRightX"], result["bottomRightY"], margin):
                raise Exception("Detection result is not within DUT limits.")

        results['screenshot'] = screenshot.name
        return results

    @json_out
    def get_detect_blink_frequency(self, duration: float, crop_left: Optional[float] = None,
                                   crop_upper: Optional[float] = None, crop_right: Optional[float] = None,
                                   crop_lower: Optional[float] = None, crop_unit: Optional[float] = None,
                                   offset_x: float = 0, offset_y: float = 0, exposure: Optional[float] = None,
                                   gain: Optional[float] = None, camera_id: str = "Camera1",
                                   analyzer: str = "blink_detector") -> Dict:
        """
        Detect the blinking frequency of an icon. Call find_objects() first to get the region of interest for the
        icon and pass those for the crop parameters. It is important to only have one blinking icon in the region.

        :param duration: Video capture duration in seconds.
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        :param offset_x: Take the picture with an offset in x from the DUT display center. (default is 0)
        :param offset_y: Take the picture with an offset in y from the DUT display center. (default is 0)
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :param camera_id: Name of the camera that is being used. (default is Camera1)
        :param analyzer: Name of the analyzer node to be used in blink detection.

        :return: Dictionary with keys: 'blink_frequency'.
        """

        analyzers = Node.find("analyzers")
        if analyzers is None:
            raise Exception("Analyzers node not found. Revise configuration.")

        blink_detector = Node.find_from(analyzers, analyzer)
        if blink_detector is None:
            raise Exception("Blink detector not found. Revise configuration.")

        frames, _ = self.record_video(duration, crop_left=crop_left, crop_upper=crop_upper,
                                      crop_right=crop_right, crop_lower=crop_lower, crop_unit=crop_unit,
                                      offset=(offset_x, offset_y), exposure=exposure, gain=gain, camera_id=camera_id)

        blink_frequency = blink_detector.analyze(frames=frames)
        return blink_frequency

    @json_out
    def post_search_text(self, pattern="", regexp=False, language='English', min_score=0.8, case_sensitive=True,
                         crop_left=None, crop_upper=None, crop_right=None, crop_lower=None, crop_unit=None,
                         exposure=None, gain=None, detector='abbyy', offset_x=0, offset_y=0, filter=None,
                         camera_id="Camera1"):
        """
        Search text pattern from the visible portion of the DUT screen.

        :param pattern: Text or pattern to find. Search all text with pattern "" (default).
        :param regexp: Use pattern as a regexp. [True | False (default)].
        :param language: OCR language e.g. "English" (default), "Finnish".
        :param min_score: Minimum score (confidence value). 0.0 - 1.0. Default is 0.8,
        value over 0.6 means the sequences are close matches.
        :param case_sensitive: Should the comparison be done case sensitive or not. [True (default) | False]
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :param detector: Name of text detector to use.
        :param offset_x: Take the picture with an offset in x from the DUT display center. (default is 0)
        :param offset_y: Take the picture with an offset in y from the DUT display center. (default is 0)
        :param filter: Name of filter to apply to the image before text search. None to use no filtering (default).
        :param camera_id: Name of the camera that is being used. (default is Camera1)
        :return: Dictionary with keys "success", "results" and "screenshot".

            Response body:
                success -- Always True
                results -- Array of Result objects
                screenshot -- Name of the screenshot

                The results array is ordered in page order i.e. text found from left to right and top to bottom.
                Note that this means that the first item might not have the highest score.

            Result object (dictionary):
                score -- Match score [0.0 .. 1.0]
                topLeftX_px -- Bounding box top left x coordinate in pixels
                topLeftY_px -- Bounding box top left x coordinate in pixels
                bottomRightX_px -- Bounding box bottom right x coordinate in pixels
                bottomRightY_px -- Bounding box bottom right y coordinate in pixels
                centerX_px -- Bounding box center x coordinate in pixels
                centerY_px -- Bounding box center y coordinate in pixels
                topLeftX -- Bounding box top left x coordinate in mm
                topLeftY -- Bounding box top left x coordinate in mm
                bottomRightX -- Bounding box bottom right x coordinate in mm
                bottomRightY -- Bounding box bottom right y coordinate in mm
                centerX -- Bounding box center x coordinate in mm
                centerY -- Bounding box center y coordinate in mm
        """
        screenshot = self.screenshot(camera_id, exposure=exposure, gain=gain, offset=(offset_x, offset_y))

        if crop_unit is not None:
            screenshot.crop(crop_left, crop_upper, crop_right, crop_lower, crop_unit)
            screenshot.save_image()

        # Filter image.
        if filter is not None:
            screenshot.filter(filter)

            # Save image so that user can inspect the effect of filtering.
            screenshot.save_image()

        results = search_text(screenshot.data, pattern, regexp, language, min_score, case_sensitive, detector)

        # Transform results from pixels (image context) to mm (DUT context).
        calculate_detection_result_coordinates(results, screenshot)

        for result in results["results"]:
            # Result kind is not needed.
            if "kind" in result:
                del result["kind"]

            # Margin value that allows some round-off errors but is not dangerous in most typical situations.
            margin = 10.0

            # Sanity check to make sure the detection coordinates are within DUT limits.
            if not self.is_point_inside(result["centerX"], result["centerY"], margin) or \
                    not self.is_point_inside(result["topLeftX"], result["topLeftY"], margin) or \
                    not self.is_point_inside(result["bottomRightX"], result["bottomRightY"], margin):
                raise Exception("Detection result is not within DUT limits.")

        results['screenshot'] = screenshot.name
        return results

    def is_point_inside(self, x, y, margin=0.0):
        """
        Test if 2D point is within DUT limits.
        :param x: X-coordinate in DUT context.
        :param y: Y-coordinate in DUT context.
        :param margin: Value added to DUT limits during the test. Positive value expands DUT size in the test.
        """
        return -margin <= x <= self.width + margin and -margin <= y <= self.height + margin

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    #
    # Compatibility add-on
    # Done for TAFF curved dut test cases
    # Which are requesting dut/data/screen_width etc.
    # Configurator will write values to dut/properties/data
    #
    @json_out
    def handle_path(self, method, path, **kwargs):
        log.info("HTTP %s /%s", method, path)

        if path[:4] != 'data':
            raise Exception("Not Found")
        path = path[4:]
        parts = path.split('/')

        if method == 'get':

            a = self.data
            for part in parts:
                if part == '':
                    continue
                try:
                    a = a[part]
                except:
                    raise Exception("Not Found")
            return a

        raise Exception("Not Found")

    def svg_data(self):
        return self._svg

    def set_svg_data(self, svg_data):
        """
        sets the corresponding svg data
        :param svg_data: svg as bytearray, or None if you want to remove the SVG.
        :return: new svg name
        """
        filename = self.name + ".svg"
        if svg_data is not None:
            self._svgregion = toolbox.dut.SvgRegion()
            files.write_data("dut_svg", filename, svg_data)
            self._svg = files.read_data("dut_svg", self.name + ".svg")
            svg_string = self._svg.decode("ascii")
            self._svgregion.load_string(svg_string=svg_string)
        else:
            self._svg = None
            files.delete_data("dut_svg", filename)

    def set_svg_scaling(self, svg_scale):
        """
        Sets scale factors for svg.
        :param svg_scale: Scale factors.
        """
        self.svg_scale = svg_scale

    @json_out
    def get_svg_data(self):
        """
        Return the svg file specified for the dut. If there is
        no specified file, return empty string
        :return: svg file or empty string
        """
        data = bytearray()
        if self._svg is not None:
            data += self._svg
        base64_data = base64.encodebytes(data)
        return base64_data.decode("ascii")

    @json_out
    def put_svg_data(self, base64_data: str = None):
        """
        Sets SVG file for the DUT
        :param base64_data: base64 encoded svg image, or None if you want to remove the current SVG.
        :return: "ok" / error
        """
        if base64_data is None:
            self.set_svg_data(None)
            return "ok"

        data = base64.decodebytes(base64_data.encode("ascii"))
        self.set_svg_data(data)
        return "ok"

    @json_out
    def put_svg_scaling(self, svg_scale):
        """
        Puts scale factors SVG's x and y axis.
        :param svg_scale: Scale factors.
        """
        self.set_svg_scaling(svg_scale)
        return "ok"

    @json_out
    def put_filter_points(self, points, region, margin=0):
        """
        Filter a list of points that are inside of DUT shape, given region and margin.
        :param points: List of (x, y) points, millimeters.
        :param region: Name of the region.
        :param margin: Margin inwards the given region, millimeters.
        :return: Filtered list of (x, y) points.
        """
        r = self._svgregion

        if r is None:
            return points

        region_object = r.region.get(region, None)

        # Use scaled contour to filter the points.
        contour = r.region_to_contour(region_object, 1000)

        scaled_contour = []
        for p in contour:
            scaled_contour.append([np.float32(p[0] * self._svg_scale[0]), np.float32(p[1] * self._svg_scale[1])])

        contour = np.asarray(scaled_contour)
        result = r.filter_points_contour(points, margin, contour)

        return result

    @json_out
    def put_filter_lines(self, lines, region, margin=0):
        """
        Filter list of (x1, y1, x2, y2) lines with given region and margin.
        The filter will cut lines to pieces that fit inside the region with given margin.
        One given line can result to none or several lines.
        :param lines: List of (x1, y1, x2, y2) lines, in millimeters.
        :param region: Name of the filter region.
        :param margin: Margin inwards the region, millimeters.
        :return: List of list of (x1, y1, x2, y2) lines (each given line results to a list of lines).
        """
        r = self._svgregion

        if r is None:
            return lines

        region_object = r.region.get(region, None)

        # Use scaled contour to filter the lines
        contour = r.region_to_contour(region_object, 1000)
        scaled_contour = []
        for p in contour:
            scaled_contour.append([np.float32(p[0] * self._svg_scale[0]), np.float32(p[1] * self._svg_scale[1])])

        contour = np.asarray(scaled_contour)

        result = []
        for line in lines:
            result.append(r.filter_line(line, contour, margin))

        return result

    @json_out
    def get_region_contour(self, region, num_points):
        """
        Return the given region as a list of (x, y) points.
        "contour" as in how OpenCV names the approximation of a shape as a point list:
        'Contours can be explained simply as a curve joining all the continuous points (along the boundary)'
        Can be used to OpenCV shape analysis or any other shape-analysis or geometric operation.
        :param region: Name of the region.
        :param num_points: Number of points to use on contour.
        :return: List of (x, y) contour points, in millimeters. Scaling is applied.
        """
        r = self._svgregion

        if r is None:
            return []

        region_object = r.region.get(region, None)
        if region_object is None:
            return []

        contour = r.region_to_contour(region_object, num_points)

        scaled_contour = []
        for p in contour:
            scaled_contour.append([np.float32(p[0] * self._svg_scale[0]), np.float32(p[1] * self._svg_scale[1])])

        contour = np.asarray(scaled_contour)

        return contour.tolist()

    def show_image(self, image):
        """
        Draws image to dut screen
        :param image: image as numpy array, bytes, or filename
        """
        self.dut_communication_server().show_image(self, image)

    def dut_communication_server(self):
        server = Node.find_class("DutServer")[0]
        return server

    def show_positioning_image(self, num_retrys=5):
        for i in range(num_retrys):
            try:
                return self.dut_communication_server().show_positioning_image(self)
            except Exception as e:
                if i >= num_retrys - 1:
                    raise e
                else:
                    log.error("Exception when showing positioning image: " + str(e) + " Retrying...")

                    # Sleep for a while before retry in case there is some temporary network glitch.
                    time.sleep(1.0)

    @json_out
    def get_show_positioning_image(self):
        params = self.show_positioning_image()
        return params

    @json_out
    def put_show_image(self, image: None):
        """
        Shows image on DUT screen.
        If image is bytes object, use:
        image = base64.decodebytes(image.encode("ascii"))

        :param image: base64 encoded data. None will empty the screen
        :return: "ok" / error
        """
        if image is not None and len(image) > 0:
            image = base64.decodebytes(image.encode("ascii"))
        else:
            image = None
        self.show_image(image)
        return "ok"

    @json_out
    def get_info(self):
        """
        Read raw info from DUT device
        :return: info dictionary
        """
        return self.dut_communication_server().info(self.name)

    @json_out
    def get_touches(self):
        """
        Gets list of touches since last call of this function.
        If you want to clear the touches buffer, call this function and discard the results.

        Current OptoTouch application supports the following fields:
            x           Touch x-coordinate. Touch resolution is the same as screen pixel resolution.
            y           Touch y-coordinate. Touch resolution is the same as screen pixel resolution.
            pressure    Touch pressure, float value in range 0..1, device dependent and not any standard unit.
            id          Touch id. Sequential number where every new finger to touch the screen
                        takes the first free positive number as id.
            action      Numbered enumeration where:
                        0 = touch start
                        1 = touch end
                        2 = touch move / stays pressed at point
                        3 = touch cancelled
            orientation Stylus event; angle in radians where 0 == north, -pi/2 = west, pi/2 = east
            azimuth     Stylus event; angle in radians where 0 == normal to surface and M_PI/2 is flat to surface.
            distance    Stylus event; 0.0 indicates direct contact and larger values
                                      indicate increasing distance from the surface.

        :return: (dict) where key 'fields' is a list of touch field names.
                    and where key 'touches' is a list of touches. One touch is an array of values.
        """
        dutserver = Node.find_class("DutServer")[0]
        touches = dutserver.touches(self.name)
        return touches

    @json_out
    def get_connected(self):
        """
        Returns connection status.
        If DUT is connected over tcp/ip connection you can use APIs like show_image, get_touches
        :return: (bool) True if connected
        """
        dutserver = self.dut_communication_server()
        return dutserver.is_dut_connected(self.name)

    # No @json_out because robot.get_position() already has it.
    def get_robot_position(self, robot_name="Robot1"):
        """
        Get the current robot position in DUT coordinates.
        DEPRECATED: Added for client compatibility.
        :param robot_name: Name of robot whose position to get.
        :return: Robot position in DUT coordinates.
        """
        return Node.find(robot_name).get_position(self.name)

    @json_out
    def get_list_buttons(self):
        """
        List button names of the current DUT.

        :return: List of button names.
        """

        child_buttons = []

        for button in self.object_children.values():
            if button.__class__.__name__ == "PhysicalButton":
                child_buttons.append(button.name)

        return child_buttons

    @json_out
    def put_move(self, x, y, z, tilt=None, azimuth=None, robot_name="Robot1"):
        """
        Moves in to given DUT position via straight path.
        DEPRECATED: Added for client compatibility.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT.
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param robot_name: Name of robot to move.
        """

        robot = Node.find(robot_name)

        robot._move(x=x, y=y, z=z, tilt=tilt, azimuth=azimuth, context=self.name)

    def remove(self):
        """
        Deletes dut and associated physical buttons
        """
        parent = self.parent

        # Loop through DUT:s object_children and remove physical buttons.
        item_list = list(self.object_children.values())
        for item in item_list:
            if isinstance(item, PhysicalButton):
                item.remove()

        parent.remove_child(self)

    def validate_orientation(self, robot):
        # Check if DUT local z-vector direction wrt robot base frame is within allowed robot-specific limit
        transform = robotmath.translate(robotmath.identity_frame(), self, robot.object_parent)

        if np.degrees(tr.angle_between_vectors(transform.A[:3, 2], np.array([0, 0, 1]))) \
                > robot.maximum_dut_tilt_angle:
            raise Exception("DUT orientation in the robot workspace is invalid.")