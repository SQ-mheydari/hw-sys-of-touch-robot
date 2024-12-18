from tntserver.drivers.robots.golden_program import Program
from tntserver.Nodes.Synchro.Robot import Robot as SynchroRobot
from tntserver.Nodes.TnT.Tip import Tip
from tntserver.Nodes.TnT.Workspace import Workspace
from tntserver.Nodes.TnT.Tools import Tools
from tntserver.Nodes.Node import Node, NodeException
from tntserver.Nodes.TnT.PhysicalButton import PhysicalButton
from tntserver.Nodes.TnT.Robot import Mount, Tool
from .test_synchro_gestures import create_synchro_environment
import tntserver.drivers.robots.sm_regs as SMRegs
import tntserver.robotmath as robotmath

import pytest
import numpy as np
import json


class RobotStub(SynchroRobot):
    """
    Helper class to enable robot functions without actual HW.
    """
    def __init__(self, name):
        super().__init__(name)

        root = Node("root")

        # Set global root node to enable find operations.
        Node.root = root

        ws = Workspace('ws')
        root.add_child(ws)

        tools = Tools("tools")
        ws.add_child(tools)

        tool = Tool("tool1")
        tools.add_child(tool)

        mount = Mount("tool1_mount")
        mount.mount_point = "tool1"
        mount.add_child(tool)

        super()._init(
            driver="golden",
            host="127.0.0.1",
            port=4001,
            model="synchro",
            simulator=True,
            speed=200,
            acceleration=400,
            visualize=False
        )
        self.program = Program(robot=self)

        ws.add_child(self)
        self.add_child(mount)

        self.calibration_data = dict()
        self.calibration_data["tool1_offset"] = np.eye(4).tolist()
        self.calibration_data["tool2_offset"] = np.eye(4).tolist()

        # No need to simulate duration during unit tests
        self.driver._comm.simulate_duration = False

        button = PhysicalButton(name="TestButton")
        button.jump_height = 5
        button.approach_position = robotmath.xyz_to_frame(10, 10, -30)
        button.pressed_position = robotmath.xyz_to_frame(11, 12, -40)
        ws.add_child(button)

        self.max_voicecoil_current = 1360


def test_homing():
    """
    Test robot homing.
    :return:
    """
    robot = RobotStub(name='TestRobot')
    robot.put_home()

    # Make sure robot joints are at correct positions after homing. This validates mainly simulator operation.
    joints = ['z', 'azimuth', 'voicecoil1', 'voicecoil2']
    for joint in joints:
        assert robot.joint_position(joint=joint) == 0.0

    assert robot.joint_position(joint='x') == 15.0
    assert robot.joint_position(joint='y') == 15.0


def test_multifinger_fails():
    """
    Test that having multifinger causes exceptions in robot functions as intended.
    :return:
    """
    tip = Tip(name='Testtip')
    robot = RobotStub(name='TestRobot')
    robot.active_tool.add_child(tip)
    # make the tip multifinger
    robot.active_tip.model = "Multifinger"

    # Test that exceptions caused by having a multifinger tool are raised
    with pytest.raises(NodeException):
        robot.put_home()

    with pytest.raises(NodeException):
        robot.put_finger_separation(distance=1)

    with pytest.raises(Exception):
        robot.press_physical_button(button_name="TestButton")


