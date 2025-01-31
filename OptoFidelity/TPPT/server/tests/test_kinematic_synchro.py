from tntserver.drivers.robots.goldenmov.kinematics.kinematic_synchro import *


class GoldenMovStub:
    def __init__(self):
        self.axis_setpoints = { "azimuth": 0, "voicecoil1": 0, "voicecoil2": 0, "x": 0, "y": 0, "z": 0, "separation": 0}
        self.separation = 50

    def get_scaled_axis_setpoint(self, axis_alias):
        return self.axis_setpoints[axis_alias]

    def get_axis_parameter(self, axis_alias, parameter):
        # Simulate all axes being in position model
        if parameter == sm_regs.SMP_CONTROL_MODE:
            return sm_regs.CM_POSITION

        # Default stub value.
        return 0

    def set_axis_setpoints(self, setpoints: dict):
        self.axis_setpoints.update(setpoints)

    def position(self, tool, kinematic_name):
        return RobotPosition(frame=np.eye(4), separation=self.separation)


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
        return {"tool2_offset": [[1.0, 0.0, 0.0, 6.15097277],
                                 [0.0, 1.0, 0.0, -0.02862004],
                                 [0.0, 0.0, 1.0, 0.0],
                                 [0.0, 0.0, 0.0, 1.0]],
                "tool1_offset": [[1.0, 0.0, 0.0, -5.2290681],
                                 [0.0, 1.0, 0.0, -0.07199028],
                                 [0.0, 0.0, 1.0, 0.0],
                                 [0.0, 0.0, 0.0, 1.0]]
                }


toolframe = np.matrix([[1, 0, 0, 10],
                       [0, 1, 0, 20],
                       [0, 0, 1, 30],
                       [0, 0, 0, 1]])


def azimuth_rotation_frame(azimuth):
    return robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, -azimuth)


def test_determine_robot_azimuth():
    """
    Test determine_robot_azimuth() function.
    """

    def test(target_azimuth, current_azimuth):
        target = azimuth_rotation_frame(target_azimuth)
        result_azimuth = determine_robot_azimuth(target, current_azimuth)
        assert np.isclose(target_azimuth, result_azimuth)

    # Test consecutive 90 deg rotations CW and CCW multiple rounds.
    for i in range(40):
        test(90.0 * (i + 1), 90.0 * i)
        test(-90.0 * (i + 1), -90.0 * i)

    # Test crossing 180 deg pole Cw and CCW.
    test(300.0, 170.0)
    test(170.0, 300.0)
    test(-300.0, -170.0)
    test(-170.0, -300.0)


def test_robot_fk_ik():
    """
    Test forward and inverse kinematics functions. Please not that voice coils
    are handled separately and, thus, they are not part of the kinematic chain.
    Also the azimuth needs special handling, because joints can only be between
    [-180, 180] and the axis value can be in range [-inf, inf]
    """
    for kinematic_name in ["synchro", "tool1", "tool2", "mid"]:
        def test(x, y, z, separation, azimuth, current_azimuth, final_azimuth):
            robot = Robot()
            k = Kinematic_synchro(robot)
            k.driver = GoldenMovStub()
            joints = {"x": x, "y": y, "z": z, "separation": separation, "azimuth": azimuth,
                      "voicecoil1": 0, "voicecoil2": 0}
            # run forward kinematics to change joints to robot position
            fk_pos = k.joints_to_position(joints=joints, kinematic_name=kinematic_name, tool=toolframe)
            # run inverse kinematics to return robot position to joints
            k.driver.set_axis_setpoints({"azimuth": current_azimuth})
            ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name=kinematic_name,
                                              tool_inv=toolframe.I)[0]

            # compare if joints are returned as they were
            for key, value in joints.items():
                # azimuth value is a special case as described in docstring
                if key == "azimuth":
                    assert np.isclose(ik_joints[key], final_azimuth)
                else:
                    assert np.isclose(joints[key], ik_joints[key])

        # manually randomized test input
        test(10, 20, 30, 100, 45, 0, 45)
        test(30, 30, 30, 40, 29, 20, 29)
        test(30, 100, 30, 57, 140, 300, 140)
        test(34.5, 30, 80.7, -130, 90, -300, -270)
        test(0, 70.2, 60, 12, -3.7, 600, 716.3)
        test(200, 30, 78, 3.5, 180, -600, -540)
        test(53.8, 123, 54, 7.56, 90, -39.6, 90)


