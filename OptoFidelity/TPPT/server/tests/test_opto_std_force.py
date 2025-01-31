import pytest
from tntserver.drivers.robots.goldenmov.opto_std_force import OptoStdForce
from tntserver.drivers.robots.goldenmov.simulator.comm import SimulatorAxisSpec
import tntserver.drivers.robots.sm_regs as SMRegs
from tntserver.Nodes.TnT.Dut import *
from tntserver.Nodes.Voicecoil.Robot import Robot
from tntserver.Nodes.Mount import Mount, Tool
import tntserver.globals
from tests.test_gestures import ProgramArguments


def create_3axis_voicecoil_environment():
    """
    Create simple environment for running xyz_voicecoil robot simulator with optostandard force.
    """
    root = Node("root")
    Node.root = root

    tool = Tool("tool1")

    mount = Mount("tool1_mount")
    mount.mount_point = "tool1"
    mount.add_child(tool)

    axis_specs = {
        23: {
            "alias": "x",
            "homing_priority": 3,
            "acceleration": 500,
            "velocity": 500,
        },
        1: {
            "alias": "y",
            "homing_priority": "2",
            "acceleration": 500,
            "velocity": 500,
        },
        12:
            {
                "alias": "z",
                "homing_priority": 1,
                "acceleration": 500,
                "velocity": 500,
            },
        11:
            {
                "alias": "voicecoil1",
                "homing_priority": 4,
                "acceleration": 30000,
                "velocity": 50,
                "move_tolerance": 0.005,
                "force_support": True
            }
    }

    force_parameters = {
        "axis_name": "voicecoil1",
        "tare_on_init": False
    }

    robot = Robot("Robot1")
    robot._init(
        driver="golden",
        host="127.0.0.1",
        port=4001,
        model="3axis_voicecoil",
        axis_specs=axis_specs,
        simulator=True,
        speed=200,
        acceleration=400,
        force_driver="opto_std_force",
        force_parameters=force_parameters,
        program_arguments=ProgramArguments()
    )

    robot.force_calibration_table = {"voicecoil1": {"actual_values": [100.0, 800.0], "setpoint_values": [101.0, 801.0]}}

    # There's no reason to simulate duration when testing gesture positions.
    robot.driver._comm.simulate_duration = False

    robot.add_child(mount)
    root.add_child(robot)

    tntserver.globals.robot = robot

    dut = Dut("dut")
    dut.tl = {"x": 100, "y": 100, "z": -40}
    dut.tr = {"x": 150, "y": 100, "z": -40}
    dut.bl = {"x": 100, "y": 150, "z": -40}

    root.add_child(dut)

    gestures = Gestures("Gestures")
    gestures._init()

    dut.add_child(gestures)

    return robot, gestures


class GoldenMock:
    def __init__(self, comm):
        self._comm = comm
        self.force_suppored = True
        self._axis_parameters = {}

    def force_is_supported(self, axis):
        return self.force_suppored

    def set_axis_parameter(self, axis, reg, value):
        if axis not in self._axis_parameters:
            self._axis_parameters[axis] = {}

        self._axis_parameters[axis][reg] = value

    def read_axis_parameter(self, axis, reg):
        if axis not in self._axis_parameters:
            self._axis_parameters[axis] = {}

        if reg not in self._axis_parameters[axis]:
            self._axis_parameters[axis][reg] = 0

        return self._axis_parameters[axis][reg]

    def set_axis_force_mode(self, axis, mode):
        pass


