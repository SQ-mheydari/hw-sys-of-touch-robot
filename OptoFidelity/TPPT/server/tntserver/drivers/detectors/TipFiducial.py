from optovision.detection import CircleExtractor
from tntserver.Nodes.Node import Node, NodeException
from optovision.utils.circle_extractor_utils import draw_detections_on_image
from tntserver.robotmath import frame_to_xyz
from numpy.linalg import norm
import time

import logging
log = logging.getLogger(__name__)


def get_detection_center(detection):
    """
    Get center from circle extractor's detection data which consists of multiple results.
    :param detection: Detection data dict.
    :return: Center as tuple (x, y).
    """
    ellipse = detection["ellipse"]
    ellipse_center = ellipse["center"]

    # TODO: Analyze other data to determine if detection is good enough.

    return ellipse_center


def sort_by_key_list(sortable, keys):
    """
    Sort given list by separate key list.
    :param sortable: List to sort.
    :param keys: List parallel to sortable that contains sort keys.
    :return: Sorted list.
    """
    tuples = [(keys[i], i, sortable[i]) for i in range(len(sortable))]

    tuples.sort()

    values = [value[2] for value in tuples]

    return values


def filter_duplicate_points(points, threshold=1e-6):
    """
    Filter out duplicate points in a list of points.
    :param points: List of point tuples (x, y).
    :param threshold: Threshold distance to determine two points as duplicates.
    :return: Filtered list of points.
    """
    filtered = []

    for p in points:
        is_unique = True

        for p2 in filtered:
            distance = norm([p[0] - p2[0], p[1] - p2[1]])

            if distance < threshold:
                is_unique = False
                break

        if is_unique:
            filtered.append(p)

    return filtered


def find_slots_from_image(image, fiducial_radius_px, slot_radius_px, radius_margin_px, detection_confidence, max_contours):
    """
    Find tip slots from image. Tips slot is defined as a large circle (tip itself) and two smaller circles (fiducials)
    that form an isosceles triangle. This function does not attempt to find the triangles, only the slots and fiducials.
    :param image: Image as Numpy array.
    :param fiducial_radius_px: Tip fiducial radius in pixels.
    :param slot_radius_px: Tip slot radius in pixels.
    :param radius_margin_px: Margin to use in detection of circles of given radius in pixels.
    :param detection_confidence: Confidence in range [0, 1] to use in circle detection.
    :param max_contours: Maximum number of contours to detect from the image.
    :return: Lists slot_centers and fiducial_centers that contain all found slot and fiducial centers.
    Sorted by increasing distance from image center.
    """
    circle_extractor = CircleExtractor(min_confidence=detection_confidence, save_debug_imgs=False, show_debug_imgs=False,
                                       max_contours=max_contours)

    detections = circle_extractor.detect(image=image.copy())


    # Uncomment for debugging.
    #draw_detections_on_image(image=image, detections=detections, show=False, save=False)

    # Find potential tip holes.
    slots = circle_extractor.get_detections_by_diameter(
        detections, min_diameter_allowed=(slot_radius_px-radius_margin_px) * 2, max_diameter_allowed=(slot_radius_px+radius_margin_px) * 2
    )

    slot_centers = [get_detection_center(slot) for slot in slots]

    # Find potential tip hole fiducials.
    fiducials = circle_extractor.get_detections_by_diameter(
        detections, min_diameter_allowed=(fiducial_radius_px - radius_margin_px) * 2,
        max_diameter_allowed=(fiducial_radius_px + radius_margin_px) * 2
    )

    fiducial_centers = [get_detection_center(fiducial) for fiducial in fiducials]

    height, width = image.shape[:2]
    cx = width / 2
    cy = height / 2

    # Sort centers by distance to image center. This will make the result independent of the order in which
    # Optovision returns the circles.
    slot_distances = [norm([cx - c[0], cy - c[1]]) for c in slot_centers]
    fiducial_distances = [norm([cx - c[0], cy - c[1]]) for c in fiducial_centers]

    # Remove duplicate points as circle extractor can find circles very close to each other.
    # TODO: Should we use average or median of close by centers?
    slot_centers = filter_duplicate_points(slot_centers, radius_margin_px)
    fiducial_centers = filter_duplicate_points(fiducial_centers, radius_margin_px)

    slot_centers = sort_by_key_list(slot_centers, slot_distances)
    fiducial_centers = sort_by_key_list(fiducial_centers, fiducial_distances)

    return slot_centers, fiducial_centers