def test_robot_fk():
    """
    Test robot forward kinematics with precalculated joints and frames
    """
    tool1_frame = np.matrix([[-8.66025404e-01, 5.00000000e-01, 6.12323400e-17, 1.11053720e+01],
                             [5.00000000e-01, 8.66025404e-01, 1.06057524e-16, 2.50521886e+01],
                             [0.00000000e+00, 1.22464680e-16, -1.00000000e+00, -2.00000000e+01],
                             [0.00000000e+00, 0.00000000e+00, 0.00000000e+00, 1.00000000e+00]])
    tool1_separation = 21.38004087

    tool2_frame = np.matrix([[-8.66025404e-01, 5.00000000e-01, 6.12323400e-17, 2.96427157e+01],
                             [5.00000000e-01, 8.66025404e-01, 1.06057524e-16, 1.43997279e+01],
                             [0.00000000e+00, 1.22464680e-16, -1.00000000e+00, -2.00000000e+01],
                             [0.00000000e+00, 0.00000000e+00, 0.00000000e+00, 1.00000000e+00]])
    tool2_separation = 21.38004087

    mid_frame = np.matrix([[-8.66025404e-01, 5.00000000e-01, 6.12323400e-17, 2.03740439e+01],
                           [5.00000000e-01, 8.66025404e-01, 1.06057524e-16, 1.97259583e+01],
                           [0.00000000e+00, 1.22464680e-16, -1.00000000e+00, -2.00000000e+01],
                           [0.00000000e+00, 0.00000000e+00, 0.00000000e+00, 1.00000000e+00]])
    mid_separation = 21.38004087

    synchro_frame = np.matrix([[-8.66025404e-01, 5.00000000e-01, 6.12323400e-17, 2.00000000e+01],
                               [5.00000000e-01, 8.66025404e-01, 1.06057524e-16, 2.00000000e+01],
                               [0.00000000e+00, 1.22464680e-16, -1.00000000e+00, -2.00000000e+01],
                               [0.00000000e+00, 0.00000000e+00, 0.00000000e+00, 1.00000000e+00]])
    synchro_separation = 21.38004087

    joints = {"x": 20, "y": 20, "z": 20, "separation": 10, "azimuth": 30,
              "voicecoil1": 0, "voicecoil2": 0}

    def calc_fk_pos(kinematic_name):
        robot = Robot()
        k = Kinematic_synchro(robot)
        k.driver = GoldenMovStub()
        fk_pos = k._robot_fk(joints, kinematic_name)
        return fk_pos

    def compare(kinematic_name):
        fk_pos = calc_fk_pos(kinematic_name)
        if kinematic_name == "tool1":
            assert np.allclose(tool1_frame, fk_pos.frame)
            assert np.isclose(tool1_separation, fk_pos.separation)
        elif kinematic_name == "tool2":
            assert np.allclose(tool2_frame, fk_pos.frame)
            assert np.isclose(tool2_separation, fk_pos.separation)
        elif kinematic_name == "mid":
            assert np.allclose(mid_frame, fk_pos.frame)
            assert np.isclose(mid_separation, fk_pos.separation)
        elif kinematic_name == "synchro":
            assert np.allclose(synchro_frame, fk_pos.frame)
            assert np.isclose(synchro_separation, fk_pos.separation)
        else:  # unknown kinematic name
            assert False

    compare("tool1")
    compare("tool2")
    compare("mid")
    compare("synchro")


