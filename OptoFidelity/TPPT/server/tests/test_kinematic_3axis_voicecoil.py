import numpy as np
import pytest

from tntserver.drivers.robots.goldenmov.kinematics.kinematic_3axis_voicecoil import *


voicecoil_joint_name = Kinematic_3axis_voicecoil.voicecoil_joint_name

joint_sets = (
    # x, y, z, vc1
    (10, 20, 30, 0),
    (30, 30, 30, 0),
    (30, 100, 30, 0),
    (34.5, 30, 80.7, 0),
    (0, 70.2, 60, 0),
    (200, 30, 78, 0),
    (53.8, 123, 54, 0),
    (10, 20, 30, 10),
    (59, 32, 30, 10),
    (30, 104, 30, 3),
    (34.5, 30, 80.7, 5),
    (0, 70.2, 60, 3),
    (220, 37, 78, 1),
    (53.8, 123, 54, 5),
)

toolframe = np.matrix([[1, 0, 0, 10],
                       [0, 1, 0, 20],
                       [0, 0, 1, 30],
                       [0, 0, 0, 1]])


class Robot:
    """
    Stub robot class to enable testing
    """
    def _init_(self):
        pass

    @property
    def calibration_data(self):
        return {'ap_model': {'coefficients': {'x': {'x': [0, 0, 0],
                                                    'y': [0, 0, 0],
                                                    'z': [0, 0, 0]}
                                              }}}


class MockRobotDriver:
    axis_setpoint = {
        'x': 0,
        'y': 0,
        'z': 0,
        voicecoil_joint_name: 0
    }

    def get_scaled_axis_setpoint(self, axis_name):
        return self.axis_setpoint[axis_name]

    def set_axis_setpoints(self, setpoints: dict):
        self.axis_setpoint.update(setpoints)


@pytest.fixture(scope='function')
def kinematics():
    """
    Returns voicecoil robot kinematics
    :return: 3-axis voicecoil robot kinematics
    """
    robot = Robot()
    kinematics = Kinematic_3axis_voicecoil(robot)
    kinematics.driver = MockRobotDriver()
    kinematics.driver.axis_setpoint = {
        'x': 0,
        'y': 0,
        'z': 0,
        voicecoil_joint_name: 0
    }
    return kinematics


@pytest.mark.parametrize("joint_set", joint_sets)
def test_robot_fk_ik(joint_set: tuple, kinematics):
    """
    Test robot forward and inverse kinematics together by checking if going
    back and forth the whole chain returns the given input value
    """

    def test(x, y, z, vc1):
        joints = {"x": x, "y": y, "z": z, voicecoil_joint_name: vc1}
        kinematics.driver.axis_setpoint[voicecoil_joint_name] = joints[voicecoil_joint_name]
        position_fk = kinematics.joints_to_position(joints, tool=toolframe)
        joints_ik = kinematics.positions_to_joints([position_fk], tool_inv=toolframe.I)[0]

        for key, value in joints.items():
            assert np.isclose(value, joints_ik[key])

    test(*joint_set)


def test_robot_fk(kinematics):
    """
    Test robot forward kinematics with precalculated joint and frame values
    """
    joints = {"x": 20, "y": 20, "z": 20, voicecoil_joint_name: 0}
    position_fk = kinematics.joints_to_position(joints=joints, tool=toolframe)
    fk_frame = np.array([[-1, 0, 0, 10],
                          [0, 1, 0, 40],
                          [0, 0, -1, -50],
                          [0, 0, 0, 1]])
    assert np.allclose(position_fk.frame, fk_frame)


def test_robot_ik_01(kinematics):
    """
    Test robot inverse kinematics with precalculated joint and frame values
    """
    joints = {"x": 30, "y": 0, "z": -10, voicecoil_joint_name: 0}
    axis_setpoints = {"z": 20, voicecoil_joint_name: 0}
    kinematics.driver.set_axis_setpoints(axis_setpoints)
    fk_frame = np.matrix([[-1, 0, 0, 20],
                          [0, 1, 0, 20],
                          [0, 0, -1, -20],
                          [0, 0, 0, 1]])
    fk_position = kinematics.create_robot_position(frame=fk_frame)
    joints_ik = kinematics.positions_to_joints(positions=[fk_position], tool_inv=toolframe.I)[0]

    for key, value in joints.items():
        assert np.isclose(value, joints_ik[key])


def test_robot_ik_02(kinematics):
    """
    Test both None and voicecoil1 kinematics
    """
    joints_vc = {"x": 30, "y": 0, "z": 5, voicecoil_joint_name: -10}
    joints = {"x": 30, "y": 0, "z": -10, voicecoil_joint_name: 5}
    axis_setpoints = {"z": 5, voicecoil_joint_name: 5}
    fk_frame = np.matrix([
        [-1, 0, 0, 20],
        [0, 1, 0, 20],
        [0, 0, -1, -25],
        [0, 0, 0, 1]])
    # end of test data

    kinematics.driver.set_axis_setpoints(axis_setpoints)

    fk_position = kinematics.create_robot_position(frame=fk_frame)
    joints_ik_vc = kinematics.positions_to_joints(positions=[fk_position], kinematic_name=voicecoil_joint_name,
                                                  tool_inv=toolframe.I)[0]
    joints_ik = kinematics.positions_to_joints(positions=[fk_position], kinematic_name=None, tool_inv=toolframe.I)[0]

    for key, value in joints.items():
        assert np.isclose(value, joints_ik[key])
    for key, value in joints_vc.items():
        assert np.isclose(value, joints_ik_vc[key])


