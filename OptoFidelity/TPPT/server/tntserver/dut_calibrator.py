import numpy as np
from tntserver.Nodes.Node import Node
from tntserver import robotmath
from optovision.detection import IndexBlobDetector
import toolbox
import random
import time

import logging
log = logging.getLogger(__name__)


class AbstractRobotTools:
    """
    Functions needed by calibration functions
    This abstract class can be subclassed with concrete robot / camera functions
    for example TnT Python Client or native TnT Server functions implementation
    """

    def __init__(self):
        pass

    def duts(self):
        raise Exception("Abstract")

    def dut(self, name):
        raise Exception("Abstract")

    def show_calibration_image(self, dut_name):
        dut = self.dut(dut_name)
        dut.show_calibration_image()

    def photo(self, exposure=None, gain=None):
        raise Exception("Abstract")

    def set_robot_speed(self, speed, acceleration):
        raise Exception("Abstract")

    def robot_position(self):
        raise Exception("Abstract")

    def camera_position(self):
        raise Exception("Abstract")

    def set_robot_position(self, x, y, z, azimuth=None):
        raise Exception("Abstract")

    @staticmethod
    def _detect_blobs_from_image(image):
        """
        Detect blobs from image using toolbox's detect_from_image().
        In case of any errors raises exception and tries to give hint for improvements.
        :param image: Image to detect blobs from.
        :return: Return values of IndexBlobDetector.detect_from_image().
        """
        try:
            markers, markers_dict, points = IndexBlobDetector.detect_from_image(image)

            if len(markers) == 0:
                raise Exception("No markers found. Try adjusting camera exposure and gain.")

            return markers, markers_dict, points
        except Exception as e:
            raise Exception("Problem in detecting markers ({}). Try adjusting camera exposure and gain.".format(str(e)))

    def get_ppmm(self):
        time.sleep(0.5)
        _, blobs_1, _ = AbstractRobotTools._detect_blobs_from_image(self.photo())
        x, y, z = self.robot_position()
        print(x, y, z)

        movement_step = 5
        x += movement_step

        self.set_robot_position(x, y, z)

        time.sleep(0.5)
        _, blobs_2, _ = AbstractRobotTools._detect_blobs_from_image(self.photo())

        diffs = []
        for pid in blobs_1:
            if pid in blobs_2:
                x0, y0 = blobs_1[pid]
                x1, y1 = blobs_2[pid]
                diffs.append(np.linalg.norm((x1-x0, y1-y0)))

        ppmm = np.median(diffs) / movement_step
        return ppmm

    def move_relative(self, x, y, z):
        rx, ry, rz = self.robot_position()
        self.set_robot_position(rx + x, ry + y, rz + z)

    def center_blob_id(self, blob_id, camera_ppmm, accuracy_mm=0.002, max_loops=10):
        loops = 0
        while True:
            max_blob_reads_retries = 4
            while max_blob_reads_retries:
                image = self.photo()
                ih, iw = image.shape[:2]
                _, blobs, _ = AbstractRobotTools._detect_blobs_from_image(image)
                if blob_id in blobs:
                    break
                log.warning("retrying reading blobs because blob id {} not found".format(blob_id))
                max_blob_reads_retries -= 1

            if max_blob_reads_retries == 0:
                raise Exception("marker {} not found".format(blob_id))

            dx, dy = blobs[blob_id]
            dx = (dx - iw / 2) / camera_ppmm
            dy = (dy - ih / 2) / camera_ppmm
            distance = np.linalg.norm((dx, dy))
            if distance < accuracy_mm:
                break
            step = 0.6 + 0.1 * random.random()
            self.move_relative(dx * step, dy * step, 0)

            loops += 1
            if loops == max_loops:
                break
        return distance

    def middle_blob_id(self, photo):
        blobs, _, _ = AbstractRobotTools._detect_blobs_from_image(photo)
        ih, iw = photo.shape[:2]

        blobs = np.array(blobs)
        ids = blobs[:, 0].flatten()
        positions = blobs[:, 1:3]

        positions -= np.array((iw/2, ih/2))
        distances = np.linalg.norm(positions, axis=0)
        lowest = np.argsort(distances)[0]
        lowest_id = ids[lowest]
        return lowest_id

    def calibrate_stereocamera(self):
        stereo = toolbox.vision.StereoImaging(x_distance=30, z_distance=3)

        x, y, z = self.robot_position()

        # how much to move in calibration phase
        # x-distance and z-distance
        # x-distance should be enough but not too much so that both eyes still see the same target blobs
        # z-distance should be enough but not more than what the camera lens can keep in focus
        x_diff = stereo.x_distance
        z_diff = stereo.z_distance
        pos1 = (x, y, z)
        pos2 = (x + x_diff, y, z)
        pos3 = (x, y, z + z_diff)
        pos4 = (x + x_diff, y, z + z_diff)

        positions = [pos1, pos2, pos3, pos4]

        for pos in positions:
            self.set_robot_position(*pos)
            image = self.photo()

            x, y, z = pos
            stereo.add_calibration_image(image, x, z)

        stereo.calibrate()
        self.stereo = stereo

    def scan_blobs_3d(self, camera_cell_node):
        """
        moves robot to stereo camera imaging positions and scans for indexblobs
        triangulates 3d-positions that are translated to the given camera_cell_node
        :param camera_cell_node: node for coordinate translation
        :return:
        """
        x, y, z = self.robot_position()
        camera_cell_frame = robotmath.translate(robotmath.identity_frame(), camera_cell_node, Node.root)

        image0 = self.photo()

        self.set_robot_position(x + self.stereo.x_distance, y, z)
        image1 = self.photo()

        self.set_robot_position(x, y, z)

        pts3d = self.stereo.triangulate(image0, image1)

        for pid in pts3d:
            f_p = robotmath.xyz_to_frame(*pts3d[pid])
            f_p = camera_cell_frame * f_p
            pts3d[pid] = tuple(robotmath.frame_to_xyz(f_p))

        return pts3d


