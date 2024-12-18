import copy
import logging
from typing import List, Optional

from typing_extensions import Literal

from tntserver.drivers.cameras.camera_optocamera import Camera_Optocamera

log = logging.getLogger(__name__)
import cv2
import queue
import io
from optovision.auto_exposure.exposure_calibrator import ExposureCalibration

from tntserver.Nodes.Node import *

try:
    from tntserver.drivers.cameras.camera_yasler import Camera_Yasler
except ImportError as e:
    log.warning("camera_yasler not available")
    Camera_Yasler = None

try:
    from tntserver.drivers.cameras.camera_optocamera_basler import Camera_Optocamera_Basler
except ImportError as e:
    log.warning("camera_optocamera_basler not available")
    Camera_Optocamera_Basler = None

from tntserver.drivers.cameras.camera_simulator import Camera_Simulator
from tntserver.drivers.cameras.camera_ximea import Camera_Ximea
from tntserver.drivers.cameras.camera_http import Camera_Http
from tntserver.drivers.cameras.camera import CameraInfo, CameraFrame
from tntserver.Nodes.TnT.Image import search_text, find_objects, Image, image_data_to_http_response
from tntserver.Nodes.Mount import Mount
from tntserver.Nodes.TnT.Workspace import get_node_workspace
import time
# This is used for unit testing only
from tntserver.drivers.cameras.camera_test import CameraTestStub


# Interpolation methods used in camera image scaling.
# Following has been measured from scaling 20MP image to half size: nearest 2 ms, linear 7 ms, cubic 9 ms.
INTERPOLATION_NEAREST = "nearest"
INTERPOLATION_LINEAR = "linear"
INTERPOLATION_CUBIC = "cubic"


def numpy_array_to_bytes(array):
    b = io.BytesIO()

    np.save(b, array)

    return b.getvalue()


def rotate_target_image_to_camera(img, target_frame, target_width, target_height, ppmm, margin, flags=cv2.INTER_LINEAR):
    """
    Rotate rectangular target that is visible in camera so that target is aligned with the camera image.
    :param img: Image where target is displayed.
    :param target_frame: Target frame in camera context.
    :param target_width: Target width in mm.
    :param target_height: Target height in mm.
    :param ppmm: Camera ppmm.
    :param margin: Margin in mm. Must be non-negative. Adds margin to target.
    :param flags: Flags for OpenCV warpPerspective.
    :return: Aligned image.
    """

    assert margin >= 0

    shape = img.shape
    h, w = shape[:2]

    # Target origin (corner).
    target_width += margin * 2
    target_height += margin * 2

    # Compute target corners in camera context.
    corners = [[-margin, -margin], [-margin + target_width, -margin],
               [-margin + target_width, -margin + target_height], [-margin, -margin + target_height]]

    corners_image = [target_frame * robotmath.xyz_to_frame(c[0], c[1], 0) for c in corners]

    # Transform corners to image pixel coordinates.
    # Negate x-coordinate when mapping from local camera coordinates to pixel coordinates.
    # The convention is that image pixel x-coordinates increase along negative camera mount x-direction.
    for i in range(len(corners_image)):
        x, y, _ = robotmath.frame_to_xyz(corners_image[i])

        x = -x * ppmm + w / 2
        y = y * ppmm + h / 2

        corners_image[i] = [x, y]

    corners_output_image = np.array([[0, 0],
                                     [target_width * ppmm, 0],
                                     [target_width * ppmm, target_height * ppmm],
                                     [0, target_height * ppmm]])

    # Find homography between rotated and upright target.
    H, mask = cv2.findHomography(np.array(corners_image), corners_output_image)

    # Warp image to make target appear upright.
    img = cv2.warpPerspective(img, M=H, dsize=(int(target_width * ppmm), int(target_height * ppmm)),
                               flags=flags,
                               borderMode=cv2.BORDER_CONSTANT)

    return img


def per_pixel_maximum(frames: List[CameraFrame]) -> np.ndarray:
    """
    Get per-pixel maximum of recorded video. Each pixel in resulting image has an RGB value corresponding to its
    maximum brightness.
    :param frames: Video recording as a list of CameraFrames.
    :return: Resulting image as a numpy array.
    """
    # Transform CameraFrames into a numpy array with axes (t, y, x, b, g, r).
    bgr_images = np.array([frame.bgr() for frame in frames])

    # Get brightness values and look for maximum over the time axis.
    bw_images = np.dstack([frame.mono() for frame in frames])
    max_pixels = np.argmax(bw_images, axis=2)

    max_frame = np.zeros_like(bgr_images[0, ...])
    y = np.arange(max_frame.shape[0])
    x = np.arange(max_frame.shape[1])
    y, x = np.meshgrid(y, x)

    # Set the rgb values of each pixel according to the maximum brightness.
    max_frame[y, x, ...] = bgr_images[max_pixels[y, x], y, x, ...]

    return max_frame


