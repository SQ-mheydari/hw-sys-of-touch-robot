"""
Unit tests for two-finger-dt robot driver.
"""
from tntserver.drivers.robots.two_finger_dt import *
import numpy as np

AXIAL_KINEMATIC = "tool1"
SEPARATED_KINEMATIC = "tool2"
CAMERA_KINEMATIC = "camera"

def create_default_driver():
    """
    Create 2-finger-dt driver that is used by unit test cases.
    The driver is created as simulator with the intention to test the basic kinematics
    and check that methods can be executed without errors.
    """
    axis_limits = {
        "x_min": 0,
        "x_max": 400,
        "y_min": 0,
        "y_max": 500,
        "z_min": 0,
        "z_max": 100
    }
    thresholds = {
        "angle": 0.01,
        "position": 0.01,
        "separation": 0.1
    }
    separation_offset = 10.0
    safe_distance = 200.0

    driver = TwoFingerDT(
        ip="10.10.12.4",
        port=6842,
        axis_limits=axis_limits,
        tf_rotate_speed=30,
        tf_move_speed=30,
        thresholds=thresholds,
        simulator=True,
        separation_offset=separation_offset,
        safe_distance=safe_distance
    )

    return driver

def test_driver_init():
    """
    Test that driver initialization is successful and robot is at home after init.
    """
    driver = create_default_driver()

    # Make sure robot is at home.
    # 2-finger-dt homes x and y axes to maximum joint values and z-axis to minimum.
    assert np.allclose(driver.get_position(), [driver.axes["x"].max, driver.axes["y"].max, driver.axes["z"].min, driver.home_angle, 0.0])

def head_frame_xyz(x, y, z):
    """
    Create a frame where position is at given x, y, z coordinates and local z point along -z in workspace.
    """
    return robotmath.frame_to_pose(robotmath.xyz_to_frame(x, y, z))

def test_home():
    """
    Test homings sequences and resulting robot positions.
    """
    driver = create_default_driver()

    driver.home_xyz()

    # Make sure robot is at home.
    # 2-finger-dt homes x and y axes to maximum joint values and z-axis to minimum.
    assert np.allclose(driver.get_position(),
                       [driver.axes["x"].max, driver.axes["y"].max, driver.axes["z"].min, driver.home_angle, 0.0])

    position = [-300, -300, -50]
    angle = 45.0
    separation = 50.0

    driver.move(head_frame_xyz(*position), robotmath.identity_frame(), AXIAL_KINEMATIC)
    driver.tf_rotate_abs(angle)
    driver.tf_move_finger_abs(separation)

    # Home xyz
    driver.home_xyz()
    assert np.allclose(driver.get_position(),
                       [driver.axes["x"].max, driver.axes["y"].max, driver.axes["z"].min, angle, separation])

    # Home rotation. Note that xyz are not tested as they can move when rotation is homed.
    driver.tf_rotate_home()
    assert np.allclose(driver.get_position()[3:5], [driver.home_angle, separation])

    # Home separation
    driver.tf_finger_home()
    assert np.allclose(driver.get_position()[3:5], [driver.home_angle, 0.0])

def test_speed_acceleration():
    """
    Test setting and getting robot speed and acceleration.
    """
    driver = create_default_driver()

    speed = 200.0
    driver.speed = speed
    assert abs(driver.speed - speed) < 1e-6

    # Acceleration getter is not implemented. Only set that setter succeeds.
    acceleration = 800.0
    driver.acceleration = acceleration

def frame_translations_equal(f1, f2):
    """
    Check if the two given frames have the same translation part.
    """
    return np.allclose(np.array(robotmath.frame_to_xyz(f1)), np.array(robotmath.frame_to_xyz(f2)))

def test_move():
    """
    Test move command by moving robot with the two different finger kinematics.
    """
    driver = create_default_driver()

    x, y, z = -200, -200, -50

    target_frame = head_frame_xyz(x, y, z)

    # Move to position using tool1.
    driver.move(target_frame, tool=robotmath.identity_frame(), kinematic_name=AXIAL_KINEMATIC)

    # Check tool1 frame.
    result_frame = driver.frame(tool=robotmath.identity_frame(), kinematic_name=AXIAL_KINEMATIC)
    assert np.allclose(target_frame, result_frame)

    # Check tool2 frame. It should be offset to +x direction from tool1 and should have 180 deg azimuth rotation.
    result_frame = driver.frame(tool=robotmath.identity_frame(), kinematic_name=SEPARATED_KINEMATIC)
    separated_target_frame = np.matrix([[1, 0, 0, x + driver.separation_offset],
                                        [0, -1, 0, y],
                                        [0, 0, -1, z],
                                        [0, 0, 0, 1]])
    assert np.allclose(separated_target_frame, result_frame)

    # Move to position using tool2.
    driver.move(target_frame, tool=robotmath.identity_frame(), kinematic_name=SEPARATED_KINEMATIC)

    # Check tool1 position.
    # Notice that in this case the azimuth will have 180 deg rotation because tool2 was driven with identity rotation.
    # Then tool1 will be at the same location as in previous step.
    result_frame = driver.frame(tool=robotmath.identity_frame(), kinematic_name=AXIAL_KINEMATIC)
    axial_target_frame = np.matrix([[1, 0, 0, x + driver.separation_offset],
                                    [0, -1, 0, y],
                                    [0, 0, -1, z],
                                    [0, 0, 0, 1]])
    assert np.allclose(axial_target_frame, result_frame)

    # Check tool2 position.
    result_frame = driver.frame(tool=robotmath.identity_frame(), kinematic_name=SEPARATED_KINEMATIC)
    assert np.allclose(target_frame, result_frame)

