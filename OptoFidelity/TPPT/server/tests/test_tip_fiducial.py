from tntserver.drivers.detectors.TipFiducial import *
from tntserver.robotmath import xyz_to_frame, pose_to_frame
from math import sqrt
import cv2
import os
import pytest
import numpy as np


def test_filter_tip_slots():
    hole_separation = 20
    fiducial_offset = 5
    fiducial_x = 6

    slot_centers = [
        (0, 0),
        (0, hole_separation),
        (0, hole_separation * 2)
    ]

    fiducial_centers = [
        (fiducial_x, -fiducial_offset),
        (fiducial_x, fiducial_offset),
        (fiducial_x, hole_separation - fiducial_offset),
        (fiducial_x, hole_separation + fiducial_offset),
        (fiducial_x, hole_separation * 2 - fiducial_offset),
        (fiducial_x, hole_separation * 2 + fiducial_offset)
    ]

    ff_distance = 2 * fiducial_offset
    fs_distance = sqrt(fiducial_x**2 + fiducial_offset**2)

    threshold = 0.001

    filtered = filter_tip_slots(slot_centers, fiducial_centers, ff_distance, fs_distance, threshold)

    # Pass find all centers.
    assert filtered == [0, 1, 2]


def test_filter_tip_slots_imperfect():
    slot_separation = 20
    fiducial_offset = 5
    fiducial_x = 6

    slot_centers = [
        (0, 0),
        (0, slot_separation),
        (0, slot_separation * 2)
    ]

    threshold = 0.001

    # Offset the fiducials so that only the first slot center is valud.
    fiducial_centers = [
        (fiducial_x, -fiducial_offset),
        (fiducial_x, fiducial_offset),
        (fiducial_x, slot_separation - fiducial_offset),
        (fiducial_x, slot_separation + fiducial_offset + 2 * threshold),
        (fiducial_x, slot_separation * 2 - fiducial_offset),
        (fiducial_x + 2 * threshold, slot_separation * 2 + fiducial_offset)
    ]

    ff_distance = 2 * fiducial_offset
    fs_distance = sqrt(fiducial_x**2 + fiducial_offset**2)

    filtered = filter_tip_slots(slot_centers, fiducial_centers, ff_distance, fs_distance, threshold)

    # Only first center should pass.
    assert len(filtered) == 1 and filtered[0] == 0


def test_find_slots_from_image():
    width = 500
    height = 800

    image = np.zeros((height, width, 3), np.uint8)

    slot_radius = 40

    slot_separation = 200
    slot_x = 200
    slot_y = 200

    fiducial_radius = 20
    fiducial_x_offset = 80
    fiducial_y_offset = 70

    for i in range(3):
        cv2.circle(image, (slot_x, slot_y + slot_separation * i), slot_radius, (255, 255, 255), -1)

        cv2.circle(image, (slot_x + fiducial_x_offset, slot_y + slot_separation * i - fiducial_y_offset), fiducial_radius, (255, 255, 255), -1)
        cv2.circle(image, (slot_x + fiducial_x_offset, slot_y + slot_separation * i + fiducial_y_offset), fiducial_radius, (255, 255, 255), -1)

    # Uncomment to debug images.
    #from optovision.utils.vision_utils import set_optovision_debug_image_dir, showImage, get_optovision_debug_image_dir
    #set_optovision_debug_image_dir(".")
    #showImage("window", image)
    #cv2.waitKey(0)

    slot_centers, fiducial_centers = find_slots_from_image(image, fiducial_radius, slot_radius, 6, 0.7, 100)

    reference_slot_centers = [(200.0, 400.0), (200.0, 600.0), (200.0, 200.0)]
    reference_fiducial_centers = [(280.0, 470.0), (280.0, 330.0), (280.0, 530.0), (280.0, 270.0), (280.0, 670.0), (280.0, 130.0)]

    assert slot_centers == reference_slot_centers
    assert fiducial_centers == reference_fiducial_centers


