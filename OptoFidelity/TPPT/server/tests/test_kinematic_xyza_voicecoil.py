from tntserver.drivers.robots.goldenmov.kinematics.kinematic_xyza_voicecoil import *
import pytest


class GoldenMovStub:
    def __init__(self):
        self.axis_setpoints = {"x": 0, "y": 0, "z": 0, "azimuth": 0, "voicecoil1": 0}

    def get_scaled_axis_setpoint(self, axis_alias):
        return self.axis_setpoints[axis_alias]

    def set_axis_setpoints(self, setpoints: dict):
        self.axis_setpoints.update(setpoints)


class Robot:
    """
    Stub robot class to enable testing
    """

    def _init_(self):
        pass

    @property
    def calibration_data(self):
        return {}


toolframe = np.matrix([[1, 0, 0, 10],
                       [0, 1, 0, 20],
                       [0, 0, 1, 30],
                       [0, 0, 0, 1]])


@pytest.mark.parametrize(["x", "y", "z", "azimuth", "current_azimuth", "final_azimuth"], [
(10, 20, 30, 45, 0, 45), (30, 30, 30, 29, 20, 29), (30, 100, 30, 140, 300, 140),
(34.5, 30, 80.7, 90, -300, -270), (0, 70.2, 60, -3.7, 600, 716.3),
(200, 30, 78, 180, -600, -540), (53.8, 123, 54, 90, -39.6, 90)
  ])
def test_robot_fk_ik(x, y, z, azimuth, current_azimuth, final_azimuth):
    """
    Test forward and inverse kinematics functions. Please not that voice coils
    are handled separately and, thus, they are not part of the kinematic chain.
    Also the azimuth needs special handling, because joints can only be between
    [-180, 180] and the axis value can be in range [-inf, inf]
    """
    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()
    joints = {"x": x, "y": y, "z": z, "azimuth": azimuth,
              "voicecoil1": 0}
    # run forward kinematics to change joints to robot position
    fk_pos = k.joints_to_position(joints=joints, tool=toolframe)
    # run inverse kinematics to return robot position to joints
    axis_setpoints = {"azimuth": current_azimuth}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_pos], tool_inv=toolframe.I)[0]

    # compare if joints are returned as they were
    for key, value in joints.items():
        # azimuth value is a special case as described in docstring
        if key == "azimuth":
            assert np.isclose(ik_joints[key], final_azimuth)
        else:
            assert np.isclose(joints[key], ik_joints[key])


def test_robot_fk():
    """
    Test robot forward kinematics with precalculated joints and frames
    """

    joints = {"x": 20, "y": 20, "z": 20, "azimuth": 30,
              "voicecoil1": 0}

    def calc_fk_pos():
        robot = Robot()
        k = Kinematic_xyza_voicecoil(robot)
        k.driver = GoldenMovStub()
        fk_pos = k.joints_to_position(joints=joints, tool=toolframe)
        return fk_pos

    ref_frame = [[-8.66025404e-01,  5.00000000e-01,  6.12323400e-17,  2.13397460e+01],
                 [5.00000000e-01,  8.66025404e-01,  1.06057524e-16,  4.23205081e+01],
                 [0.00000000e+00,  1.22464680e-16, -1.00000000e+00, -5.00000000e+01],
                 [0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]]

    fk_pos = calc_fk_pos()
    assert np.allclose(ref_frame, fk_pos.frame)