class TnTRobotTools(AbstractRobotTools):
    """
    Concrete implementation of abstract RobotTools with TnT Server classes
    """
    def __init__(self, robot_name, camera_name, exposure, gain):
        super().__init__()

        self._robot = Node.find(robot_name)
        self._camera = Node.find(camera_name)
        self._exposure = exposure
        self._gain = gain

    def duts(self):
        node_duts = Node.find_class("Duts")[0]
        dut_names = [name for name in node_duts.children.keys()]
        return dut_names

    def dut(self, name):
        node_duts = Node.find_class("Duts")[0]
        dut = node_duts.children[name]
        return dut

    def photo(self, exposure=None, gain=None):
        exposure = self._exposure if exposure is None else exposure
        gain = self._gain if gain is None else gain

        with self._camera._api_lock:
            image = self._camera.still(exposure=exposure, gain=gain, undistorted=True)
        return image

    def set_robot_speed(self, speed, acceleration):
        with self._robot._api_lock:
            self._robot.set_speed(speed, acceleration)

    def robot_position(self):
        with self._robot._api_lock:
            pose = self._robot.effective_pose()
        x, y, z = robotmath.frame_to_xyz(pose)
        return x, y, z

    def camera_position(self):
        frame = robotmath.translate(robotmath.identity_frame(), self._camera, Node.root)
        x, y, z = robotmath.frame_to_xyz(frame)
        return x, y, z

    def set_robot_position(self, x, y, z, azimuth=None):
        if azimuth is None:
            with self._robot._api_lock:
                pose = self._robot.effective_pose()
            _, _, _, _, _, c = robotmath.frame_to_xyz_euler(pose)
            azimuth = -c

        pose = robotmath.xyz_euler_to_frame(x, y, z, 0, 0, -azimuth)
        with self._robot._api_lock:
            self._robot.set_effective_pose(context=self._robot.object_parent, pose=pose)

    def center_to_blob(self):
        """
        Center to one blob found in image, whichever is first detected.
        :return: ID of found blob.
        """
        # Estimate camera ppmm and center to first found blob
        ppmm = self.get_ppmm()
        photo = self.photo()
        blob_list, _, _ = AbstractRobotTools._detect_blobs_from_image(photo)
        found_blob = None
        # Iterate over found blobs and exit loop at first found blob.
        for blob_id in blob_list[0]:
            try:
                self.center_blob_id(blob_id, ppmm)
            except Exception:
                continue
            else:
                found_blob = blob_id
                break
        return found_blob


