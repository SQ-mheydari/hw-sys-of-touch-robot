from tntserver.drivers.robots.goldenmov.kinematics.kinematic_xyza_vc_stylus import *
import pytest
import math
import tntserver.robotmath as robotmath


class GoldenMovStub:
    def __init__(self):
        self.axis_setpoints = {"x": 0, "y": 0, "z": 0, "azimuth": 0, "voicecoil1": 0, "tilt_slider": 0}

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
        """
        Calibration data is an arbitrary dictionary of data that kinematics
        can use to calibrate parts of a kinematic chain.
        The data is primarily stored under Robot node.
        """
        return {"tool1_offset": robotmath.xyz_euler_to_frame(x=math.sin(math.radians(15))*100, y=0,
                                                             z=math.cos(math.radians(15))*100, a=0, b=0,
                                                             c=0).tolist()}


@pytest.mark.parametrize(["x", "y", "z", "azimuth", "tilt_slider", "current_azimuth", "final_azimuth"], [
(10, 20, 30, 45, 0, 0, 45), (30, 30, 30, 29, 35, 20, 29), (30, 100, 30, 140, 40, 300, 140),
(34.5, 30, 80.7, 90, 30, -300, -270), (0, 70.2, 60, -3.7, 45, 600, 716.3),
(200, 30, 78, 180, 50, -600, -540), (53.8, 123, 54, 90, 60, -39.6, 90)
  ])
def test_robot_fk_ik(x, y, z, azimuth, tilt_slider, current_azimuth, final_azimuth):
    """
    Test forward and inverse kinematics functions. Please not that voice coils
    are handled separately and, thus, they are not part of the kinematic chain.
    Also the azimuth needs special handling, because joints can only be between
    [-180, 180] and the axis value can be in range [-inf, inf]
    """
    for kinematic_name in ['tool1', 'azimuth', 'voicecoil1']:
        robot = Robot()
        k = Kinematic_xyza_vc_stylus(robot)
        k.driver = GoldenMovStub()
        joints = {"x": x, "y": y, "z": z, "azimuth": azimuth,
                  "voicecoil1": 0, "tilt_slider": tilt_slider}
        # run forward kinematics to change joints to robot position
        fk_pos = k.joints_to_position(joints=joints, kinematic_name=kinematic_name)
        # run inverse kinematics to return robot position to joints
        axis_setpoints = {"azimuth": current_azimuth, 'z': z, 'tilt_slider': tilt_slider}
        k.driver.set_axis_setpoints(axis_setpoints)
        ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name=kinematic_name)[0]

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

    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()

    joints = {"x": 20, "y": 20, "z": 20, "azimuth": 30, "tilt_slider": 40 - k.tilt_slider_zero_position,
              "voicecoil1": 2.0}

    def calc_fk_pos():

        fk_pos = k.joints_to_position(joints=joints, kinematic_name="tool1")
        return fk_pos

    ref_frame = [[-8.56337404e-01,  5.00000000e-01, - 1.29175273e-01,  2.00000000e+01],
                 [4.94406630e-01,  8.66025404e-01,  7.45793787e-02,  2.00000000e+01],
                 [1.49158757e-01,  1.02828020e-16, - 9.88813261e-01, - 1.11651514e+02],
                 [0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]]

    fk_pos = calc_fk_pos()
    assert np.allclose(ref_frame, fk_pos.frame)