def test_voicecoil_ik_01(kinematics):
    # test data
    z = 5
    joints = {"x": 30, "y": 00, "z": z, voicecoil_joint_name: 5}
    axis_setpoints = {"z": z, voicecoil_joint_name: 5}
    fk_frame = np.matrix([[-1, 0, 0, 20],
                          [0, 1, 0, 20],
                          [0, 0, -1, -40],
                          [0, 0, 0, 1]])
    # end of test data
    fk_position = kinematics.create_robot_position(frame=fk_frame)
    kinematics.driver.set_axis_setpoints(axis_setpoints)
    joints_ik = kinematics.positions_to_joints(positions=[fk_position], kinematic_name=voicecoil_joint_name,
                                               tool_inv=toolframe.I)[0]

    for key, value in joints.items():
        assert np.isclose(value, joints_ik[key])


def test_voicecoil_ik_02(kinematics):
    # test data
    z = -20
    joints = {"x": 30, "y": 0, "z": z, voicecoil_joint_name: -20}
    axis_setpoints = {"z": z, voicecoil_joint_name: -20}
    fk_frame = np.matrix([
        [-1, 0, 0, 20],
        [0, 1, 0, 20],
        [0, 0, -1, 10],
        [0, 0, 0, 1]])
    # end of test data
    fk_position = kinematics.create_robot_position(frame=fk_frame)
    kinematics.driver.set_axis_setpoints(axis_setpoints)
    joints_ik = kinematics.positions_to_joints(positions=[fk_position], kinematic_name=voicecoil_joint_name,
                                               tool_inv=toolframe.I)[0]

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


def test_axis_setpoint_fk(kinematics):
    """
    Test robot forward kinematics with different axis setpoint and joint value
    """
    joints = {"x": 20, "y": 20, "z": 10, voicecoil_joint_name: 10}
    fk_frame = np.matrix([[-1, 0, 0, 10],
                          [0, 1, 0, 40],
                          [0, 0, -1, -50],
                          [0, 0, 0, 1]])
    # driver setpoint is used instead of joint value in calulation
    kinematics.driver.axis_setpoint[voicecoil_joint_name] = 0
    position_fk = kinematics.joints_to_position(joints, tool=toolframe)
    # If axis_setpoint is different than joint value then
    assert not np.allclose(position_fk.frame, fk_frame)
    kinematics.driver.axis_setpoint[voicecoil_joint_name] = 10
    position_fk = kinematics.joints_to_position(joints, tool=toolframe)
    assert np.allclose(position_fk.frame, fk_frame)


def test_force_fk(kinematics):
    joints = {"x": 20, "y": 30, "z": 10, voicecoil_joint_name: 10}
    fk_frame = np.array([[-1, 0, 0, 10],
                         [0, 1, 0, 50],
                         [0, 0, -1, -40],
                         [0, 0, 0, 1]])

    # Force kinematics must neglect VC position.
    kinematics.driver.axis_setpoint[voicecoil_joint_name] = 0
    position_fk = kinematics.joints_to_position(joints, kinematic_name="force", tool=toolframe)

    # If axis_setpoint is different than joint value then
    assert np.allclose(position_fk.frame, fk_frame)

    # Force kinematics must neglect VC setpoint.
    kinematics.driver.axis_setpoint[voicecoil_joint_name] = 10
    position_fk = kinematics.joints_to_position(joints, kinematic_name="force", tool=toolframe)

    assert np.allclose(position_fk.frame, fk_frame)


def test_force_ik(kinematics):
    """
    Test robot inverse kinematics with precalculated joint and frame values
    """
    joints = {"x": 30, "y": 10, "z": -20}

    kinematics.driver.axis_setpoint[voicecoil_joint_name] = 40

    fk_frame = np.matrix([[-1, 0, 0, 20],
                          [0, 1, 0, 30],
                          [0, 0, -1, -10],
                          [0, 0, 0, 1]])

    fk_position = kinematics.create_robot_position(frame=fk_frame)
    joints_ik = kinematics.positions_to_joints([fk_position], kinematic_name="force", tool_inv=toolframe.I)

    # Only one point.
    joints_ik = joints_ik[0]

    for key, value in joints.items():
        assert np.isclose(value, joints_ik[key])

    # With force mode the join dict can not have voicecoil position to prevent axis going to position mode
    # in Optomotion.
    assert voicecoil_joint_name not in joints_ik
