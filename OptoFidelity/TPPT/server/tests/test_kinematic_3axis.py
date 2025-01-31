from tntserver.drivers.robots.goldenmov.kinematics.kinematic_3axis import *
import numpy as np


class Robot:
    """
    Stub robot class to enable testing
    """

    def _init_(self):
        pass

    @property
    def calibration_data(self):
        return {}


def test_robot_fk_ik():
    """
    Test robot forward and inverse kinematics together by checking if going
    back and forth the whole chain returns the given input value
    """
    robot = Robot()
    k = Kinematic_3axis(robot)

    toolframe = np.matrix([[1, 0, 0, 10],
                           [0, 1, 0, 20],
                           [0, 0, 1, 30],
                           [0, 0, 0, 1]])

    def test(x, y, z):
        joints = {"x": x, "y": y, "z": z}
        position_fk = k.joints_to_position(joints, tool=toolframe)
        joints_ik = k.positions_to_joints([position_fk], tool_inv=toolframe.I)[0]

        for key, value in joints.items():
            assert np.isclose(value, joints_ik[key])

    test(10, 20, 30)
    test(30, 30, 30)
    test(30, 100, 30)
    test(34.5, 30, 80.7)
    test(0, 70.2, 60)
    test(200, 30, 78)
    test(53.8, 123, 54)


def test_robot_fk():
    """
    Test robot forward kinematics with precalculated joint and frame values
    """
    robot = Robot()
    k = Kinematic_3axis(robot)
    toolframe = np.matrix([[1, 0, 0, 10],
                           [0, 1, 0, 20],
                           [0, 0, 1, 30],
                           [0, 0, 0, 1]])

    joints = {"x": 20, "y": 20, "z": 20}

    position_fk = k.joints_to_position(joints=joints, tool=toolframe)
    fk_frame = np.matrix([[-1, 0, 0, 10],
                          [0, 1, 0, 40],
                          [0, 0, -1, -50],
                          [0, 0, 0, 1]])
    assert np.allclose(position_fk.frame, fk_frame)


def test_robot_ik():
    """
    Test robot inverse kinematics with precalculated joint and frame values
    """
    robot = Robot()
    k = Kinematic_3axis(robot)
    tool = np.matrix([[1, 0, 0, 10],
                      [0, 1, 0, 20],
                      [0, 0, 1, 30],
                      [0, 0, 0, 1]])

    joints = {"x": 30, "y": 10, "z": -10}

    fk_frame = np.matrix([[-1, 0, 0, 20],
                          [0, 1, 0, 30],
                          [0, 0, -1, -20],
                          [0, 0, 0, 1]])
    fk_position = k.create_robot_position(frame=fk_frame)
    joints_ik = k.positions_to_joints(positions=[fk_position], tool_inv=tool.I)[0]

    for key, value in joints.items():
        assert np.isclose(value, joints_ik[key])


def test_filter():
    frame = robotmath.pose_to_frame(robotmath.xyz_to_frame(10, 20, 30))
    filtered = filter_frame_3axis(frame)

    # Test that filtering a frame with no rotation does nothing.
    assert np.allclose(frame, filtered)

    frame = robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(10, 20, 30, 40, 50, 60))
    frame_no_rot = robotmath.pose_to_frame(robotmath.xyz_to_frame(10, 20, 30))
    filtered = filter_frame_3axis(frame)

    # Test that filtering removes rotations but keeps translation.
    assert np.allclose(frame_no_rot, filtered)