class DutCalibrator:
    """
    Worker for calibrating (locating) DUT with optical / mechanical methods.
    """
    def __init__(self, robot_name, camera_name, dut_name, exposure, gain, accuracy=0.01):
        self._dut_points = {}  # x, y points indexed with point_id, in dut diplay pixel coordinates.
        self._camera_points = {}  # x, y points indexed with point_id, in robot base coordinates.
        self._plane_points = []  # list of x, y, z points, millimeters, in robot base coordinates.

        self._width = None
        self._height = None

        self._ppmm = None

        self.ct = TnTRobotTools(robot_name, camera_name, exposure, gain)
        self._dut = self.ct.dut(dut_name)

        self.blobs = {}         # initial position blobs
        self.blob_ids = []      # initial position blob ids unordered

        self._loop_index = 0

        self.accuracy = accuracy

        self._width = 0  # dut width in mm
        self._height = 0  # dut height in mm

    def start_calibration(self, show_positioning_image=True, position_image_parameters=None):
        """
        Start calibration process
        Camera should be over the dut at focus height
        1. shows calibration image on dut screen
        2. moves robot sideways 1mm to calculate ppmm
        3. moves robot sideways x mm and up/down x mm to calibrate stereo imaging
        4. stores initial blob list for later looping
        5. 3d scan surface with stereo camera imaging

        :param show_positioning_image: If true, positioning image is sent to DUT (via DUTServer connection)
        :param position_image_parameters: Dictionary containing positioning image parameters
        :return: Dictionary containing used positioning image parameters. If input parameters are None and
        show_positioning_image is True, server will generate the parameters.
        """

        self._dut_points = {}  # x, y points indexed with point_id
        self._camera_points = {}  # x, y points indexed with point_id
        self._plane_points = []  # list of x, y, z points

        start_position = self.ct.robot_position()

        # 1. show calibration image on dut screen
        if show_positioning_image:
            show_params = self.show_positioning_image()
        else:
            if position_image_parameters is None:
                raise Exception("Positioning image blob positions are required!")
            show_params = position_image_parameters

        self._dut_points = show_params["blobs"]
        self.dut_width_px = float(show_params['display_size_px'][0])
        self.dut_height_px = float(show_params['display_size_px'][1])

        # 2. calculate ppmm
        ppmm = self.ct.get_ppmm()
        self._ppmm = ppmm
        print(ppmm)

        # 3. calibrate stereo imaging
        # self.ct.calibrate_stereocamera()

        x, y, z = start_position
        self.ct.set_robot_position(x, y, z)

        # 4. read initial blob list
        # center the centermost blob to camera center
        # this will be the zero position where to search blobs in loop
        photo = self.ct.photo()
        middle_id = self.ct.middle_blob_id(photo)
        self.ct.center_blob_id(middle_id, self._ppmm)
        self.start_position = self.ct.robot_position()

        # get list of blobs to loop through
        photo = self.ct.photo()
        blob_list, blobs, _ = AbstractRobotTools._detect_blobs_from_image(photo)

        # reorder blob list to be optimal
        blob_indices = self._best_point_order(np.array(blob_list)[:, :2])
        blob_ids_ordered = [blob_list[i][0] for i in blob_indices]
        self.blob_ids = blob_ids_ordered
        self.blobs = blobs

        self._loop_index = 0

        # 5. 3d scan surface
        # this step would need a node that is positioned physically at camera imaging cell.
        # we do not have that kind of thing at the moment.
        # so use manual methods instead.
        """
        self.ct.set_robot_position(*start_position)

        camera_node = Node.find("Camera1")

        blobs_3d = self.ct.scan_blobs_3d(camera_node)

        surface_points = [(x, y, z) for x, y, z in blobs_3d.values()]
        for pt in surface_points:
            self.add_plane_point(pt)
        """

        return show_params

    def show_positioning_image(self):
        """
        Show positioning image on DUT screen
        :return: Dictionary containing positions of drawn markers, display size in mm, display size in pixels
        """
        return self._dut.show_positioning_image()

    def locate_next_blob(self):
        """
        Add one blob to the calibration data.
        Moves the camera to the center of the blob and stores camera location.
        :return: ID of found blob.
        """

        blob_id = None
        # get next blob
        while self._loop_index < len(self.blob_ids):
            blob_id = self.blob_ids[self._loop_index]
            self._loop_index += 1

            # move to initial position first (there you can see the blobs in the list)
            self.ct.set_robot_position(*self.start_position)

            # then center the selected blob
            try:
                self.ct.center_blob_id(blob_id, self._ppmm, accuracy_mm=self.accuracy)

            # if detection failed, try the next blob in the list
            except Exception as e:
                log.exception(e)
                continue
            else:
                x, y, _ = self.ct.camera_position()
                self.set_camera_point(str(blob_id), (x, y))
                break
        return blob_id

    def center_to_blob(self):
        """
        Center to one blob found in image, whichever is first detected.
        :return: ID of found blob.
        """
        return self.ct.center_to_blob()

    def result(self):
        """
        Calculates everything with given data
        Updates DUT coordinates
        Creates message to return
        :return: message
        """

        mtx2d, dut_frame, dut_pts, message = self.calculate()

        message.update({"m2d": mtx2d.tolist(),
                        "dut_frame": dut_frame.tolist(),
                        "dut_pts": dut_pts,
                        "dut_size_mm": (self._width, self._height)})

        return message

    def set_dut_point(self, point_id, point):
        """
        Set x, y position for identifier 'point_id'. position is in DUT display pixel coordinates.
        :param point_id: id of the point.
        :param point: (x, y)
        """
        self._dut_points[point_id] = point

    def set_camera_point(self, point_id, point):
        """
        Set x, y position for identifier 'point_id'. position is in robot base coordinates, millimeters.
        :param point_id: id of the point.
        :param point: (x, y)
        """
        self._camera_points[int(point_id)] = point

    def clear_plane_points(self):
        """
        Clear the DUT surface plane point list.
        The found x, y corner positions will be later projected on this plane.
        """
        self._plane_points = []

    def add_plane_point(self, point):
        """
        Add a point on DUT surface plane
        The found x, y corner positions will be later projected on this plane.
        :param point: (x, y, z) point in robot base coordinates.
        """
        if point is None:
            point = self.ct.robot_position()

        self._plane_points.append(point)

    def set_dut_size(self, width, height):
        """
        Force set DUT size in millimeters.
        :param width: DUT width in millimeters.
        :param height: DUT height in millimeters.
        :return:
        """
        self._width = width
        self._height = height

    def calculate(self):
        """
        Calculate everything possible with current set of data.
        Tries to create transformation between dut_points and robot_points
        Tries to create surface plane from plane_points
        Tries to project DUT corner 2d points on DUT surface.
        :return: 2d matrix, 3d matrix, three dut corners as a dictionary, message containing errors, status, etc.
        """
        # solve dut frame 2d portion

        mtx2d, msg = toolbox.dut.DutPositioning.dut_to_camera_transformation(self._camera_points, self._dut_points)
        dut_frame = None

        # create a plane from 3..n points
        plane = self._plane_from_points(self._plane_points)

        tl = [0, 0, 0]
        tr = [0, 0, 0]
        bl = [0, 0, 0]

        if mtx2d is not None and plane is not None:
            # create width, height
            dut_scale = np.linalg.norm(mtx2d[0:3, 0:3], axis=1)

            # dut size is measured from the middle of the corner pixel to the middle of the next corner pixel
            # that is why the width is calculated from (width_px - 1)
            dut_width_mm = float((self.dut_width_px - 1) * dut_scale[0])
            dut_height_mm = float((self.dut_height_px - 1) * dut_scale[1])
            self._width = dut_width_mm
            self._height = dut_height_mm

            # create dut corner points with 2d transformation
            tl = robotmath.frame_to_xyz(mtx2d * robotmath.xyz_to_frame(0, 0, 0))
            tr = robotmath.frame_to_xyz(mtx2d * robotmath.xyz_to_frame(dut_width_mm / dut_scale[0], 0, 0))
            bl = robotmath.frame_to_xyz(mtx2d * robotmath.xyz_to_frame(0, dut_height_mm / dut_scale[1], 0))

            # project 2d corner points to 3d-plane (2d pts -> 3d pts)
            tl, tr, bl = self._project_2d_points_on_plane([tl, tr, bl], plane)
            tl = tl.tolist()
            tr = tr.tolist()
            bl = bl.tolist()

            # create the dut frame from the 3 points in traditional way
            dut_frame = robotmath.three_point_frame(tl, tr, bl)

        if mtx2d is None:
            mtx2d = robotmath.identity_frame()

        if dut_frame is None:
            dut_frame = robotmath.identity_frame()

        return mtx2d, dut_frame, {"tl": tl, "tr": tr, "bl": bl}, msg

    def _plane_from_points(self, points):
        """
        Create a 4x4 matrix that defines plane on which the given points reside.
        :param points: list of (x, y, z) points on a plane.
        :return: 4x4 matrix defining the plane.
        """

        if len(points) < 3:
            return None

        points = np.array(points)

        # barycenter of the points
        # compute centered coordinates
        g = points.sum(axis=0) / points.shape[0]

        # run SVD
        a, b, vh = np.linalg.svd(points - g)

        m = robotmath.identity_frame()
        m.A[0:3, 0:3] = vh.T
        m.A[0:3, 3] = g
        return m

    def _plane_line_intersection(self, plane, line_start, line_end):
        """
        Calculates intersection point between plane and line
        :param plane: plane as 4x4 matrix
        :param line_start: line start point (x, y, z)
        :param line_end: line end point     (x, y, z)
        :return: intersection point as x, y, z
        """

        plane_origo = plane.A[0:3, 3].flatten()
        plane_normal = plane.A[0:3, 2].flatten()

        line = np.array([line_start, line_end], dtype=np.float64)

        line_direction = (line[1] - line[0])
        line_direction /= np.linalg.norm(line_direction)

        denominator = np.dot(plane_normal, line_direction)

        t = np.dot(line[0] - plane_origo, plane_normal) / denominator

        intersection = line[0] - line_direction * t
        return intersection

    def _project_2d_points_on_plane(self, points, plane):
        """
        Projects 2d points on plane in z-axis direction.
        This is done by drawing lines to the direction of Z-axis through the points
         and see where the points intersect the given plane.
        As the plane is calculated by fitting set of arbitrary points to a plane,
         the plane's origo is unknown and plane surface might be pointing up or down.
         This why the projecting method is what it is instead of simple matrix transformation.
        Input 2d points (x, y) and get 3d points (x, y, z)
        :param points: (x, y) points
        :return: (x, y, z) points
        """
        results = []
        for pt in points:
            x, y = pt[0:2]
            line = (x, y, -1), (x, y, 1)  # Line in z-axis direction.
            pt = self._plane_line_intersection(plane, line[0], line[1])
            results.append(pt)
        return results

    def _best_point_order(self, points):
        """
        Finds point order where the results will be best from first set of points onwards

        If the points are just used from the blob detector, the points are usually
        well ordered and first few points will be on the same line in x/y coordinates
        and the next points will be very close to the first points

        This function tries to do the opposite of the natural order;
        next point is the furthest point possible
        and furthest point perpendicular to a line formed by last ordered points

        :return: ordered index list
        """

        # change points from (x, y) to (x, y, index)
        points = [np.array([pt[0], pt[1], i]) for i, pt in enumerate(points)]

        ordered_points = []

        pt0 = points[0]
        points = points[1:]
        ordered_points.append(pt0)

        # 1. second point is the one furthest away from first point
        i = np.argsort(np.linalg.norm(np.array(points)[:, :2] - pt0[:2], axis=1))[-1]
        pt1 = points[i]
        ordered_points.append(pt1)
        del points[i]

        def distance_from_line(line_pt0, line_pt1, pt):
            return np.linalg.norm(np.cross(line_pt1[:2]-line_pt0[:2], line_pt0[:2]-pt[:2]))/np.linalg.norm(line_pt1[:2]-line_pt0[:2])

        # next point is the furthest point from the line defined by last two points
        while len(points):
            ds = [distance_from_line(pt0, pt1, pt) for pt in points]
            furthest_index = np.argsort(ds)[-1]
            ordered_points.append(points[furthest_index])
            del points[furthest_index]
            pt0 = pt1
            pt1 = ordered_points[-1]

        return np.array(ordered_points)[:, 2].flatten().astype(np.int)