def test_robot_ik_0deg():
    """
    Test robot inverse kinematics with precalculated joints and frames, azimuth 0 degrees
    """
    test_frame = np.matrix([[-1, 0, 0, 20],
                            [0, 1, 0, 20],
                            [0, 0, -1, -20],
                            [0, 0, 0, 1]])

    def test(kinematic_name):
        robot = Robot()
        k = Kinematic_synchro(robot)
        k.driver = GoldenMovStub()
        current_azimuth = 0
        separation = 10
        if kinematic_name == "tool1":
            fk_position = k.create_robot_position(frame=test_frame, separation=separation)
            joints = {"x": 24.539047665, "y": 20.07199028, "z": 20.0, "separation": -1.38004087, "azimuth": 0}
        elif kinematic_name == "tool2":
            fk_position = k.create_robot_position(frame=test_frame, separation=separation)
            joints = {"x": 14.539047665, "y": 20.02862004, "z": 20.0, "separation": -1.38004087, "azimuth": 0}
        elif kinematic_name == "mid":
            fk_position = k.create_robot_position(frame=test_frame, separation=separation)
            joints = {"x": 19.539047665, "y": 20.05030516, "z": 20.0, "separation": -1.38004087, "azimuth": 0}
        elif kinematic_name == "synchro":
            fk_position = k.create_robot_position(frame=test_frame, separation=separation)
            joints = {"x": 20.0, "y": 20.0, "z": 20.0, "separation": -1.38004087, "azimuth": 0}
        else:  # unknown kinematic name
            assert False

        k.driver.set_axis_setpoints({"azimuth": current_azimuth})
        ik_joints = k.positions_to_joints(positions=[fk_position], kinematic_name=kinematic_name)[0]

        for key, _ in joints.items():
            assert np.isclose(joints[key], ik_joints[key])

    test("tool1")
    test("tool2")
    test("mid")
    test("synchro")


def test_robot_ik_90deg():
    """
    Test robot inverse kinematics with precalculated joints and frames, azimuth 90 degrees
    """
    test_frame = np.matrix([[0, 1, 0, 20],
                            [-1, 0, 0, 20],
                            [0, 0, -1, -20],
                            [0, 0, 0, 1]])

    def test(kinematic_name):
        robot = Robot()
        k = Kinematic_synchro(robot)
        k.driver = GoldenMovStub()
        current_azimuth = 0
        separation = 10
        if kinematic_name == "tool1":
            fk_position = k.create_robot_position(frame=test_frame, separation=separation)
            joints = {"x": 20.07199028, "y": 24.539047665, "z": 20.0, "separation": -1.38004087, "azimuth": 90}
        elif kinematic_name == "tool2":
            fk_position = k.create_robot_position(frame=test_frame, separation=separation)
            joints = {"x": 20.02862004, "y": 14.539047665, "z": 20.0, "separation": -1.38004087, "azimuth": 90}
        elif kinematic_name == "mid":
            fk_position = k.create_robot_position(frame=test_frame, separation=separation)
            joints = {"x": 20.05030516, "y": 19.539047665, "z": 20.0, "separation": -1.38004087, "azimuth": 90}
        elif kinematic_name == "synchro":
            fk_position = k.create_robot_position(frame=test_frame, separation=separation)
            joints = {"x": 20.0, "y": 20.0, "z": 20.0, "separation": -1.38004087, "azimuth": 90}
        else:  # unknown kinematic name
            assert False

        k.driver.set_axis_setpoints({"azimuth": current_azimuth})
        ik_joints = k.positions_to_joints(positions=[fk_position], kinematic_name=kinematic_name)[0]

        for key, _ in joints.items():
            assert np.isclose(joints[key], ik_joints[key])

    test("tool1")
    test("tool2")
    test("mid")
    test("synchro")