def test_move_rotation_separation():
    """
    Test the move command when changing azimuth rotation and separation.
    """
    driver = create_default_driver()

    for separation in [driver.separation_offset, 40, 60]:
        driver.set_finger_separation(separation)

        for azimuth in [0, 90, 180, 270]:
            x, y, z = -200, -200, -50
            target_frame = robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(x, y, z, 0, 0, -azimuth))
            target_camera_frame = robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(x, y, z, 0, 0, 0))

            # Move to position using tool1.
            driver.move(target_frame, tool=robotmath.identity_frame(), kinematic_name=AXIAL_KINEMATIC)

            # Check tool1 position. This should not depend on azimuth rotation.
            result_frame = driver.frame(tool=robotmath.identity_frame(), kinematic_name=AXIAL_KINEMATIC)
            assert np.allclose(target_frame, result_frame)

            # Check tool2 position. This should rotate with azimuth around target position.
            result_frame = driver.frame(tool=robotmath.identity_frame(), kinematic_name=SEPARATED_KINEMATIC)
            offset = robotmath.xyz_to_frame(-separation, 0, 0)  # Negative separation as robot frame local x-axis is along -x in workspace at home.
            assert frame_translations_equal(target_frame * offset, result_frame)

            # Check camera kinematic. It should not rotate but should move with x, y, z and its local z should point along -z_workspace.
            result_frame = driver.frame(tool=robotmath.identity_frame(), kinematic_name=CAMERA_KINEMATIC)
            assert np.allclose(target_camera_frame, result_frame)

def test_tap():
    """
    Test tap gesture.
    """
    driver = create_default_driver()

    target_frame = head_frame_xyz(-200, -200, -50)

    # Just test that tap is executed without errors.
    driver.tap(target_frame, robotmath.identity_frame(), kinematic_name=AXIAL_KINEMATIC, duration=2.0)


def test_swipe():
    """
    Test swipe gesture.
    """
    driver = create_default_driver()

    start = head_frame_xyz(-200, -200, -50)
    end = head_frame_xyz(-100, -200, -50)

    # Just test that swipe is executed without errors.
    driver.swipe(start, end, 10.0, robotmath.identity_frame(), kinematic_name=AXIAL_KINEMATIC)

def test_tool_frame():
    """
    Test moving robot with non-identity tool frame.
    """
    driver = create_default_driver()

    finger_length = 16.0

    # Create tool frame that represents typical finger.
    tool_frame = robotmath.xyz_to_frame(0, 0, finger_length)

    target_frame = head_frame_xyz(-200, -200, -50)

    # Move to position using tool1.
    driver.move(target_frame, tool=tool_frame, kinematic_name="tool1")

    head_frame = driver.frame(tool=robotmath.identity_frame(), kinematic_name="tool1")
    effector_frame = driver.frame(tool=tool_frame, kinematic_name="tool1")

    # Make sure effector z is at target.
    assert abs(effector_frame.A1[11] - target_frame.A1[11]) < 1e-6

    # Make sure head z is finger_length distance over target.
    assert abs((head_frame.A1[11] - finger_length) - target_frame.A1[11]) < 1e-6

def test_api_success():
    """
    Test that 2-finger API functions can be called without errors when providing correct parameters.
    Test functions that may not be tested in other unit tests.
    """
    driver = create_default_driver()

    driver.bounds(tool=robotmath.identity_frame())
    driver.tf_move_finger_rel(10.0)
    driver.tf_move_finger_abs(50.0)
    driver.tf_rotate_rel(45.0)
    driver.tf_rotate_abs(180.0)
    driver.tf_get_position()
    driver.tf_move_speed = 100.0
    driver.tf_rotate_speed = 50.0
    driver.get_finger_separation()