class OptomotionCommStub:
    """
    Stub communication class that allows setting Simplemotion parameters and provides mock optomotion scaling factors.
    """
    def __init__(self):
        # Create some axis specs to read later.
        self.spec = SimulatorAxisSpec(acceleration=10, posToDevice=0.1, posFromDevice=5, velocity=20)

    def get_scaled_axis_setpoint(self, axis):
        return 0

    def set_axis_parameter(self, axis, register, value):
        """
        Sets value to Simplemotion register address.
        :param axis: Axis name (needed for compatibility reasons).
        :param register: Register address.
        :param value: Parameter value to write.
        :return: None.
        """
        setattr(self, str(register), value)

    def get_axis_spec(self, axis):
        """
        Returns axis specifications of drive.
        :param axis: Axis name (needed for compatibility reasons).
        :return: Axis specifications.
        """
        return self.spec

    @staticmethod
    def get_errors():
        return []

    def clear_errors(self):
        self.set_axis_parameter(axis=None, register=SMRegs.SMP_FAULTS, value=0)

    def get_axis_parameter(self, axis, param):
        """
        Returns Simplemotion parameter value, if it has been set.
        :param axis: Axis name (needed for compatibility reasons)
        :param param: Parameter address to read.
        :return: Parameter value if it has been written earlier, otherwise 1.
        """
        if hasattr(self, str(param)):
            return getattr(self, str(param))
        else:
            return 1

    def discover_axis(self, *args):
        pass

    def set_axis_force_mode(self, axis, mode):
        pass


class RobotStub:
    def __init__(self):
        self.driver = GoldenMock(comm=OptomotionCommStub())


        self.robot_velocity = 100
        self.voicecoil_cont_current = 500
        self.voicecoil_peak_current = 500
        self.voicecoil_nominal_cont_current = 500
        self.voicecoil_nominal_peak_current = 500

    def move_joint_position(self, joint_position: dict, speed=None, acceleration=None):
        pass

    def set_current_limits(self, continuous_current, peak_current):
        pass

def init_driver(parameters=None):
    robot = RobotStub()

    if parameters is None:
        parameters = {
            "axis_name": 'test_axis',
            "no_contact_force_threshold": 20,
            "tare_on_init": False
        }

    driver = OptoStdForce(robot, parameters)
    driver.set_force_calibration_table({"voicecoil1": {"actual_values": [100.0, 800.0], "setpoint_values": [101.0, 801.0]}})

    # Set some registers to non-zero values.
    driver.set_axis_parameter(SMRegs.SMP_AXIS_SCALE, 20000)
    driver.set_axis_parameter(SMRegs.SMP_ENCODER_PPR, 1024)
    driver.set_axis_parameter(SMRegs.SMP_ACTUAL_POSITION_FB, 12345)

    # Set force control register to return immediate success for tare and touch probe.
    driver.set_axis_parameter(SMRegs.SMP_FORCE_FUNCTIONS_STATUS, (1 << SMRegs.FFS_TARE_SUCCESS) |
                              (1 << SMRegs.FFS_TOUCH_PROBE_SUCCESS))

    return driver


def test_init_driver():
    """
    Test creating driver instance.
    """
    assert init_driver() is not None


def test_default_parameters():
    """
    Test initializing driver with default parameters.
    """
    driver = init_driver({"tare_on_init": False})

    assert driver._axis == "voicecoil1"
    assert driver._no_contact_force_threshold == 20
    assert driver._voicecoil_speed == 50
    assert driver._voicecoil_acceleration == 30000
    assert driver._force_tare_threshold == 0.5
    assert driver._force_tare_stabilization_time == 2
    assert driver._force_tare_timeout == 10
    assert driver._press_start_height == 1
    assert driver._force_touch_probing_velocity == 1.0
    assert driver._force_touch_probing_acceleration == 100
    assert driver._force_touch_probing_threshold == 10
    assert driver.min_force == 25
    assert driver.max_force == 800
    assert driver.force_calibration_window_size == 100