def test_robot_ik_0deg():
    """
    Test robot inverse kinematics with precalculated joints and frames, azimuth 0 degrees
    """
    test_frame = np.matrix([[-1, 0, 0, 20],
                            [0, 1, 0, 20],
                            [0, 0, -1, -20],
                            [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()
    current_azimuth = 0

    fk_position = k.create_robot_position(frame=test_frame)
    joints = {"x": 30, "y": 0, "z": -10.0, "azimuth": 0}

    axis_setpoints = {"azimuth": current_azimuth, "voicecoil1": 0}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_position], tool_inv=toolframe.I)[0]

    for key, _ in joints.items():
        assert np.isclose(joints[key], ik_joints[key])


def test_robot_ik_90deg():
    """
    Test robot inverse kinematics with precalculated joints and frames, azimuth 90 degrees
    """
    test_frame = np.matrix([[0, 1, 0, 20],
                            [-1, 0, 0, 20],
                            [0, 0, -1, -20],
                            [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()
    current_azimuth = 0

    fk_position = k.create_robot_position(frame=test_frame)
    joints = {"x": 0, "y": 30, "z": -10.0, "azimuth": 90}

    axis_setpoints = {"azimuth": current_azimuth, "voicecoil1": 0}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_position], tool_inv=toolframe.I)[0]

    for key, _ in joints.items():
        assert np.isclose(joints[key], ik_joints[key])


def test_voicecoils_robot_fk():
    """
    Test voicecoil value handling in robot_fk
    """
    # Having different values for all of these makes it possible
    # to see if the correct value is used in function
    voicecoil1_new = 5

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()
    joints = {"x": 0, "y": 0, "z": 0, "azimuth": 0,
              "voicecoil1": voicecoil1_new}
    fk_pos = k.joints_to_position(joints=joints, tool=toolframe)

    assert np.isclose(fk_pos.voicecoil1, 0)


def test_voicecoils_camera_fk():
    """
    Test voicecoil value handling in camera_fk
    """
    # Having different values for all of these makes it possible
    # to see if the correct value is used in function
    voicecoil1_new = 5

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()

    joints = {"x": 0, "y": 0, "z": 0, "azimuth": 0,
              "voicecoil1": voicecoil1_new}
    fk_pos = k.joints_to_position(joints=joints, kinematic_name="camera", tool=toolframe)

    assert np.isclose(fk_pos.voicecoil1, 0)


def test_voicecoils_robot_ik():
    """
    Test voicecoil value handling in robot_ik
    """
    fk_pos_frame = np.matrix([[-1, 0, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, -1, 0],
                              [0, 0, 0, 1]])
    # Having different values for all of these makes it possible
    # to see if the correct value is used in function
    fk_voicecoil1 = 5

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_pos_frame, voicecoil1=fk_voicecoil1)

    axis_setpoints = {"azimuth": 0}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_pos], tool_inv=toolframe.I)[0]

    assert np.isclose(fk_voicecoil1, ik_joints["voicecoil1"])


def test_voicecoil_ik():
    """
    Test that VC is moved and z is stationary when using "voicecoil1" kinematics.
    """
    fk_pos_frame = np.matrix([[-1, 0, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, -1, -20],
                              [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_pos_frame)

    axis_setpoints = {"azimuth": 0, "voicecoil1": 0, "z": 0}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="voicecoil1", tool_inv=toolframe.I)[0]

    assert np.isclose(-10, ik_joints["voicecoil1"])
    assert np.isclose(0, ik_joints["z"])


def test_tool1_ik():
    """
    Test that z is moved and VC is stationary when using "tool1" kinematics.
    """
    fk_pos_frame = np.matrix([[-1, 0, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, -1, -20],
                              [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_pos_frame)

    axis_setpoints = {"azimuth": 0, "voicecoil1": 0, "z": 0}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="tool1", tool_inv=toolframe.I)[0]

    assert np.isclose(0, ik_joints["voicecoil1"])
    assert np.isclose(-10, ik_joints["z"])


def test_voicecoils_camera_ik():
    """
    Test voicecoil value handling in camera_ik
    """
    fk_pos_frame = np.matrix([[-1, 0, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, -1, 0],
                              [0, 0, 0, 1]])
    # Having different values for all of these makes it possible
    # to see if the correct value is used in function
    fk_voicecoil1 = 5

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_pos_frame, voicecoil1=fk_voicecoil1)

    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="camera")[0]

    assert np.isclose(fk_voicecoil1, ik_joints["voicecoil1"])