def test_tip_rack_detection():
    image = cv2.imread(os.path.join("tests", "data", "images", "tip_rack_fiducial.png"))

    fiducial_radius = 16
    slot_radius = 57

    slot_centers, fiducial_centers = find_slots_from_image(image, fiducial_radius, slot_radius, 10, 0.7, 100)

    print(slot_centers)
    print(fiducial_centers)

    ff_distance = 192
    fs_distance = sqrt((ff_distance/2)**2 + 100**2)
    detection_threshold = 10

    for c in slot_centers:
        cv2.circle(image, (int(c[0]), int(c[1])), slot_radius, (255, 0, 0), 2)

    for c in fiducial_centers:
        cv2.circle(image, (int(c[0]), int(c[1])), fiducial_radius, (0, 0, 255), 2)

    # Uncomment to debug images.
    #from optovision.utils.vision_utils import set_optovision_debug_image_dir, showImage, get_optovision_debug_image_dir
    #showImage("window", image)
    #cv2.waitKey(0)

    indices = filter_tip_slots(slot_centers, fiducial_centers, ff_distance, fs_distance, detection_threshold)

    # Should find two matches.
    assert len(indices) == 2
    assert np.allclose(slot_centers[0], (454.37017822265625, 670.84619140625))
    assert np.allclose(slot_centers[1], (454.3057861328125, 1093.672119140625))


class StubRobot:
    """
    Stub robot to simulate robot relative movements.
    """
    def __init__(self):
        self.x = 0
        self.y = 0

    def move_relative(self, x, y):
        self.x += x
        self.y += y

    @property
    def effective_frame(self):
        pose = xyz_to_frame(self.x, self.y, 0)
        return pose_to_frame(pose)


class StubCamera:
    """
    Stub camera to simulate camera that moves with robot and takes images of slot+fiducial target.
    """
    def __init__(self, ppmm, robot):
        self.ppmm = ppmm
        self.robot = robot

        # How much camera offset is scaled from robot movement.
        # This simulates behavior that if camera moves at constant steps the target in camera image
        # might not move at exactly constant steps due to perspective projection and distortion.
        self.move_scale = 1.2

    def get_still(self, format):
        return None, self.create_image()

    def create_image(self):
        # Offset image with robot to simulate camera that moves with robot.
        # Camera image moves to direction opposite to robot movement.
        offset_x = -self.robot.x * self.ppmm * self.move_scale
        offset_y = -self.robot.y * self.ppmm * self.move_scale

        width = 600
        height = 600

        image = np.zeros((height, width, 3), np.uint8)

        slot_radius = 40

        slot_x = int(round(width / 2 + offset_x))
        slot_y = int(round(height / 2 + offset_y))

        fiducial_radius = 20
        fiducial_x_offset = 80
        fiducial_y_offset = 70

        cv2.circle(image, (slot_x, slot_y), slot_radius, (255, 255, 255), -1)

        cv2.circle(image, (slot_x + fiducial_x_offset, slot_y - fiducial_y_offset),
                   fiducial_radius, (255, 255, 255), -1)
        cv2.circle(image, (slot_x + fiducial_x_offset, slot_y + fiducial_y_offset),
                   fiducial_radius, (255, 255, 255), -1)

        # Uncomment to debug images.
        #cv2.imshow("window", image)
        #cv2.waitKey(0)

        return image


@pytest.mark.parametrize(["robot_start_x", "robot_start_y"], [[-10, 15], [4, 12], [-2, 7], [12, -8]])
def test_center_camera_to_tip(robot_start_x, robot_start_y):
    robot = StubRobot()

    # When robot is at (0, 0) the target is visible at camera center. Move robot start position
    # away from origin to test the centering.
    robot.x = robot_start_x
    robot.y = robot_start_y

    # ppmm is arbitrary in this test.
    ppmm = 10

    camera = StubCamera(ppmm=ppmm, robot=robot)

    fiducial_radius = 20
    tip_hole_radius = 40
    ff_distance = 2 * 70
    fs_distance = sqrt(70**2 + 80**2)
    radius_margin = 6
    detection_threshold = 6

    result = center_camera_to_tip(camera, robot, fiducial_radius, tip_hole_radius, ff_distance, fs_distance,
                         radius_margin, detection_threshold, max_iterations=20, movement_threshold=0.01, delay=0)

    assert result == True
    assert np.allclose([robot.x, robot.y], [0, 0])