def test_passed_parameters():
    """
    Test initializing driver with given parameters.
    """
    parameters = {
        "tare_on_init": False,
        "axis_name": "test_axis",
        "no_contact_force_threshold": 1,
        "voicecoil_speed": 2,
        "voicecoil_acceleration": 3,
        "force_tare_threshold": 4,
        "force_tare_stabilization_time": 5,
        "force_tare_timeout": 6,
        "press_start_height": 7,
        "force_touch_probing_velocity": 8,
        "force_touch_probing_acceleration": 9,
        "force_touch_probing_threshold": 10,
        "min_force": 11,
        "max_force": 12,
        "force_calibration_window_size": 13
    }

    driver = init_driver(parameters)

    assert driver._axis == parameters["axis_name"]
    assert driver._no_contact_force_threshold == parameters["no_contact_force_threshold"]
    assert driver._voicecoil_speed == parameters["voicecoil_speed"]
    assert driver._voicecoil_acceleration == parameters["voicecoil_acceleration"]
    assert driver._force_tare_threshold == parameters["force_tare_threshold"]
    assert driver._force_tare_stabilization_time == parameters["force_tare_stabilization_time"]
    assert driver._force_tare_timeout == parameters["force_tare_timeout"]
    assert driver._press_start_height == parameters["press_start_height"]
    assert driver._force_touch_probing_velocity == parameters["force_touch_probing_velocity"]
    assert driver._force_touch_probing_acceleration == parameters["force_touch_probing_acceleration"]
    assert driver._force_touch_probing_threshold == parameters["force_touch_probing_threshold"]
    assert driver.min_force == parameters["min_force"]
    assert driver.max_force == parameters["max_force"]
    assert driver.force_calibration_window_size == parameters["force_calibration_window_size"]

def test_parameter_write():
    driver = init_driver()
    driver.set_axis_parameter(1234, 5678)
    assert driver.get_axis_parameter(1234) == 5678


def test_setting_getting_limits():
    """
    Test setting various parameter limits.
    """
    driver = init_driver()
    driver.set_continuous_and_peak_current_limits(peak_current_limit=1000, continous_current_limit=500)
    cc, pc = driver.get_continuous_and_peak_current_limits()
    driver.get_current_position()

    # Check that stored values are read back correctly.
    assert cc == 500
    assert pc == 1000


def test_force():
    """
    Test force application.
    """
    driver = init_driver()
    driver.force_tare()
    driver.seek_surface(pos=20)
    driver.force_press(force=100, duration=0.1, use_calib=False)


def test_timeouts():
    """
    Test timeouts work.
    """
    driver = init_driver()

    # Clear touch probe success bit
    driver._set_axis_parameter(SMRegs.SMP_FORCE_FUNCTIONS_STATUS, 0)
    with pytest.raises(Exception):
        driver.seek_surface(pos=10, timeout=0.1)

    # Set tare busy
    driver._set_axis_parameter(SMRegs.SMP_FORCE_FUNCTIONS_STATUS, (1 << SMRegs.FFS_TARE_BUSY))
    with pytest.raises(Exception):
        driver.force_tare(timeout=0.5)


def test_tare_failure():
    """
    Test that tare failure causes exception.
    """
    driver = init_driver()

    # clear tare success bit
    status = driver._comm.get_axis_parameter(driver._axis, SMRegs.SMP_FORCE_FUNCTIONS_STATUS)
    driver._set_axis_parameter(SMRegs.SMP_FORCE_FUNCTIONS_STATUS, status & ~(1 << SMRegs.FFS_TARE_SUCCESS))
    with pytest.raises(Exception):
        driver.force_tare()


def test_press():
    """
    Test that press gesture can be executed without errors.
    No validation is done.
    """
    robot, gestures = create_3axis_voicecoil_environment()

    robot.force_driver.press(context=gestures, x=0, y=0, force=400, z=10, tilt=0, azimuth=45, duration=0.1,
                             tool_name="tool1")


def test_drag_force():
    """
    Test that drag force gesture can be executed without errors.
    No validation is done.
    """
    robot, gestures = create_3axis_voicecoil_environment()

    robot.force_driver.drag_force(context=gestures, x1=0, y1=0, x2=50, y2=50, force = 300, z=10,
                                  tilt1=0, tilt2=0, azimuth1=0, azimuth2=90, tool_name="tool1")