def test_robot_ik_0deg():
    """
    Test robot inverse kinematics with precalculated joints and frames, azimuth 0 degrees, tilt 0 degrees
    """
    test_frame = np.matrix([[-1, 0, 0, 20],
                            [0, 1, 0, 20],
                            [0, 0, -1, -120],
                            [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()
    current_azimuth = 0

    # Because of the mechanical mounting offset, at 0 degrees stylus tilt the SR-mechanism tilt angle is already 15 deg.
    tilt_slider_total = np.cos(np.pi/2 - np.radians(15)) * 2 * k.sr_link_length

    # Tilt slider joint position.
    tilt_slider = tilt_slider_total - k.tilt_slider_zero_position

    # Resulting z-coordinate value is then
    z_stylus = np.sqrt(4 * k.sr_link_length ** 2 - tilt_slider_total ** 2)

    fk_position = k.create_robot_position(frame=test_frame)
    joints = {"x": 20, "y": 20, "z": 120 - z_stylus, "azimuth": 0, "tilt_slider": tilt_slider}

    axis_setpoints = {"azimuth": current_azimuth, "voicecoil1": 0}
    k.driver.set_axis_setpoints(axis_setpoints)
    ik_joints = k.positions_to_joints(positions=[fk_position], kinematic_name="tool1")[0]

    for key, _ in joints.items():
        assert np.isclose(joints[key], ik_joints[key])


def test_robot_ik_90deg():
    """
    Test robot inverse kinematics with precalculated joints and frames, azimuth 90 degrees, tilt 0 degrees
    """
    test_frame = np.matrix([[0, 1, 0, 20],
                            [-1, 0, 0, 20],
                            [0, 0, -1, -120],
                            [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()
    current_azimuth = 0

    # Because of the mechanical mounting offset, at 0 degrees stylus tilt the SR-mechanism tilt angle is already 15 deg.
    tilt_slider = np.cos(np.pi/2 - np.radians(15)) * 2 * k.sr_link_length

    # Resulting z-coordinate value is then
    z_stylus = np.sqrt(4 * k.sr_link_length ** 2 - tilt_slider ** 2)

    fk_position = k.create_robot_position(frame=test_frame)
    joints = {"x": 20, "y": 20, "z": 120 - z_stylus, "azimuth": 90}

    axis_setpoints = {"azimuth": current_azimuth, "voicecoil1": 0}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_position], kinematic_name="tool1")[0]

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
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()
    joints = {"x": 0, "y": 0, "z": 0, "azimuth": 0, "tilt_slider": 25,
              "voicecoil1": voicecoil1_new}
    fk_pos = k.joints_to_position(joints=joints, kinematic_name="tool1")

    assert np.isclose(fk_pos.voicecoil1, 0)


def test_voicecoils_camera_fk():
    """
    Test voicecoil value handling in camera_fk
    """
    # Having different values for all of these makes it possible
    # to see if the correct value is used in function
    voicecoil1_new = 5

    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()

    joints = {"x": 0, "y": 0, "z": 0, "azimuth": 0,
              "voicecoil1": voicecoil1_new}
    fk_pos = k.joints_to_position(joints=joints, kinematic_name="camera")

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
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_pos_frame, voicecoil1=fk_voicecoil1)

    axis_setpoints = {"azimuth": 0}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="tool1")[0]

    assert np.isclose(fk_voicecoil1, ik_joints["voicecoil1"])


def test_voicecoil_ik():
    """
    Test that VC is moved and z is stationary when using "voicecoil1" kinematics.
    """
    fk_pos_frame = np.matrix([[-1, 0, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, -1, -120],
                              [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_pos_frame)

    # Because of the mechanical mounting offset, at 0 degrees stylus tilt the SR-mechanism tilt angle is already 15 deg.
    tilt_slider = np.cos(np.pi / 2 - np.radians(15)) * 2 * k.sr_link_length

    # Resulting z-coordinate value is then
    z_stylus = np.sqrt(4 * k.sr_link_length ** 2 - tilt_slider ** 2)

    axis_setpoints = {"azimuth": 0, "voicecoil1": 0, "z": 100 - z_stylus}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="voicecoil1")[0]

    assert np.isclose(20, ik_joints["voicecoil1"])
    assert np.isclose(100 - z_stylus, ik_joints["z"])


def test_tool1_ik():
    """
    Test that z is moved and VC is stationary when using "tool1" kinematics.
    """
    fk_pos_frame = np.matrix([[-1, 0, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, -1, -120],
                              [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_pos_frame)

    # Because of the mechanical mounting offset, at 0 degrees stylus tilt the SR-mechanism tilt angle is already 15 deg.
    tilt_slider = np.cos(np.pi/2 - np.radians(15)) * 2 * k.sr_link_length

    # Resulting z-coordinate value is then
    z_stylus = np.sqrt(4 * k.sr_link_length ** 2 - tilt_slider ** 2)

    axis_setpoints = {"azimuth": 0, "voicecoil1": 0, "z": 0}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="tool1")[0]

    assert np.isclose(0, ik_joints["voicecoil1"])
    assert np.isclose(120 - z_stylus, ik_joints["z"])


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
    k = Kinematic_xyza_vc_stylus(robot)
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
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()
    joints = {"x": x, "y": y, "z": z,
              "voicecoil1": 0, "tilt_slider": 0}
    # run forward kinematics to change joints to robot position
    fk_pos = k.joints_to_position(joints=joints, kinematic_name="camera")
    # run inverse kinematics to return robot position to joints
    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="camera")[0]

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
    fk_pos_frame = np.matrix([[-1, 0, 0, 40],
                              [0, 1, 0, 30],
                              [0, 0, -1, -70],
                              [0, 0, 0, 1]])

    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()
    if azimuth is None:
        joints = {"x": 40, "y": 30, "z": 70,
                  "voicecoil1": 0, "tilt_slider": 30}
    else:
        joints = {"x": 40, "y": 30, "z": 70,
                  "voicecoil1": 0, "azimuth": azimuth, "tilt_slider": 30}

    fk_pos = k.joints_to_position(joints=joints, kinematic_name="camera")
    assert np.allclose(fk_pos.frame, fk_pos_frame)


@pytest.mark.parametrize("turn_azimuth", [True, False])
def test_camera_ik(turn_azimuth):
    """
    Testing camera inverse kinematics alone and also checking that givin/changing
    azimuth value does not affect
    """
    # The results should be the same for all the cases
    joints = {"x": 40, "y": 30, "z": 70,
              "voicecoil1": 0, "tilt_slider": 30}

    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()
    if turn_azimuth:
        fk_pos_frame = np.matrix([[0, -1, 0, 40],
                                  [1, 0, 0, 30],
                                  [0, 0, -1, -70],
                                  [0, 0, 0, 1]])
    else:
        fk_pos_frame = np.matrix([[-1, 0, 0, 40],
                                  [0, 1, 0, 30],
                                  [0, 0, -1, -70],
                                  [0, 0, 0, 1]])

    fk_pos = k.create_robot_position(frame=fk_pos_frame, voicecoil1=0, tilt_slider=30)
    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="camera")[0]

    for key, _ in ik_joints.items():
        assert np.isclose(ik_joints[key], joints[key])


def test_stylus_ik():
    fk_pos_frame = np.matrix([[-1, 0, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, -1, -0],
                              [0, 0, 0, 1]])
    tilt_angle = 35
    tilt_frame = robotmath.xyz_euler_to_frame(0, 0, 0, 0, tilt_angle, 0)

    fk_target_frame = fk_pos_frame * tilt_frame

    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_target_frame, voicecoil1=0)

    axis_setpoints = {"azimuth": 0, "voicecoil1": 0}
    k.driver.set_axis_setpoints(axis_setpoints)

    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="tool1")[0]

    fk_result = k.joints_to_position(joints=ik_joints, kinematic_name="tool1")

    assert np.allclose(fk_target_frame[0:3, 0:3], fk_result.frame[0:3, 0:3])


