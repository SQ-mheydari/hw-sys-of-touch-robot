from tntserver.Nodes.Node import Node, json_out, png_out
from tntserver import dut_calibrator
from toolbox.dut import DutPositioning
from tntserver import robotmath

import cv2
import logging

log = logging.getLogger(__name__)


class NodeDutPositioning(Node):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dut_calibrator = None
        self._offset_calibrator = None
        self._dut_positioning = None
        self._surfaceprobe = None

    def _init(self, robot: str, camera: str, **kwargs):
        """
        Initialize the node.
        :param robot: Name of the robot to use.
        :param camera: Name of the camera to use.
        """
        self._robot_name = robot
        self._camera_name = camera
        self._dut_positioning = DutPositioning()
        self._surfaceprobe = Node.find(kwargs.get('surfaceprobe', ""))

    @staticmethod
    def dict_keys_to_int(input_dict):
        """
        Helper function to convert dictionary keys to integers.
        :param input_dict: Input dictionary.
        :return: New dictionary with integer values as keys.
        """
        return {int(k): v for k, v in input_dict.items()}

    @json_out
    def put_start(self, dut_name, camera_exposure, camera_gain,
                  position_image_params=None, show_positioning_image=False):
        """
        Start DUT positioning process.
        :param dut_name: Name of DUT to position.
        :param camera_exposure: Camera exposure (in seconds) to use in blob detection.
        :param camera_gain: Camera gain to use in blob detection.
        :param position_image_params: Dictionary containing positioning image parameters. NOTE: The image parameters
        must match the shown image on the DUT screen. If show_positioning_image is True, this is handled automatically.
        However, if show_positioning_image is False the user manually sets the image on the DUT screen. In this case the
        user must make sure the passed parameters correspond to the image being showed.
        :param show_positioning_image: If true, positioning image is sent to DUT (via DUTServer connection)
        """
        self._dut_calibrator = dut_calibrator.DutCalibrator(robot_name=self._robot_name,
                                                            camera_name=self._camera_name,
                                                            dut_name=dut_name,
                                                            exposure=camera_exposure,
                                                            gain=camera_gain)

        # Convert dictionary keys for blobs back to integers after JSON serialization
        if position_image_params is not None:
            position_image_params["blobs"] = self.dict_keys_to_int(position_image_params["blobs"])
        self._dut_calibrator.start_calibration(show_positioning_image=show_positioning_image,
                                               position_image_parameters=position_image_params)

    @json_out
    def put_start_xyz_positioning(self, dut_name, camera_name, camera_exposure, camera_gain, display_ppmm,
                                  position_image_params, n_markers=5, show_positioning_image=False):
        """
        Start complete DUT positioning process which includes sub-steps of surface probing. It is assumed the DUT is
        roughly horizontal and not inclined significantly wrt the robot tooling plate. Before calling this method
        the robot should be at a safe z-height to start centering the camera on found markers.
        :param dut_name: Name of DUT to position.
        :param camera_name: Name of positioning camera.
        :param camera_exposure: Camera exposure to use in blob detection.
        :param camera_gain: Camera gain to use in blob detection.
        :param display_ppmm: Screen ppmm of positioned DUT.
        :param position_image_params: Dictionary containing positioning image parameters. NOTE: The image parameters
        must match the shown image on the DUT screen. If show_positioning_image is True, this is handled automatically.
        However, if show_positioning_image is False the user manually sets the image on the DUT screen. In this case the
        user must make sure the passed parameters correspond to the image being showed.
        :param n_markers: Number of markers to use in positioning.
        :param show_positioning_image: If true, positioning image is sent to DUT (via DUTServer connection)
        """

        if self._surfaceprobe is None:
            raise Exception("Surfaceprobe resource not initialized properly. Please check configuration.")

        dc = dut_calibrator.DutCalibrator(robot_name=self._robot_name, camera_name=self._camera_name, dut_name=dut_name,
                                          exposure=camera_exposure, gain=camera_gain)

        # Center to one visible marker and probe z height to get camera to focus height.
        log.info("Detecting markers from image.")
        if show_positioning_image:
            dc.show_positioning_image()

        found_blob = dc.center_to_blob()
        if found_blob is None:
            raise Exception("Could not find any markers from image. Try adjusting lighting conditions, camera exposure "
                            "and/or camera gain. Aborting sequence.")

        camera = Node.find(camera_name)
        robot = camera.find_object_parent_by_class_name("Robot")
        dut = Node.find(dut_name)
        dut_gesture = dut.find_child_with_path("gestures")

        # Get camera X, Y position in world coordinates and move robot to the same X,Y position
        camera_frame = robotmath.translate(camera.frame, camera.object_parent, Node.find("tnt"))
        cam_x, cam_y, _ = robotmath.frame_to_xyz(camera_frame)

        robot_frame = robotmath.translate(robot.effective_frame, robot.object_parent, Node.find("tnt"))
        _, _, robot_z = robotmath.frame_to_xyz(robot_frame)

        target_pose = robotmath.xyz_to_frame(cam_x, cam_y, robot_z)
        robot.effective_frame = robotmath.pose_to_frame(target_pose)

        # Probe surface once to get camera to the focus height.
        log.info("Probing surface once for initial coordinates")
        start_pos = self._surfaceprobe.probe_z_surface()

        x = start_pos[0][3]
        y = start_pos[1][3]
        z = start_pos[2][3]
        planar_points = [(x, y, z), (x + 10, y, z), (x + 10, y + 10, z)]

        log.info("Moving to focus height")
        focus_height = camera.focus_height
        target_pose = robotmath.xyz_to_frame(x, y, z + focus_height)
        target_frame = robotmath.pose_to_frame(target_pose)
        robot.effective_frame = target_frame

        log.info("Initializing DUT positioning")
        # Convert dictionary keys for blobs back to integers after JSON serialization
        if position_image_params is not None:
            position_image_params["blobs"] = self.dict_keys_to_int(position_image_params["blobs"])
            dc.start_calibration(show_positioning_image=show_positioning_image,
                                 position_image_parameters=position_image_params)
        else:
            position_image_params = dc.start_calibration(show_positioning_image=show_positioning_image,
                                                         position_image_parameters=None)

        found_blobs = []
        for i in range(n_markers):
            log.info("Locating marker {} / {}".format(i + 1, n_markers))
            found_blobs.append(dc.locate_next_blob())

        # Update DUT to use a horizontal plane temporarily before using probed surface locations.
        for p in planar_points:
            dc.add_plane_point(p)

        retval = dc.result()
        tl = retval["dut_pts"]["tl"]
        dut.tl = {"x": tl[0], "y": tl[1], "z": tl[2]}
        tr = retval["dut_pts"]["tr"]
        dut.tr = {"x": tr[0], "y": tr[1], "z": tr[2]}
        bl = retval["dut_pts"]["bl"]
        dut.bl = {"x": bl[0], "y": bl[1], "z": bl[2]}

        # Probe found marker locations
        probed_points = []
        for i, blob_id in enumerate(found_blobs):
            p0 = position_image_params["blobs"][blob_id]
            dut_gesture.put_jump(x=p0[0] / display_ppmm, y=p0[1] / display_ppmm, z=20)
            log.info("Probing at marker {} / {}".format(i + 1, len(found_blobs)))
            probed_points.append(self._surfaceprobe.probe_z_surface())

        # Clear existing plane points and re-calculate DUT position with probed surface points.
        dc.clear_plane_points()

        for p in probed_points:
            dc.add_plane_point((p[0][3], p[1][3], p[2][3]))

        retval = dc.result()
        tl = retval["dut_pts"]["tl"]
        dut.tl = {"x": tl[0], "y": tl[1], "z": tl[2]}
        tr = retval["dut_pts"]["tr"]
        dut.tr = {"x": tr[0], "y": tr[1], "z": tr[2]}
        bl = retval["dut_pts"]["bl"]
        dut.bl = {"x": bl[0], "y": bl[1], "z": bl[2]}

        log.debug("DUT corner points updated to {}".format(retval["dut_pts"]))

    @json_out
    def put_locate_next_blob(self):
        """
        Searches for the next positioning marker in the sequence.
        :return: ID of detected marker.
        """
        return self._dut_calibrator.locate_next_blob()

    @json_out
    def put_center_to_blob_in_image(self, dut_name, camera_exposure, camera_gain):
        """
        Searches for position markers in the image and centers camera to the first found marker.
        :param dut_name: Name of DUT to position.
        :param camera_exposure: Camera exposure (in seconds) to use in blob detection.
        :param camera_gain: Camera gain to use in blob detection.
        """
        dc = dut_calibrator.DutCalibrator(robot_name=self._robot_name, camera_name=self._camera_name, dut_name=dut_name,
                                          exposure=camera_exposure, gain=camera_gain)

        dc.center_to_blob()

    @json_out
    def put_clear_plane_points(self):
        """
        Clear plane points that have been added previously.
        """
        self._dut_calibrator.clear_plane_points()

    @json_out
    def put_add_robot_plane_point(self, point):
        """
        Add new plane point for the determination of DUT plane.
        :param point: Point as list [x, y, z].
        """
        self._dut_calibrator.add_plane_point(point)

    @json_out
    def put_calculate(self):
        """
        Calculate the DUT positioning based on positioned blobs and plane points.
        :return: Positioning data.
        """
        return self._dut_calibrator.result()

    @png_out
    def get_dut_positioning_image(self, width, height, ppmm):
        """
        Returns DUT positioning image according to input parameters.
        :param width: Image width in pixels.
        :param height: Image height in pixels.
        :param ppmm: Image scaling in pixels per millimeter. Image markers have a fixed diameter of 8 mm, which is
        scaled to number of pixels using this parameter.
        :return: Positioning image in PNG-format.
        """
        img, _ = self._dut_positioning.positioning_image(dut_svg=None, region=None, dut_pixel_size=(int(width),
                                                                                                 int(height)),
                                                      ppmm=float(ppmm))
        return cv2.imencode(".png", img)[1]

    @json_out
    def get_positioning_image_parameters(self, width, height, ppmm):
        """
        Returns dictionary of positioning image parameters according to image input parameters.
        :param width: Image width in pixels.
        :param height: Image height in pixels.
        :param ppmm: Image scaling in pixels per millimeter.
        :return: Dictionary with image parameters.
        """
        _, blob_positions = self._dut_positioning.positioning_image(dut_svg=None, region=None, dut_pixel_size=(int(width),
                                                                                                 int(height)),
                                                      ppmm=float(ppmm))
        mm_size = width / ppmm, height / ppmm

        return {"blobs": blob_positions,
                "display_size_mm": mm_size,
                "display_size_px": (int(width), int(height))}