def test_voicecoils_robot_fk():
    """
    Test voicecoil value handling in robot_fk
    """
    # Having different values for all of these makes it possible
    # to see if the correct value is used in function
    voicecoil1_new = 5
    voicecoil2_new = 7

    robot = Robot()
    k = Kinematic_synchro(robot)
    k.driver = GoldenMovStub()
    joints = {"x": 0, "y": 0, "z": 0, "separation": 0, "azimuth": 0,
              "voicecoil1": voicecoil1_new, "voicecoil2": voicecoil2_new}
    fk_pos = k.joints_to_position(joints=joints, kinematic_name="synchro", tool=toolframe)

    assert np.isclose(fk_pos.voicecoil1, 0)
    assert np.isclose(fk_pos.voicecoil2, 0)


def test_voicecoils_camera_fk():
    """
    Test voicecoil value handling in camera_fk
    """
    # Having different values for all of these makes it possible
    # to see if the correct value is used in function
    voicecoil1_new = 5
    voicecoil2_new = 7

    robot = Robot()
    k = Kinematic_synchro(robot)
    k.driver = GoldenMovStub()

    joints = {"x": 0, "y": 0, "z": 0, "separation": 0, "azimuth": 0,
              "voicecoil1": voicecoil1_new, "voicecoil2": voicecoil2_new}
    fk_pos = k.joints_to_position(joints=joints, kinematic_name="camera", tool=toolframe)

    assert np.isclose(fk_pos.voicecoil1, 0)
    assert np.isclose(fk_pos.voicecoil2, 0)


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
    fk_voicecoil2 = 8

    robot = Robot()
    k = Kinematic_synchro(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_pos_frame, voicecoil1=fk_voicecoil1, voicecoil2=fk_voicecoil2)
    k.driver.set_axis_setpoints({"azimuth": 0})
    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="synchro", tool_inv=toolframe.I)[0]

    assert np.isclose(fk_voicecoil1, ik_joints["voicecoil1"])
    assert np.isclose(fk_voicecoil2, ik_joints["voicecoil2"])


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
    fk_voicecoil2 = 8

    robot = Robot()
    k = Kinematic_synchro(robot)
    k.driver = GoldenMovStub()

    fk_pos = k.create_robot_position(frame=fk_pos_frame, voicecoil1=fk_voicecoil1, voicecoil2=fk_voicecoil2)

    ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="camera", tool_inv=toolframe.I)[0]

    assert np.isclose(fk_voicecoil1, ik_joints["voicecoil1"])
    assert np.isclose(fk_voicecoil2, ik_joints["voicecoil2"])


def test_home_separation():
    """
    Test home_separation property. It is based on stub robot calibration_data
    """
    robot = Robot()
    k = Kinematic_synchro(robot)
    separation = k.home_separation
    assert np.isclose(separation, 11.38004087)


def test_camera_fk_ik():
    """
    Test camera forward and inverse kinematics
    """

    def test(x, y, z, separation):
        robot = Robot()
        k = Kinematic_synchro(robot)
        k.driver = GoldenMovStub()
        joints = {"x": x, "y": y, "z": z, "separation": separation,
                  "voicecoil1": 0, "voicecoil2": 0}
        # run forward kinematics to change joints to robot position
        fk_pos = k.joints_to_position(joints=joints, kinematic_name="camera", tool=toolframe)
        # run inverse kinematics to return robot position to joints
        ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="camera", tool_inv=toolframe.I)[0]

        # compare if joints are returned as they were
        for key, value in joints.items():
            assert np.isclose(value, ik_joints[key])

    # manually randomized test input
    test(10, 20, 30, 100)
    test(30, 30, 30, 40)
    test(30, 100, 30, 57)
    test(34.5, 30, 80.7, -130)
    test(0, 70.2, 60, 12)
    test(200, 30, 78, 3.5)
    test(53.8, 123, 54, 7.56)