def filter_tip_slots(slot_centers, fiducial_centers, ff_distance, fs_distance, threshold):
    """
    Find tip slots from given lists of slot centers and fiducial centers. A slot center and two fiducial centers
    must form an isosceles triangle where the points are within known distance from each other.
    :param slot_centers: Slots centers as list of tuples (x, y). May contain false positives.
    :param fiducial_centers: Fiducial centers as list of tuples (x, y). May contain false positives.
    :param ff_distance: Fiducial-fiducial distance in pixels.
    :param fs_distance: Fiducial-slot distance in pixels.
    :param threshold: Threshold for distance comparison in pixels.
    :return: List of indices to slot_centers that were verified to be actual slot centers.
    """
    indices = []

    # Loop through each potential slot center.
    for i, slot_center in enumerate(slot_centers):
        selected_fiducial_centers = []

        # Loop through each potential fiducial center.
        for fiducial_center in fiducial_centers:
            # Check that fiducial is within required distance from the hole.
            distance = norm([fiducial_center[0] - slot_center[0], fiducial_center[1] - slot_center[1]])

            # Check fiducial-slot distance.
            if fs_distance - threshold <= distance <= fs_distance + threshold:
                selected_fiducial_centers.append(fiducial_center)

        # Did not find a pair of fiducials for current hole center.
        if len(selected_fiducial_centers) < 2:
            continue

        # Make sure that the fiducials are within required distance from each other.
        c0 = selected_fiducial_centers[0]
        c1 = selected_fiducial_centers[1]
        distance = norm([c0[0] - c1[0], c0[1] - c1[1]])

        if ff_distance - threshold <= distance <= ff_distance + threshold:
            indices.append(i)

    return indices


def center_camera_to_tip(camera, robot, fiducial_radius, tip_hole_radius, ff_distance, fs_distance,
                         radius_margin, detection_threshold, max_iterations=20, movement_threshold=0.01,
                         max_movement_radius=50, detection_confidence=0.7, max_contours=100, delay=1.0):
    """
    Center camera to tip slot assuming that the camera moves with a robot.
    The target slot should be close to camera center at the beginning.
    Moves robot in small increments towards detected tip slot until the slot is at the camera canter.
    Parameter movement_threshold most likely determines the overall accuracy of the algorithm. Other
    parameters are more about finding the correct target reliably. If no targets are found, those parameters
    can be made looser. Then there is possibility of false positives in detection.
    :param camera: Camera node (must be attached to robot).
    :param robot: Robot node.
    :param fiducial_radius: Fiducial radius in pixels.
    :param tip_hole_radius: Tip hole radius in pixels.
    :param ff_distance: Fiducial-fiducial distance in pixels.
    :param fs_distance: Fiducial-slot distance in pixels.
    :param radius_margin: Radius margin for circle detection in pixels.
    :param detection_threshold: Threshold for ff and fs distance comparison in pixels.
    :param max_iterations: Maximum number of iterations for robot movements.
    :param movement_threshold: Threshold for robot movements. When attempted movement is less than this, centering is complete.
    :param max_movement_radius: Maximum movement radius in mm of robot form the initial position to prevent robot going too far in case of error.
    :param detection_confidence: Detection confidence in range [0, 1] for circle detection.
    :param max_contours: Maximum number of contours in circle detection.
    :param delay: Delay between iterations. This gives chance to e.g. change exposure to help the algorithm.
    :return: True if centering was successful. False centering was not successful within max_iterations.
    """
    ppmm = camera.ppmm

    # Keep track of robot movement length to prevent wandering too far from start.
    frame = robot.effective_frame
    start_x, start_y, _ = frame_to_xyz(frame)
    robot_x, robot_y = start_x, start_y

    for i in range(max_iterations):
        # Take image with camera.
        _, image = camera.get_still("none")

        height, width = image.shape[:2]
        camera_center = [width / 2, height / 2]

        # Find slot closest to camera center.
        slot_centers, fiducial_centers = find_slots_from_image(image, fiducial_radius, tip_hole_radius, radius_margin,
                                                               detection_confidence, max_contours)

        indices = filter_tip_slots(slot_centers, fiducial_centers, ff_distance, fs_distance,
                                   detection_threshold)

        if len(indices) == 0:
            log.warning("Could not find tip!")

            # Sleep for a while to let user affect e.g. lighting conditions if algorithm is failing.
            time.sleep(delay)

            # TODO: Try something else e.g. random offset or autoexposure.
            continue

        # Pick slot center closest to camera center as target.
        target = slot_centers[indices[0]]

        diff_x = (target[0] - camera_center[0])  / ppmm
        diff_y = (target[1] - camera_center[1]) / ppmm

        if norm([diff_x, diff_y]) < movement_threshold:
            log.info("Centered camera to tip with given threshold.")
            return True

        robot_x += diff_x
        robot_y += diff_y

        if norm([robot_x - start_x, robot_y - start_y]) > max_movement_radius:
            log.error("Attempt to move over {} from start position. Try starting closer to target.".format(max_movement_radius))
            return False

        robot.move_relative(x=diff_x, y=diff_y)

    log.error("Could not center camera to tip within {} iterations!".format(max_iterations))

    return False