@pytest.mark.parametrize(["x", "y", "z"], [
    (10, 20, 30), (30, 30, 30), (30, 100, 30),
    (34.5, 30, 80.7), (0, 70.2, 60), (200, 30, 78), (53.8, 123, 54)])
def test_camera_fk_ik(x, y, z):
    """
    Test camera forward and inverse kinematics
    """

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()
    joints = {"x": x, "y": y, "z": z,
              "voicecoil1": 0}
    # run forward kinematics to change joints to robot position
    fk_pos = k.joints_to_position(joints=joints, kinematic_name="camera", tool=toolframe)
    # run inverse kinematics to return robot position to joints
    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="camera", tool_inv=toolframe.I)[0]

    # compare if joints are returned as they were
    for key, value in joints.items():
        assert np.isclose(value, ik_joints[key])


@pytest.mark.parametrize("azimuth", [None, 0, 45])
def test_camera_fk(azimuth):
    """
    Testing camera forward kinematics alone and also checking that givin/changing
    azimuth value does not affect
    """
    # The results should be the same for all the cases
    fk_pos_frame = np.matrix([[-1, 0, 0, 30],
                              [0, 1, 0, 50],
                              [0, 0, -1, -100],
                              [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()
    if azimuth is None:
        joints = {"x": 40, "y": 30, "z": 70,
                  "voicecoil1": 0}
    else:
        joints = {"x": 40, "y": 30, "z": 70,
                  "voicecoil1": 0, "azimuth": azimuth}

    fk_pos = k.joints_to_position(joints=joints, kinematic_name="camera", tool=toolframe)
    assert np.allclose(fk_pos.frame, fk_pos_frame)


@pytest.mark.parametrize("turn_azimuth", [True, False])
def test_camera_ik(turn_azimuth):
    """
    Testing camera inverse kinematics alone and also checking that givin/changing
    azimuth value does not affect
    """
    # The results should be the same for all the cases
    joints = {"x": 40, "y": 30, "z": 70,
              "voicecoil1": 0}

    robot = Robot()
    k = Kinematic_xyza_voicecoil(robot)
    k.driver = GoldenMovStub()
    if turn_azimuth:
        fk_pos_frame = np.matrix([[0, -1, 0, 30],
                                  [1, 0, 0, 50],
                                  [0, 0, -1, -100],
                                  [0, 0, 0, 1]])
    else:
        fk_pos_frame = np.matrix([[-1, 0, 0, 30],
                                  [0, 1, 0, 50],
                                  [0, 0, -1, -100],
                                  [0, 0, 0, 1]])

    fk_pos = k.create_robot_position(frame=fk_pos_frame, voicecoil1=0)
    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="camera", tool_inv=toolframe.I)[0]

    for key, _ in ik_joints.items():
        assert np.isclose(ik_joints[key], joints[key])


def test_filter():
    frame = robotmath.pose_to_frame(robotmath.xyz_to_frame(10, 20, 30))
    filtered = filter_frame_xyza(frame)

    # Test that filtering a frame with no rotation does nothing.
    assert np.allclose(frame, filtered)

    frame = robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(10, 20, 30, 0, 0, 60))
    filtered = filter_frame_xyza(frame)

    # Test that filtering a frame that has translation and azimuth rotation does nothing.
    assert np.allclose(frame, filtered)

    frame = robotmath.xyz_euler_to_frame(10, 20, 30, 0, 30, 40) * robotmath.xyz_euler_to_frame(0, 0, 0, 180, 0, 180)
    frame_xyza = robotmath.xyz_euler_to_frame(10, 20, 30, 0, 0, 40) * robotmath.xyz_euler_to_frame(0, 0, 0, 180, 0, 180)
    filtered = filter_frame_xyza(frame)

    # Test that filtering removes tilt rotation but keeps translation and azimuth.
    assert np.allclose(frame_xyza, filtered)