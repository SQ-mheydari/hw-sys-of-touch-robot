import json

from tntserver.drivers.robots.golden_program import Program
from tntserver.Nodes.Voicecoil.Robot import Robot as VoicecoilRobot
import tntserver.drivers.robots.sm_regs as SMRegs


class RobotStub(VoicecoilRobot):
    """
    Helper class to enable robot functions without actual HW.
    """
    def __init__(self, name, **kwargs):
        super().__init__(name)

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

        super()._init(
            driver="golden",
            host="127.0.0.1",
            port=4001,
            model="3axis_voicecoil",
            simulator=True,
            axis_specs=axis_specs,
            speed=200,
            acceleration=400,
            visualize=False,
            force_driver="opto_std_force",
            force_parameters=force_parameters,
            **kwargs
        )
        self.program = Program(robot=self)

        # Set some registers to non-zero values.
        self.driver.set_axis_parameter('voicecoil1', SMRegs.SMP_AXIS_SCALE, 20000)
        self.driver.set_axis_parameter('voicecoil1', SMRegs.SMP_ENCODER_PPR, 1024)
        self.driver.set_axis_parameter('voicecoil1', SMRegs.SMP_ACTUAL_POSITION_FB, 12345)

        # Set force control register to return immediate success for tare and touch probe.
        self.driver.set_axis_parameter('voicecoil1', SMRegs.SMP_FORCE_FUNCTIONS_STATUS, (1 << SMRegs.FFS_TARE_SUCCESS) |
                                       (1 << SMRegs.FFS_TOUCH_PROBE_SUCCESS))

        self.calibration_saved = False

    def force_press(self, force: float, duration=1, tare=False, use_calib=True):

        # This function is called during force calibration (among other uses), with usually a long duration. To allow
        # quicker unit test execution, the duration is minimized before the call is passed to the base class.
        super().force_press(force=force, tare=tare, duration=0.05, use_calib=use_calib)

    def save(self):
        self.calibration_saved = True


def test_force_functions():
    """
    Test force related functions.
    """
    robot = RobotStub(name='Robot1')
    robot.force_driver.force_tare()
    robot.force_driver.seek_surface()
    robot.force_driver.force_press(force=100, duration=0.1, use_calib=False)


def test_homing():
    """
    Test homing functions.
    """
    robot = RobotStub(name='Robot1')
    robot.put_home()
    robot.home()


def test_current_limits():
    """
    Test that set current limits are stored and read back correctly.
    """
    robot = RobotStub(name='Robot1')
    cc, pc = 100, 200
    robot.set_current_limits(continuous_current=cc, peak_current=pc)

    read_cc, read_pc = robot.force_driver.get_continuous_and_peak_current_limits()

    assert read_cc == cc
    assert read_pc == pc

