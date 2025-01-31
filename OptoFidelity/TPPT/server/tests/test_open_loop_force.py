from tests.test_opto_std_force import RobotStub
from tests.test_synchro_gestures import create_synchro_environment
import tntserver.drivers.robots.sm_regs as SMRegs
from tntserver.drivers.robots.goldenmov.open_loop_force import OpenLoopForce, VoicecoilForce
import pytest


def init_driver(parameters):
    robot = RobotStub()

    driver = OpenLoopForce(robot, parameters)

    return driver


def test_init_driver():
    """
    Test creating driver instance.
    """
    assert init_driver({}) is not None


def test_default_parameters():
    """
    Test initializing driver with default parameters.
    """
    driver = init_driver({})

    # These currents match Synchro tool voicecoils and should be the defaults for compatibility.
    assert driver.min_current == 100
    assert driver.max_current == 1360
    assert driver.current_step == 100

    assert driver.press_distance == 2.5
    assert driver.press_depth == -1
    assert driver.drag_distance == 2.5
    assert driver.drag_stroke == 3.5
    assert driver.drag_clearance == driver.drag_distance


def test_passed_parameters():
    """
    Test initializing driver with given parameters.
    """
    parameters = {
        "min_current": 200,
        "max_current": 500,
        "current_step": 50,

        "press_distance": 1.2,
        "press_depth": -0.5,
        "drag_distance": 3.1,
        "drag_stroke": 2.2,
        "drag_clearance": 1.1
    }

    driver = init_driver(parameters)

    # Driver attribute names match parameter keys.
    for key, value in parameters.items():
        assert getattr(driver, key) == value


def test_force_calibration_table():
    """
    Test setting calibration table and setting force limit.
    """
    driver = init_driver({})

    assert not driver.force_usage_allowed("voicecoil1")

    driver.set_force_calibration_table({"voicecoil1": {"current": [300.0, 800.0], "force": [100.0, 500.0]}})

    assert driver.force_usage_allowed("voicecoil1")

    driver.set_force_limit("voicecoil1", 100.0)

    assert driver.read_torque_limit("voicecoil1") == 300.0

    driver.set_force_limit("voicecoil1", 500.0)

    assert driver.read_torque_limit("voicecoil1") == 800.0


def test_tap_with_force():
    """
    Test tapping with force using different axes.
    """
    driver = init_driver({})

    driver.set_force_calibration_table({"voicecoil1": {"current": [300, 800], "force": [100, 500]}})

    driver.tap_with_force(100, 0.1, 2.0, "voicecoil1")

    # No calibration for voicecoil2.
    with pytest.raises(Exception):
        driver.tap_with_force(100, 0.1, 2.0, "voicecoil2")

    # No calibration for voicecoil2.
    with pytest.raises(Exception):
        driver.tap_with_force(100, 0.1, 2.0, "both")

    # Unrecognized axis.
    with pytest.raises(Exception):
        driver.tap_with_force(100, 0.1, 2.0, "foo")

    # Set calibration for voicecoil2 after which we can use "voicecoil2" and "both".
    driver.set_force_calibration_table({"voicecoil2": {"current": [300.0, 800.0], "force": [100.0, 500.0]}})

    driver.tap_with_force(100, 0.1, 2.0, "voicecoil2")

    driver.tap_with_force(100, 0.1, 2.0, "both")


def test_tap_with_current():
    """
    Test tapping with given current value.
    """
    driver = init_driver({})

    driver.set_torque_limit("voicecoil1", 1200)

    driver.tap_with_current(300, 0.1, 2.0, "voicecoil1")

    # Make sure torque limit is restored.
    assert driver.read_torque_limit("voicecoil1") == 1200


def test_press():
    """
    Test that press gesture can be executed without errors.
    No validation is done.
    """
    robot, gestures = create_synchro_environment()

    robot.force_driver.press(context=gestures, x=0, y=0, force=400, z=10, tilt=0, azimuth=45, duration=0.1,
                             tool_name="tool1")

    robot.force_driver.press(context=gestures, x=0, y=0, force=400, z=10, tilt=0, azimuth=45, duration=0.1,
                             tool_name="tool2")

    robot.force_driver.press(context=gestures, x=0, y=0, force=400, z=10, tilt=0, azimuth=45, duration=0.1,
                             tool_name="both")


def test_drag_force():
    """
    Test that drag force gesture can be executed without errors.
    No validation is done.
    """
    robot, gestures = create_synchro_environment()

    robot.force_driver.drag_force(context=gestures, x1=0, y1=0, x2=50, y2=50, force = 300, z=10,
                                  tilt1=0, tilt2=0, azimuth1=0, azimuth2=90, tool_name="tool1")

    robot.force_driver.drag_force(context=gestures, x1=0, y1=0, x2=50, y2=50, force=300, z=10,
                                  tilt1=0, tilt2=0, azimuth1=0, azimuth2=90, tool_name="tool2")

    robot.force_driver.drag_force(context=gestures, x1=0, y1=0, x2=50, y2=50, force=300, z=10,
                                  tilt1=0, tilt2=0, azimuth1=0, azimuth2=90, tool_name="both")


def test_voicecoil_force():
    """
    Test context manager class VoicecoilForce.
    """
    driver = init_driver({})

    driver.set_force_calibration_table({"voicecoil1": {"current": [300.0, 800.0], "force": [100.0, 500.0]}})

    driver.set_torque_limit("voicecoil1", 1200.0)

    with VoicecoilForce(driver, {"voicecoil1": 100.0}):
        assert driver.read_torque_limit("voicecoil1") == 300.0

    # Check that torque was restored.
    assert driver.read_torque_limit("voicecoil1") == 1200.0