def test_arc_r():
    """
    Test arc_r with given separation value
    """
    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    assert np.isclose(k.arc_r(), 50.0)


def test_filter():
    robot = Robot()
    k = Kinematic_xyza_vc_stylus(robot)
    k.driver = GoldenMovStub()

    tool_frame = robotmath.xyz_to_frame(0.5, -0.3, 100)
    tool_inv = tool_frame.I
    axis_setpoints = {"azimuth": 0, "voicecoil1": 0}

    # Create impossible target position with rotation around X-axis
    frame = robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(10, 20, 30, 20, 0, 0))
    fk_pos = k.create_robot_position(frame=frame, voicecoil1=0)

    ik_joints = k._robot_ik(fk_pos, axis_setpoints, kinematic_name="tool1")
    fk_result = k._robot_fk(ik_joints, kinematic_name="tool1", axis_setpoints=axis_setpoints)

    # Make sure robot fails to reach target position
    assert not np.allclose(frame[0:3, 3], fk_result.frame[0:3, 3])

    # Filter target position and try again
    filtered = k.filter_position(fk_pos, axis_setpoints, kinematic_name="tool1", tool_inv=tool_inv)

    ik_joints = k._robot_ik(filtered, axis_setpoints, kinematic_name="tool1")
    fk_result = k._robot_fk(ik_joints, kinematic_name="tool1", axis_setpoints=axis_setpoints)

    # Make sure position is now reached
    assert np.allclose(frame[0:3, 3], fk_result.frame[0:3, 3])

    # Test that filtering does not affect reachable positions
    frame = robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(10, 20, 30, 0, 35, 60))
    fk_pos = k.create_robot_position(frame=frame, voicecoil1=0)

    fk_pos = k.filter_position(fk_pos, axis_setpoints, kinematic_name="tool1", tool_inv=tool_inv)

    ik_joints = k._robot_ik(fk_pos, axis_setpoints, kinematic_name="tool1")
    fk_result = k._robot_fk(ik_joints, kinematic_name="tool1", axis_setpoints=axis_setpoints)

    # Make sure position and orientation are unaltered
    assert np.allclose(frame[0:3, 3], fk_result.frame[0:3, 3])  # position
    assert np.allclose(frame[0:3, 0:3], fk_result.frame[0:3, 0:3])  # orientation