def test_camera_fk():
    """
    Testing camera forward kinematics alone and also checking that givin/changing
    azimuth value does not affect
    """
    # The results should be the same for all the cases
    fk_pos_frame = np.matrix([[-1, 0, 0, 30],
                              [0, 1, 0, 50],
                              [0, 0, -1, -100],
                              [0, 0, 0, 1]])
    separation = 21.38004087

    def test(azimuth):
        robot = Robot()
        k = Kinematic_synchro(robot)
        k.driver = GoldenMovStub()
        if azimuth is None:
            joints = {"x": 40, "y": 30, "z": 70, "separation": 10,
                      "voicecoil1": 0, "voicecoil2": 0}
        else:
            joints = {"x": 40, "y": 30, "z": 70, "separation": 10,
                      "voicecoil1": 0, "voicecoil2": 0, "azimuth": azimuth}

        fk_pos = k.joints_to_position(joints=joints, kinematic_name="camera", tool=toolframe)
        assert np.allclose(fk_pos.frame, fk_pos_frame)
        assert np.isclose(fk_pos.separation, separation)

    test(None)
    test(0)
    test(45)


def test_camera_ik():
    """
    Testing camera inverse kinematics alone and also checking that givin/changing
    azimuth value does not affect
    """
    # The results should be the same for all the cases
    joints = {"x": 50, "y": 10, "z": 40, "separation": 10,
              "voicecoil1": 0, "voicecoil2": 0}

    separation = 21.38004087

    def test(turn_azimuth):
        robot = Robot()
        k = Kinematic_synchro(robot)
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

        fk_pos = k.create_robot_position(frame=fk_pos_frame, separation=separation, voicecoil1=0, voicecoil2=0)
        ik_joints = k.positions_to_joints(positions=[fk_pos], kinematic_name="camera", tool_inv=toolframe.I)[0]

        for key, _ in ik_joints.items():
            assert np.isclose(ik_joints[key], joints[key])

    test(turn_azimuth=False)
    test(turn_azimuth=True)


def test_compute_tool_transform():
    """
    Test compute_tool_transform function. This needs to be tested separately
    because the ik-fk test seems to "annihilate" possible errors in this function
    """
    robot = Robot()
    k = Kinematic_synchro(robot)
    separation_joint = 10

    tool1_m = np.matrix([[1, 0, 0, -10.2290681],
                         [0, 1, 0, -0.07199028],
                         [0, 0, 1, 0],
                         [0, 0, 0, 1]])

    tool2_m = np.matrix([[1, 0, 0, 11.15097277],
                         [0, 1, 0, -0.02862004],
                         [0, 0, 1, 0],
                         [0, 0, 0, 1]])

    mid_m = np.matrix([[1, 0, 0, 0.46095233],
                       [0, 1, 0, -0.05030516],
                       [0, 0, 1, 0],
                       [0, 0, 0, 1]])

    synchro_m = np.matrix([[1, 0, 0, 0],
                           [0, 1, 0, 0],
                           [0, 0, 1, 0],
                           [0, 0, 0, 1]])

    assert np.allclose(k.compute_tool_transform("tool1", separation_joint), tool1_m)
    assert np.allclose(k.compute_tool_transform("tool2", separation_joint), tool2_m)
    assert np.allclose(k.compute_tool_transform("mid", separation_joint), mid_m)
    assert np.allclose(k.compute_tool_transform("synchro", separation_joint), synchro_m)


def test_arc_r_not_none():
    """
    Test arc_r with given separation value
    """
    robot = Robot()
    k = Kinematic_synchro(robot)
    k.driver = GoldenMovStub()
    k.driver.separation = 10.0
    assert np.isclose(k.arc_r(toolframe=np.eye(4), kinematic_name="tool1"), 5.0)


def test_arc_r_none():
    """
    Test arc_r so that separation is None
    :return:
    """
    robot = Robot()
    k = Kinematic_synchro(robot)
    k.driver = GoldenMovStub()
    k.driver.separation = None
    assert np.isclose(k.arc_r(toolframe=np.eye(4), kinematic_name="tool1"), 50)


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