def test_force_torque_limit_settings(caplog):
    """
    Test setting force and torque limits.
    :param caplog: pytest built-in fixture for logging capture
    :return:
    """

    robot = RobotStub(name='TestRobot')

    # Set some dummy values into the calibration table.
    robot.force_calibration_table = {'voicecoil1': {'current': [1, 2, 3], 'force': [10, 20, 30]}}

    # Generate calibration functions so we can set parameter values. Test that calibration table values match.
    robot.force_driver.set_force_limit(axis_name='voicecoil1', grams=30)
    assert robot.force_driver.read_torque_limit(axis_name='voicecoil1') == 3

    # Test setting of torque limit.
    test_limit = robot.max_voicecoil_current * 0.5
    robot.set_torque_limit(axis_name='voicecoil1', torque_limit=test_limit)
    assert json.loads(robot.get_axis_parameter(axis='voicecoil1',
                                               parameter=SMRegs.SMP_TORQUELIMIT_CONT)[1].decode()) == test_limit

    # Test that we get a warning.
    caplog.clear()
    robot.set_torque_limit(axis_name='voicecoil1', torque_limit=robot.max_voicecoil_current + 1)
    for record in caplog.records:
        assert record.levelname == "WARNING"


def test_axis_positions():
    """
    Test setting individual axis position.
    :return:
    """
    robot = RobotStub(name='TestRobot')
    robot.put_axis_position(axis='voicecoil1', value=10.0)
    robot.set_speed(speed=100, acceleration=500)

    # Final axis position is one position increment short of commanded value. This value is "correct" for the given
    # speed and acceleration parameters.
    assert json.loads(robot.get_axis_position(axis='voicecoil1')[1].decode()) == 9.999989624528315


def test_separation():
    """
    Test finger separation setting.
    :return:
    """
    robot = RobotStub(name='TestRobot')
    assert robot.default_separation == json.loads(robot.get_default_separation()[1].decode())

    robot.set_speed(speed=100, acceleration=500)
    # Final axis position is one position increment short of commanded value. This value is "correct" for the given
    # speed and acceleration parameters.

    limits = robot.get_finger_separation_limits()
    limits = json.loads(limits[1].decode())

    # Small margin is used for actual axis limits.
    reference = [-2 + 0.001, 130 - 0.001]

    assert np.allclose(limits, reference)

    robot.put_finger_separation(distance=20)
    assert json.loads(robot.get_finger_separation()[1].decode()) == 19.996000000000002


def test_press_physical_button():
    """
    Test pressing physical button.
    :return:
    """
    robot = RobotStub(name='TestRobot')
    assert json.loads(robot.put_press_physical_button(button_name="TestButton")[1].decode()) == "ok"

    # Test that pressing non-existent button fails
    with pytest.raises(NodeException):
        robot.press_physical_button("Dummy")


def test_camera_capture_preparations():
    """
    Test camera_capture_preparations().
    :return:
    """
    robot = RobotStub(name='TestRobot')
    # Move azimuth to non-zero so we can verify it changes to zero
    robot.move_relative(x=10, y=10, z=-10, azimuth=100)
    position_before = json.loads(robot.get_position()[1].decode())["position"]

    robot.camera_capture_preparations("Camera1")
    # Check that azimuth is zeroed
    position = json.loads(robot.get_position()[1].decode())["position"]
    assert position['azimuth'] == pytest.approx(0.0)
    # Check that other axis were not changed
    assert position['x'] == pytest.approx(position_before['x'])
    assert position['y'] == pytest.approx(position_before['y'])
    assert position['z'] == pytest.approx(position_before['z'])


def test_move_voicecoils():
    """
    Test robot API put_move_voicecoils.
    """
    robot, gestures = create_synchro_environment()

    # Note that reference position is slightly less than target due to known issue in create_track().
    target_pos = 8.0
    ref_pos = 7.99838379715733

    robot.put_move_voicecoils(target_pos)
    vc1_pos = robot.axis_position("voicecoil1")
    vc2_pos = robot.axis_position("voicecoil2")

    assert np.allclose([vc1_pos, vc2_pos], [ref_pos, ref_pos])

    target_pos = 2.0
    ref_pos = 2.000167804404812

    robot.put_move_voicecoils(target_pos)
    vc1_pos = robot.axis_position("voicecoil1")
    vc2_pos = robot.axis_position("voicecoil2")

    assert np.allclose([vc1_pos, vc2_pos], [ref_pos, ref_pos])