class Camera(Node):
    """
    TnT™ Compatible Camera resource
    Should work together with
    - TnT Sequencer
    - TnT Positioning Tool
    - TnT UI

    Camera coordinate convention:
    Camera node's parent frame determines the camera mount frame. Convention is that
    camera mount frame local z-axis points in the direction of the camera view (towards imaging target).
    When looking along camera view, the local x-axis of camera mount frame points to the left meaning that
    the pixel x-coordinates increase along negative local x-axis direction. The local y-axis direction points down
    in the image meaning that pixel y-coordinates increase along positive local y-axis direction.
    """

    def __init__(self, name):
        super().__init__(name)
        self._driver = None
        self._camera_open = False
        self._calibration = None
        self.camera_info = None
        self._continuous_capture = False
        self._continuous_capture_params = {}
        self._continuous_capture_lock = threading.Lock()
        self.max_stream_fps = 30

    def _init(self, driver: str, flipx: bool = False, flipy: bool = False, rotate: bool = False,
              retry_count=10, **kwargs):
        """
        Standard Node init function
        arguments from configuration node arguments

        :param driver: name of the driver, ximea, basler, http, simulator
        :param flipx: mirror x-coordinates of the image
        :param flipy: mirror y-coordinates of the image
        :param rotate: rotate image 90 degrees
        :param retry_count: Number of times to retry image capture in case of any errors.
        :param kwargs: optional arguments focal_length, exposure, gain for every camera,
                        ip_address, serial_number, etc. depending of the driver
        """
        camera_info = CameraInfo()

        # get some (optional) defaults
        camera_info.focal_length = kwargs.pop("focal_length", 8)
        exposure = kwargs.pop("exposure", 0.1)
        gain = kwargs.pop("gain", 0)
        self._flipx = flipx
        self._flipy = flipy
        self._rotate = rotate

        # find driver class
        cameras = {
            "ximea": Camera_Ximea,
            "yasler": Camera_Yasler,
            "optocamera": Camera_Optocamera,
            "optocamera-basler": Camera_Optocamera_Basler,
            "http": Camera_Http,
            "simulator": Camera_Simulator,
            "test": CameraTestStub
        }
        if driver not in cameras:
            raise(Exception("unknown camera driver {}".format(driver)))
        driver_cls = cameras[driver]

        # create driver instance
        driver_instance = driver_cls(**kwargs)

        # Set driver retry count.
        driver_instance.retry_count = retry_count

        # Simulator driver uses camera node name to locate simulator camera object.
        if driver == "simulator":
            driver_instance.name = self.name

        # read camera info values from driver
        if not rotate:
            camera_info.pixel_width, camera_info.pixel_height = driver_instance.resolution
            camera_info.sensor_width, camera_info.sensor_height = driver_instance.sensor_size
        else:  # the image is rotated -> width and height switch values
            camera_info.pixel_height, camera_info.pixel_width = driver_instance.resolution
            camera_info.sensor_height, camera_info.sensor_width = driver_instance.sensor_size

        self.camera_info = camera_info

        # set rest of the member variables and init calibration (if any)
        self._driver = driver_instance
        self._reload_calibration()

        # Set exposure and gain values
        self.exposure = exposure
        self.gain = gain

    def still(self, undistorted: bool, exposure, gain, flipx=None, flipy=None, rotate90=None, width=None,
              height=None, scaling=None, zoom=None, interpolation=INTERPOLATION_CUBIC):

        with self._continuous_capture_lock:
            if not self._camera_open:
                self._driver.open()

            if self._continuous_capture:
                self._driver.stop_continuous()

            # Update incoming gain and exposure values to camera driver
            if gain is not None:
                self.gain = gain
            if exposure is not None:
                self.exposure = exposure

            image = self._driver.capture_image()

            if self._continuous_capture:
                # Restore gain and exposure if they are defined before restarting continuous capture.
                if "gain" in self._continuous_capture_params:
                    self.gain = self._continuous_capture_params["gain"]

                if "exposure" in self._continuous_capture_params:
                    self.exposure = self._continuous_capture_params["exposure"]

                self._driver.start_continuous()

            if not self._camera_open:
                self._driver.close()

        if flipx is None:
            flipx = self._flipx

        if flipy is None:
            flipy = self._flipy

        if rotate90 is None:
            rotate90 = self._rotate

        image = self.image_transformations(image, flipx, flipy, rotate90, width, height, scaling, zoom, undistorted,
                                           interpolation)

        return image

    def image_transformations(self, image, flipx, flipy, rotate90, width, height,  scaling, zoom, undistorted,
                              interpolation):
        """
        Does all the image transformations to the copy of the image and returns the transformed image
        :param image: the raw image
        :param flipx: mirror x-coordinates of the image
        :param flipy: mirror y-coordinages of the image
        :param rotate90: rotate the image 90 degrees
        :param width: the new width of the image (px), is overrun by scaling if that is defined
        :param height: the new height of the image (px), is overrun by scaling if that is defined
        :param scaling: scaling factor for the image (0.5 halves the image size), keeps aspect ratio,
        overruns width and height
        :param zoom: zoom to be used
        :param undistorted: if True to the distortion fix matrix is applied, if not the distortion is not fixed
        :param interpolation: Interpolation method ('nearest', 'linear', 'cubic').
        :return: transformed image
        """

        # Numpy flip is fast as it only returns a view but for some reason that result in cv2.resize() can
        # make resize take 10x more time. It seems to be faster to use cv2.flip() when cv2.resize() is also used.
        # Note! It matters in which order these flippings and rotate are done
        if flipx and flipy:
            image = cv2.flip(image, -1)
        else:
            if flipx:
                image = cv2.flip(image, 1)
            elif flipy:
                image = cv2.flip(image, 0)
            else:
                image = image.copy()

        if rotate90:
            image = np.rot90(image, 1)

        # distortion correction must be made to whole image before cropping and scaling since
        # the image used for calibration is not cropped or scaled (rotated and flipped only)
        if undistorted:
            if self._distortion_map is None:
                raise ValueError("no distortion correction made")

            mapx, mapy = self._distortion_map
            image = cv2.remap(image, mapx, mapy, cv2.INTER_CUBIC)

        resize_w_h = False
        resize_scaling = False

        h, w = image.shape[:2]

        # If both scaling and width and height have been defined, the scaling is used and others ignored
        if (width is not None or height is not None) and scaling is not None:
            log.warning("The image size has too many parameters, using the scaling and ignoring width and height")

        # Scaling the picture based on width and height or scaling
        if scaling is None:
            if width is None:
                width = w
            else:
                resize_w_h = True
            if height is None:
                height = h
            else:
                resize_w_h = True
        else:  # we use the scaling if it is available
            width = int(round(w * scaling))
            height = int(round(h * scaling))
            resize_scaling = True

        # If the image is rotated and resized by width and height parameters
        # it gets quished unless the width and height are changed too
        if rotate90 and resize_w_h:
            width, height = height, width

        if zoom is None:
            zoom = 1

        # image cropping
        if zoom > 1:
            crop_width = int(w / zoom)
            crop_height = int(h / zoom)

            crop_width = int(crop_width / 2) * 2
            crop_height = int(crop_height / 2) * 2

            x = int((w - crop_width) / 2)
            y = int((h - crop_height) / 2)
            # TODO why is there +1?
            image = image[y:y + crop_height + 1, x:x + crop_width + 1]

        # image scaling
        if resize_w_h or resize_scaling:
            if interpolation == INTERPOLATION_NEAREST:
                interpolation = cv2.INTER_NEAREST
            elif interpolation == INTERPOLATION_LINEAR:
                interpolation = cv2.INTER_LINEAR
            elif interpolation == INTERPOLATION_CUBIC:
                interpolation = cv2.INTER_CUBIC
            else:
                assert False

            image = cv2.resize(image, (int(width), int(height)), interpolation=interpolation)


        return image

    def get_still(self, filetype: str="jpg", width=None, height=None, zoom=None, undistorted: bool = False,
                  exposure: float = None, gain: float = None, scaling=None, interpolation: str = INTERPOLATION_CUBIC,
                  flipx: Optional[bool] = None, flipy: Optional[bool] = None, rotate90: Optional[bool] = None,
                  duration: Optional[float] = None):
        """
        Takes a photo. This function opens camera automatically, no need to use open() -function. In case the still is
        taken in the middle of stream view, a sleep-command might be needed before taking still to ensure that all
        the images from continuous capture are processed before clearing the queue.
        :param filetype: jpg, png, raw(np.array).
        :param width: optional target image width. both width and height needed
        :param height: optional target image height. both width and height needed
        :param zoom: optional image zoom.
        :param undistorted: true/false, only available after undistort called succesfully
        :param exposure: exposure in seconds. If not set, uses last exposure used.
        :param gain: gain value. If not set, uses last gain value used.
        :param scaling: Camera image scaling factor in range [0, 1].
        :param interpolation: Interpolation method ('nearest', 'linear', 'cubic').
        :param flipx: mirror x-coordinates of the image
        :param flipy: mirror y-coordinages of the image
        :param rotate90: rotate the image 90 degrees
        :param duration: Video capture duration in seconds. Per-pixel maximum will be taken over the video.
        :return: image in 'filetype' format

        In case filetype is "bytes", the returned image is bytearray that can be transformed into numpy array as:

        data = camera_client.take_still(filetype="bytes")
        w = int.from_bytes(data[0:4], byteorder="big")
        h = int.from_bytes(data[4:8], byteorder="big")
        d = int.from_bytes(data[8:12], byteorder="big")
        data = np.frombuffer(data[12:], dtype=np.uint8).reshape((h, w, d))
        """

        if duration is None:
            if isinstance(undistorted, str):
                undistorted = True if undistorted == "true" else False

            flipx = self._flipx if flipx is None else flipx
            flipy = self._flipy if flipy is None else flipy
            rotate90 = self._rotate if rotate90 is None else rotate90

            log.debug("Camera {} still".format(self.name))
            image = self.still(undistorted, exposure, gain, flipx, flipy, rotate90, width, height, scaling, zoom,
                               interpolation)
        else:
            frames = self.record_video(duration, width=width, height=height, zoom=zoom, scaling=scaling,
                                       undistorted=undistorted, exposure=exposure, gain=gain)
            image = per_pixel_maximum(frames)

        return image_data_to_http_response(filetype, image)

    def record_video(self, duration: float, width: Optional[int] = None, height: Optional[int] = None,
                     zoom: Optional[float] = None, undistorted: bool = False,
                     exposure: Optional[float] = None, gain: Optional[float] = None, scaling: float = 1,
                     interpolation: Literal["nearest", "linear", "cubic"] = INTERPOLATION_NEAREST,
                     trigger_type: Literal["SW", "HW"] = "SW", target_context: Optional[str] = None,
                     target_context_margin: float = 0) -> List[CameraFrame]:
        """
        Record video from camera. The function will wait until the recording is done and the return the recorded frames.

        :param duration: Video capture duration in seconds.
        :param width: Width of image or None to use full image width.
        :param height: Height of image or None to use full image width.
        :param zoom: Zoom factor or None for no zoom.
        :param undistorted: Use distortion calibration to undistort?
        :param exposure: Camera exposure or None to use Camera node exposure state.
        :param gain: Camera gain or None to use Camera node exposure state.
        :param scaling: Scaling factor or None for no scaling.
        :param interpolation: Interpolation method ("nearest", "linear" or "cubic"). May affect image stream performance.
        :param trigger_type: Camera triggering based on internal timer "SW" or external trigger "HW".
        :param target_context: Possible DUT target for image context transformation, "None" means no transformation. (Default: None)
        :param target_context_margin: Margin for context transformation. (Default: 0)

        :return: List of captured images as CameraFrames.
        """

        frames = []

        def callback(*args):
            # Optocamera has a different signature for the callback function.
            if len(args) == 2:
                frame, error = args
            else:
                cam, frame, error = args

            # Add the frame to list. Image transformations are done afterwards as they are too slow to do in realtime.
            frames.append(CameraFrame(frame.bgr(), frame.timestamp))

            return True

        with self._continuous_capture_lock:
            if not self._camera_open:
                self._driver.open()

            # Need to stop video stream while recording video.
            if self._continuous_capture:
                self._driver.stop_continuous()

            if gain is not None:
                self.gain = gain
            if exposure is not None:
                self.exposure = exposure

            self._driver.start_continuous(callback=callback, trigger_type=trigger_type)

            # Wait until capturing is done.
            time.sleep(duration)

            self._driver.stop_continuous()

            if self._continuous_capture:
                # Restore gain and exposure if they are defined before restarting continuous capture.
                if "gain" in self._continuous_capture_params:
                    self.gain = self._continuous_capture_params["gain"]

                if "exposure" in self._continuous_capture_params:
                    self.exposure = self._continuous_capture_params["exposure"]

                # Restart video stream.
                self._driver.start_continuous()

        # Parameters for context coordinate transformation.
        node = None
        target_frame = None
        if target_context is not None:
            node = Node.find(target_context)
            # Transform DUT frame to camera context.
            target_frame = robotmath.translate(node.frame, node.object_parent, self)

        images = []
        for frame in frames:
            image = self.image_transformations(frame.bgr(), self._flipx, self._flipy, self._rotate, width, height,
                                               scaling, zoom, undistorted, interpolation)

            if node is not None:
                # Rotate image to the target context.
                # TODO: check that this is correct
                image = rotate_target_image_to_camera(image, target_frame, node.width, node.height, self.ppmm * scaling,
                                                      target_context_margin)

            images.append(CameraFrame(image, frame.timestamp))

        return images

    @json_out
    def put_start_continuous(self, width=None, height=None, zoom=None, undistorted: bool = False,
                             exposure: float = None, gain: float = None, scaling=None,
                             interpolation=INTERPOLATION_NEAREST, trigger_type="SW", target_context=None,
                             target_context_margin=0):
        """
        Start continuous camera image capture.
        Note that Camera node argument max_queue_size should be small such as 1 to avoid latency.

        The mjpeg stream can be retrieved via GET request at URL
        http://127.0.0.1:8000/tnt/workspaces/ws/cameras/Camera1/mjpeg_stream
        where Camera1 is the name of the camera node.
        This can be used in HTML image element to view the stream.
        Be aware that browser can cache the image so if may be necessary to add e.g. current time as
        parameter to the URL by importing time library and adding '?'+str(time.time()) to the URL

        :param width: Width of image or None to use full image width.
        :param height: Height of image or None to use full image width.
        :param zoom: Zoom factor or None for no zoom.
        :param undistorted: Use distortion calibration to undistort?
        :param exposure: Camera exposure or None to use Camera node exposure state.
        :param gain: Camera gain or None to use Camera node exposure state.
        :param scaling: Scaling factor or None for no scaling.
        :param interpolation: Interpolation method ("nearest", "linear" or "cubic"). May affect image stream performance.
        :param trigger_type: Camera triggering based on internal timer "SW" or external trigger "HW".
        :param target_context: Possible DUT target for image context transformation, "None" means no transformation. (Default: None)
        :param target_context_margin: Margin for context transformation. (Default: 0)
        """
        if not self._continuous_capture:
            self._driver.start_continuous(callback=None, trigger_type=trigger_type)
            self._continuous_capture = True
            self._continuous_capture_params = {
                "filetype": "jpg",
                "width": width,
                "height": height,
                "zoom": zoom,
                "undistorted": undistorted,
                "exposure": self.exposure if exposure is None else exposure,
                "gain": self.gain if gain is None else gain,
                "scaling": scaling,
                "from_buffer": True,
                "buffer_timeout": 0.01,
                "interpolation": interpolation,
                "target_context": target_context,
                "target_context_margin": target_context_margin
            }

            if isinstance(undistorted, str):
                self._continuous_capture_params["undistorted"] = True if undistorted == "true" else False

    @thread_safe
    @json_out
    def put_stop_continuous(self):
        """
        Stop continuous capture that was started by start_continuous().
        """
        self._driver.stop_continuous()
        self._continuous_capture = False

    @thread_safe
    @json_out
    @multipart(True)
    def get_mjpeg_stream(self, http_handler):
        """
        Start streaming camera images in 'motion JPEG' format.
        Motion JPEG stream will be delivered as multipart HTTP response.

        NOTE:
        - put_start_continuous() should be called before this function
        - this function will run until stop_continuous() is called
        """
        http_handler.send_response(200)
        http_handler.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
        http_handler.end_headers()

        while self._continuous_capture:
            start_time = time.time()
            try:
                with self._continuous_capture_lock:
                    if not self._camera_open:
                        self._driver.open()

                    self.gain = self._continuous_capture_params["gain"]
                    self.exposure = self._continuous_capture_params["exposure"]

                    image = self._driver.get_image_from_buffer(timeout=0.01)

                    if not self._camera_open:
                        self._driver.close()

                width = self._continuous_capture_params["width"]
                height = self._continuous_capture_params["height"]
                scaling = self._continuous_capture_params["scaling"]
                zoom = self._continuous_capture_params["zoom"]
                undistorted = self._continuous_capture_params["undistorted"]
                interpolation = self._continuous_capture_params["interpolation"]
                target_context = self._continuous_capture_params["target_context"]
                target_context_margin = self._continuous_capture_params["target_context_margin"]


                image = self.image_transformations(image, self._flipx, self._flipy, self._rotate, width, height,
                                                   scaling, zoom, undistorted, interpolation)

                if target_context is not None:
                    dut = Node.find(target_context)
                    # Transform DUT frame to camera context.
                    target_frame = robotmath.translate(dut.frame, dut.object_parent, self)

                    # Rotate image so that DUT in the image is aligned with the resulting image.
                    image = rotate_target_image_to_camera(image, target_frame, dut.width, dut.height, self.ppmm*scaling,
                                                          target_context_margin)

                # Resolution greatly affects stream latency.
                t, img = image_data_to_http_response("jpg", image)

                # TODO: Check this with color camera
                #img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)

                boundary = "--jpgboundary\r\n".encode()
                http_handler.wfile.write(boundary)
                http_handler.send_header('Content-type','image/jpeg')
                http_handler.send_header('Content-length', len(boundary) + len(img))
                http_handler.end_headers()
                http_handler.wfile.write(img)

            except queue.Empty:
                pass  # If there was no image in queue then do nothing
            except Exception as e:
                # In case of any exception, log warning but keep streaming alive.
                # It is common to get some capture error if e.g. inter-packet delay is slightly too small.
                log.warning(e)

            # Wait to the end of frame time
            frame_time_remaining = 1 / self.max_stream_fps - (time.time() - start_time)
            if frame_time_remaining > 0:
                time.sleep(frame_time_remaining)

    @json_out
    def put_set_mjpeg_stream_parameter(self, key, value):
        """
        Update continuous capture parameter (e.g. gain, exposure, DUT context) while stream is running.
        :param key: A key in the continuous capture parameter list
        :param value: Value for the parameter
        :return:
        """
        if key not in self._continuous_capture_params:
            raise NodeException('Continuous capture parameter with key {} not found.'.format(key))
        else:
            self._continuous_capture_params[key] = value

    @json_out
    def put_move_with_robot(self, frame, context: str):
        """
        Move camera to target specified by frame and context at focus height.
        DEPRECATED: Parallel to move().
        :param frame: target frame
        :param context: target context
        :param robot_name: name of the robot to use in movement
        :return:
        """
        if isinstance(frame, str):
            frame = json.loads(frame)
        frame = np.matrix(frame)
        context = Node.find(context)
        robot = self.find_object_parent_by_class_name("Robot")
        self.move_with_robot(frame, context, robot)

    def move_with_robot(self, frame: np.matrix, context: Node, robot: Node, optional_z=None):
        if optional_z is not None:
            frame.A[2, 3] = optional_z

        # TODO: Is robot.object_parent correct context in general?
        frame = robotmath.translate(frame, context, robot.object_parent)

        # Camera must be child of Mount node.
        camera_mount = self.object_parent
        assert type(camera_mount) == Mount

        # Use camera frame as tool frame for the movement.
        # Tool frame needs to be specified here explicitly in case there are multiple cameras attached
        # to the same kinematic mount point.
        robot.move_frame(frame, robot.object_parent, camera_mount.mount_point, tool_frame=self.frame)

    @json_out
    def put_move(self, x, y, z, context: str = "tnt"):
        """
        Move camera focus point to given position (x, y, and z-coordinate) in a given context.
        :param x: Target x coordinate in a given context.
        :param y: Target y coordinate in a given context.
        :param z: Target z coordinate in a given context.
        :param context: Name of the target context.
        """
        frame = robotmath.pose_to_frame(robotmath.xyz_to_frame(x, y, z))

        frame = np.matrix(frame)
        context = Node.find(context)
        robot = self.find_object_parent_by_class_name("Robot")

        self.move_with_robot(frame, context, robot)

    @json_out
    def put_open(self):
        """
        Open camera for use.
        After the camera has been opened, sequential images can be taken quickly.
        """
        log.info("Camera {} open".format(self.name))
        self._driver.open()
        self._camera_open = True

    @json_out
    def put_close(self):
        """
        Shuts down the camera.
        """
        log.info("Camera {} close".format(self.name))
        self._driver.close()
        self._camera_open = False

    @json_out
    def get_info(self):
        info = self.camera_info.to_dict()
        return info

    @json_out
    def put_parameters(self, parameters):
        """
        Set camera parameters.
        See get_parameters.
        :param parameters: Parameter dictionary.
        :return: {'status': 'ok'}
        """
        log.debug("Setting camera parameters {}".format(parameters))
        self._driver.set_parameters(parameters)
        return {'status': 'ok'}

    @json_out
    def get_parameters(self, parameters=None):
        """
        Get given set of parameters from camera. Input dict indicates which parameters are retrieved.
        :param parameters: Additional arguments to indicate which parameters should be retrieved from camera.
            Values are ignored. List cannot be passed into HTTP GET that only has arguments and no body.
        :return: Dictionary of requested parameters and their values.
        """

        #TODO: This function utilizes drivers set_parameters and some drivers may not implement it.
        #      This has been implemented with HSUP and yasler in mind. Overall, the camera driver hassle would need
        #      refactoring as information can be retrieved with get_info or get_self, or through some properties.

        # Get the keys of the kwargs as they are a list of strings representing parameters to retrieve.
        # We'll completely ignore the values as they have no meaning.
        # When passing dict via HTTP request it is serialized into JSON formatted string. Need to use eval instead of json.loads() due to use of single-quotes.
        if isinstance(parameters, str):
            parameters = eval(parameters)

        params_to_retrieve = parameters.keys()
        params = self._driver.get_parameters(params_to_retrieve)
        log.debug("Getting camera parameters {}".format(params))
        return {'status': 'ok',
                'params': params}

    @json_out
    def put_parameter(self, name, value):
        """
        Set parameter value.
        :param name: Name of the parameter to set.
        :param value: Value to set to the parameter.
        :return: {'status': 'ok'}
        """
        self._driver.set_parameters({name: value})
        return {'status': 'ok'}

    @json_out
    def get_parameter(self, name):
        """
        Get parameter value.
        :param name: Name of the parameter to be read.
        :return: {'status': 'ok', 'params': parameter_dictionary}.
        """
        params = self._driver.get_parameters([name])
        log.debug("Getting camera parameters {}".format(params))
        return {'status': 'ok',
                'params': params}

    @property
    def calibration(self):
        return self._calibration

    @calibration.setter
    def calibration(self, calibration: dict):
        """
        set camera calibration information
        :param calibration: dictionary containing
            - intrisic parameters
            - extrisic parameters
            - pixels per millimeter ( at focus distance )
        """

        self._calibration = calibration
        self._reload_calibration()

    @property
    @private
    def pixel_width(self):
        return self.camera_info.pixel_width

    @property
    @private
    def pixel_height(self):
        return self.camera_info.pixel_height

    @property
    @private
    def focus_height(self):
        return self._calculate_focus_distance()

    # Same as focus_height. Added for sequence generator support!
    @property
    @private
    def focus_distance(self):
        return self._calculate_focus_distance()

    # Convenience property, not meant to be saved to configuration
    # (already in calibration info)
    @property
    @private
    def ppmm(self):
        value = 0
        if self._calibration is not None:
            value = self.calibration.get("ppmm", 0)
        return value

    @json_out
    def get_focus_height(self):
        """
        Get camera focus height (distance)
        :return: Focus height in mm.
        """
        return self.focus_height

    def _calculate_focus_distance(self):
        """
        :return: distance in millimeters between tool tip and camera focus point
                Z-coordinates in workspace coordinate system. i.e. how much to raise
                robot when tool tip touches target to get camrea to focus.
        """
        robot = self.find_object_parent_by_class_name("Robot")

        if robot is None:
            ws = get_node_workspace(self)

            nodes = Node.find_class_from(ws, "Robot")

            if len(nodes) == 0:
                raise Exception("Could not find robot nodes for focus distance calculation.")

            robot = nodes[0]

        f_camera = robotmath.translate(robotmath.identity_frame(), self, Node.root)
        f_robot = robot.effective_frame

        z_camera = f_camera.A[2, 3]
        z_robot = f_robot[2, 3]

        # z_camera - z_robot is how much z must be added to rise to focus height
        # and results always in negative number
        # but focus_distance and focus_height are positive numbers
        focus_distance = float(np.abs(z_camera - z_robot))

        return focus_distance

    def _reload_calibration(self):
        if self._calibration is None:
            return

        if self.camera_info is None:
            return

        w = self.camera_info.pixel_width
        h = self.camera_info.pixel_height

        try:
            intrinsic = np.array(self._calibration["intrinsic"])
        except KeyError:
            f = self.camera_info.focal_length
            intrinsic = np.array([[f, 0.0, 0.5 * w],
                                  [0.0, f, 0.5 * h],
                                  [0.0, 0.0, 1.0]])

        try:
            dist_coeffs = np.array(self._calibration["dist_coeffs"])
        except KeyError:
            dist_coeffs = np.zeros(4)

        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(
            intrinsic, dist_coeffs, (w, h), 0, (w, h),
            centerPrincipalPoint=True)

        mapx, mapy = cv2.initUndistortRectifyMap(
            intrinsic, dist_coeffs, None, newcameramtx, (w, h), cv2.CV_32FC1)

        self._distortion_map = (mapx, mapy)

    @json_out
    def get_detect_icon(self, icon: str, confidence: float = 0.75, context=None, detector: str = 'halcon', exposure=None, gain=None, **kwargs):
        """
        DEPRECATED!
        List of detected objects with their positions in relation to given context.
        :param icon: Name of the icon. You can teach new icons with TnT UI.
        :param confidence: Confidence factor 0..1 where 1 is very confident. Normal confidence is about 0.7.
        :param context: Returned positions are relative to this context.
        :param detector: Detector name as string, like "halcon".
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :return: List of detected objects.
        """
        log.warning("API method 'detect_icon()' is deprecated. Use Dut.find_objects() or Camera.screenshot() and Image.find_objects() instead.")

        _, image = self.get_still(filetype="none", undistorted=True, exposure=exposure, gain=gain, **kwargs)

        detector_results = find_objects(image=image, icon_name=icon, min_score=confidence, detector=detector)

        # convert pixel boxes to camera coordinate system
        ppmm = self.ppmm
        w, h = self.camera_info.pixel_width, self.camera_info.pixel_height

        results = []

        for detector_result in detector_results["results"]:
            result = {
                "confidence": detector_result["score"],
                "scale": detector_result["scale"],
                "angle": detector_result["angle"],
                "center_x": detector_result["centerX_px"],
                "center_y": detector_result["centerY_px"],
                "detector": "Halcon",
                "duration": 0,
                "topLeftX_px": detector_result["topLeftX_px"],
                "topLeftY_px": detector_result["topLeftY_px"],
                "bottomRightX_px": detector_result["bottomRightX_px"],
                "bottomRightY_px": detector_result["bottomRightY_px"]
            }

            x0, y0 = detector_result["topLeftX_px"], detector_result["topLeftY_px"]
            x1, y1 = detector_result["bottomRightX_px"], detector_result["bottomRightY_px"]

            # box_px in pixels
            result["box_px"] = [x0, y0, x1, y1]

            # camera frame pointing down, x-axis pointing left
            # pose and size_mm in millimeters
            x0, y0 = -(x0 - w / 2) / ppmm, (y0 - h / 2) / ppmm
            x1, y1 = -(x1 - w / 2) / ppmm, (y1 - h / 2) / ppmm

            # at this point box is guaranteed to be in straight position, after context transform it is not.
            w_mm = x1 - x0
            h_mm = y1 - y0

            if context is not None:
                # transform coordinates to context
                source = self
                target = Node.find(context)
                if target is None:
                    raise Exception("context not found")

                ftl = robotmath.xyz_to_frame(x0, y0, 0)
                ftr = robotmath.xyz_to_frame(x1, y0, 0)
                fbr = robotmath.xyz_to_frame(x1, y1, 0)

                ftl = robotmath.translate(ftl, source, target)
                ftr = robotmath.translate(ftr, source, target)
                fbr = robotmath.translate(fbr, source, target)
                x0, y0, z0 = robotmath.frame_to_xyz(ftl)
                x1, y1, z1 = robotmath.frame_to_xyz(fbr)
                w_mm = np.linalg.norm(ftr.A[0:3, 3] - ftl.A[0:3, 3])
                h_mm = np.linalg.norm(fbr.A[0:3, 3] - ftr.A[0:3, 3])

            mx, my = (x0+x1)/2, (y0+y1)/2
            result["pose"] = [mx, my]
            result["size_mm"] = [w_mm, h_mm]

            results.append(result)

        return results

    @json_out
    def get_read_text(self, context: str = "tnt", language: str = "English", detector: str = 'abbyy', exposure=None, gain=None, **kwargs):
        """
        DEPRECATED!
        Take a photo and analyze the image for text.
        :param context: Returned positions are relative to this context.
        :param language: Language as string, like "English" (default).
        :param detector: Analyzer name, like abbyy (default).
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :return: Found text with position information.
        """
        log.warning("API method 'read_text()' is deprecated. Use Dut.search_text() or Camera.screenshot() and Image.search_text() instead.")
        
        threshold = kwargs.pop("threshold", False)
        negate = kwargs.pop("negate", False)

        _, image = self.get_still(filetype="none", undistorted=True, exposure=exposure, gain=gain, **kwargs)

        # grayscale
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if threshold:
            _, image = cv2.threshold(image, 128, 255, cv2.THRESH_BINARY)

        if negate:
            image = 255 - image

        results = search_text(image, pattern=None, language=language, detector=detector)

        # convert pixel boxes to camera coordinate system
        ppmm = self.ppmm
        w, h = self.camera_info.pixel_width, self.camera_info.pixel_height

        # results in format [TYPE, [x0,y0,x1,y1], TEXT] where TYPE can be Word, Paragraph
        rs = []
        for result in results["results"]:
            type = result["kind"]
            text = result["text"]

            x0 = result["topLeftX_px"]
            y0 = result["topLeftY_px"]
            x1 = result["bottomRightX_px"]
            y1 = result["bottomRightY_px"]

            r = {"box_px": [x0, y0, x1, y1], "type": type, "text": text}

            # camera frame pointing down, x-axis pointing left
            # pose and size_mm in millimeters
            x0, y0 = -(x0 - w / 2) / ppmm, (y0 - h / 2) / ppmm
            x1, y1 = -(x1 - w / 2) / ppmm, (y1 - h / 2) / ppmm

            # at this point box is quaranteed to be in straight position, after context transform it is not.
            w_mm = x1 - x0
            h_mm = y1 - y0

            if context is not None:
                # transform coordinates to context
                source = self
                target = Node.find(context)
                if target is None:
                    raise NodeException("context not found")

                ftl = robotmath.xyz_to_frame(x0, y0, 0)
                ftr = robotmath.xyz_to_frame(x1, y0, 0)
                fbr = robotmath.xyz_to_frame(x1, y1, 0)

                ftl = robotmath.translate(ftl, source, target)
                ftr = robotmath.translate(ftr, source, target)
                fbr = robotmath.translate(fbr, source, target)
                x0, y0, z0 = robotmath.frame_to_xyz(ftl)
                x1, y1, z1 = robotmath.frame_to_xyz(fbr)

                w_mm = np.linalg.norm(ftr.A[0:3, 3] - ftl.A[0:3, 3])
                h_mm = np.linalg.norm(fbr.A[0:3, 3] - ftr.A[0:3, 3])

            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            r["pose"] = [mx, my]
            r["size_mm"] = [w_mm, h_mm]

            rs.append(r)

        return rs

    def auto_exposure(self, starting_exposure=0.7, undistorted=False):
        """
        Finds automatically optimal exposure for the camera based on currently seen image.
        Does not change the exposure property of camera.
        :param starting_exposure: Exposure in seconds to start the iteration from.
        :param undistorted: Use undistorted image?
        :return: Optimal exposure value in seconds.
        """

        # Keep track of exposure (in seconds) and pass it as parameter to still() during exposure calibration.
        # This seems like the most robust way at the moment as exposure state is managed on many levels.
        exposure = starting_exposure

        def exposure_getter():
            return exposure * 1000

        def exposure_setter(new_exposure):
            nonlocal exposure
            exposure = new_exposure * 0.001

        def capture_image():
            return self.still(undistorted=undistorted, exposure=exposure, gain=None)

        # ExposureCalibration manages exposure in ms so we need to be converting between s <-> ms.
        exposure_calibrator = ExposureCalibration(
            exposure_getter_handler=exposure_getter,
            exposure_setter_handler=exposure_setter,
            capture_image_handler=capture_image,
            allowed_overexposure_percentage=1,
            starting_exposure=starting_exposure*1000,
        )

        optimal_exposure = exposure_calibrator.quick_auto_exposure()
        optimal_exposure *= 0.001

        return optimal_exposure

    @json_out
    def put_auto_exposure(self, starting_exposure=0.7, undistorted=False):
        """
        Finds automatically optimal exposure for the camera based on currently seen image.
        Does not change the exposure property of camera.
        :param starting_exposure: Exposure in seconds to start the iteration from.
        :param undistorted: Use undistorted image?
        :return: Optimal exposure value in seconds.
        """
        return self.auto_exposure(starting_exposure, undistorted)

    @property
    @private
    def exposure(self):
        """
        Camera exposure time in seconds.
        """
        return self._driver.exposure

    @exposure.setter
    @private
    def exposure(self, value):
        """
        Camera exposure time in seconds.
        :param value: New exposure time in seconds.
        """
        max = self._driver.exposure_max
        min = self._driver.exposure_min
        if value < min:
            log.warning("Camera exposure parameter too low ({}). Using min value ({})".format(str(value), str(min)))
        if value > max:
            log.warning("Camera exposure parameter too high ({}). Using max value ({})".format(str(value), str(max)))
        # Float conversion is needed as np.clip returns float64 which does not work.
        self._driver.exposure = float(np.clip(value, min, max))

    @property
    @private
    def gain(self):
        """
        Camera gain value.
        """
        return self._driver.gain

    @gain.setter
    @private
    def gain(self, value):
        """
        Camera gain value.
        :param value: New gain value.
        """
        self._driver.gain = value

    def screenshot(self, exposure=None, gain=None, duration=None) -> Image:
        """
        Take a still image with camera and store as image object.
        :param exposure: exposure in seconds. If not set, uses last exposure used.
        :param gain: gain value. If not set, uses last gain value used.
        :param duration: Video capture duration in seconds. Per-pixel maximum will be taken over the video.
        :return: tntserver.Nodes.TnT.Image.Image
        """

        # Prepare robots for capturing image.
        for robot in Node.find_class("Robot"):
            robot.camera_capture_preparations(self.name)

        if duration is None:
            img = self.still(undistorted=True, exposure=exposure, gain=gain)
        else:
            frames = self.record_video(duration, exposure=exposure, gain=gain)
            img = per_pixel_maximum(frames)

        images = Node.find("images")

        if images is None:
            raise Exception("Images node not found. Revise configuration.")

        # Add new image resource. Use None name to generate image name from current time.
        img_name = images.add(None)
        screenshot = Node.find(img_name)

        screenshot.set_data(img)
        screenshot.ppmm = self.ppmm

        return screenshot

    @json_out
    def post_screenshot(self, crop_left=None, crop_upper=None, crop_right=None,
                        crop_lower=None, crop_unit=None, exposure=None, gain=None, duration=None):
        """
        Take a still image with camera and store as image object.
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        :param exposure: exposure in seconds. If not set, uses last exposure used.
        :param gain: gain value. If not set, uses last gain value used.
        :param duration: Video capture duration in seconds. Per-pixel maximum will be taken over the video.
        :return: Image name.
        """
        screenshot = self.screenshot(exposure=exposure, gain=gain, duration=duration)

        if crop_unit is not None:
            screenshot.crop(crop_left, crop_upper, crop_right, crop_lower, crop_unit)
            screenshot.save_image()

        return screenshot.name

    @json_out
    def put_output_state(self, value):
        """
        Set all camera digital outputs to some value.
        :param value: Boolean value.
        """
        self._driver.set_output_state(int(value))