class TipFiducial:
    """
    Detector for finding tip rack slot positions from standard tip rack.
    A tip must be attached to the rack slot.
    The algorithm tries to find tip hole and two circular fiducials at fixed distances from the hole.
    User can either just detect the fiducials with camera or simultaneously move robot to center the camera
    over a slot closest to camera center.
    """
    def __init__(self, fiducial_radius=1, tip_hole_radius=3.5, ff_distance=11.32, fs_distance=7.94,
                 detection_threshold=0.4, radius_margin=0.2, robot_name="Robot1", camera_name="Camera1",
                 max_iterations=20, movement_threshold=0.01, max_movement_radius=50,
                 detection_confidence=0.7, max_contours=100, delay=1.0, **kwargs):
        """
        Initialize tip fiducial detector driver.
        :param fiducial_radius: Fiducial radius in mm.
        :param tip_hole_radius: Tip hole radius in mm.
        :param ff_distance: Fiducial-fiducial distance in mm.
        :param fs_distance: Fiducial-slot distance in mm.
        :param detection_threshold: Threshold for ff and fs distance comparison in mm.
        :param radius_margin: Margin for circle radius detection in mm.
        :param robot_name: Name of robot to use in movements.
        :param camera_name: Name of camera to use in detection.
        :param max_iterations: Maximum number of iterations when centering camera to target.
        :param movement_threshold: Movement threshold in mm when centering camera to target.
        :param max_movement_radius: Maximum radius robot is allowed to move from starting point in mm.
        :param detection_confidence: Confidence of circle detection in [0, 1].
        :param max_contours: Maximum number of contours to find in circle detection.
        :param delay: Time delay between detections in case detection fails.
        :param kwargs: Extra keyword arguments.
        """

        self.fiducial_radius = fiducial_radius
        self.tip_hole_radius = tip_hole_radius
        self.ff_distance = ff_distance
        self.fs_distance = fs_distance
        self.detection_threshold = detection_threshold
        self.radius_margin = radius_margin

        self.max_iterations = max_iterations
        self.movement_threshold = movement_threshold
        self.max_movement_radius = max_movement_radius

        self.detection_confidence = detection_confidence
        self.max_contours = max_contours
        self.delay = delay

        self.robot_name = robot_name
        self.camera_name = camera_name

    def detect(self, center_camera=False, radius_margin=None, detection_threshold=None):
        """
        Detect tip slot position in tip rack based on circular fiducials.
        :param center_camera: If True, move robot so that camera center is at slot center. If False, only detect from image.
        :param radius_margin: Margin in mm for detecting fiducial and tip slot. Default value from init.
        :param detection_threshold: Threshold in mm for determining if fiducial and slot positions form correct triangle. Default value from init.
        :return: List of found xy-positions in pixel coordinates e.g. [[x1, y1], [x2, y2]].
        The list is sorted by increasing distance from the camera center.
        """

        # TODO: Should detector driver access nodes directly? At the moment there is no other way to access camera.
        camera = Node.find(self.camera_name)

        ppmm = camera.ppmm

        t, image = camera.get_still("none")

        if radius_margin is None:
            radius_margin = self.radius_margin

        if detection_threshold is None:
            detection_threshold = self.detection_threshold

        # Convert parameters from pixel units to mm for the detection algorithms that work in pixel units.
        fiducial_radius = self.fiducial_radius * ppmm
        tip_hole_radius = self.tip_hole_radius * ppmm
        radius_margin = radius_margin * ppmm
        detection_threshold = detection_threshold * ppmm
        ff_distance = self.ff_distance * ppmm
        fs_distance = self.fs_distance * ppmm

        slot_centers, fiducial_centers = find_slots_from_image(image, fiducial_radius, tip_hole_radius, radius_margin,
                                                               self.detection_confidence, self.max_contours)

        indices = filter_tip_slots(slot_centers, fiducial_centers, ff_distance, fs_distance, detection_threshold)

        # Move robot to center camera over slot closest to camera center.
        if center_camera:
            robot = Node.find(self.robot_name)

            result = center_camera_to_tip(camera, robot, fiducial_radius, tip_hole_radius, ff_distance, fs_distance,
                                 radius_margin, detection_threshold, self.max_iterations, self.movement_threshold,
                                          self.max_movement_radius, self.detection_confidence, self.max_contours,
                                          self.delay)

            if not result:
                raise NodeException("Could not successfully center camera to tip!")

        return [slot_centers[i] for i in indices]