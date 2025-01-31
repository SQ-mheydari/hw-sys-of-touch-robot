from tntserver.drivers.robots.goldenmov.kinematics.kinematic_synchro import Kinematic_synchro
import math
import numpy as np


def rotation_matrix(angle):
    c = np.cos(angle)
    s = np.sin(angle)

    return np.array([[c, s], [-s, c]])


class Robot:
    """
    Stub robot class to enable testing
    """

    def _init_(self):
        pass

    @property
    def calibration_data(self):
        return {}


def test_synchro_offset():
    """
    Test that  compute_synchro_finger_camera_offsets() is able to determine camera and finger offsets
    from simulated data.
    """
    # Camera offset that the calibration should determine.
    camera_offset = np.array([-5, 40])

    # Finger offset that the calibration should determine.
    finger_offset = np.array([16, -1])

    measurements = []

    # Number of simulated measurement angles.
    num_angles = 10

    # Simulated audit gauge location. This is arbitrary and should not affect the result.
    audit_gauge_location = np.array([-40, 20])

    k = Kinematic_synchro(robot=Robot())

    for i in range(num_angles):
        angle = 2 * math.pi * i / num_angles

        # Robot head position when finger is at audit gauge.
        robot_finger = audit_gauge_location - rotation_matrix(angle) @ finger_offset

        # Robot head position when the camera is at audit gauge.
        robot_camera = audit_gauge_location - camera_offset

        # Append simulated measurement
        measurements.append((angle, robot_finger[0], robot_finger[1], robot_camera[0], robot_camera[1]))

    # Calculate offsets.
    r = k.calibrate({'measurements': measurements})
    calc_camera_offset, calc_finger_offset, residual_error = r['camera_offset'], r['tool_offset'], r['residual_error']
    # Make sure the results match the known offsets.
    assert np.allclose(calc_camera_offset, camera_offset)
    assert np.allclose(calc_finger_offset, finger_offset)
    assert abs(residual_error) < 1e-6

