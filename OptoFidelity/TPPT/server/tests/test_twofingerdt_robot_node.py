from tntserver import Node, robotmath, NodeException
from tntserver.Nodes.Mount import Mount
from tntserver.Nodes.TnT.Tip import Tip
from tntserver.Nodes.TnT.Tool import Tool

import pytest
import numpy as np
import json

from tntserver.Nodes.TwoFingerDt.Robot import Robot


def init_robot(**kwargs):
    """
    Initialize robot node with sensible arguments.
    :return: Robot node object
    """
    root = Node("root")
    Node.root = root

    tool = Tool("tool1")

    mount = Mount("tool1_mount")
    mount.mount_point = "tool1"
    mount.add_child(tool)

    robot = Robot("Robot1")
    robot._init(
        driver="two_finger_dt",
        host="127.0.0.1",
        port=6842,
        simulator=True,
        speed=200,
        acceleration=400,
        separation_offset=10.0,
        axis_limits={"x_min": 0, "x_max": 600, "y_min": 0, "y_max": 600, "z_min": 0, "z_max": 100},
        tf_rotate_speed=50,
        tf_move_speed=40,
        thresholds={"angle": 0.01, "separation": 0.1, "position": 0.005},
        safe_distance=200.0,
    )

    robot.add_child(mount)
    root.add_child(robot)

    return robot


def test_init():
    """
    Test robot init. Even though this is done multiple times during other testing
    it is good to have separate test to more easily see if init causes the failure
    """
    robot = init_robot()

def test_homing():
    """
    Test robot homing.
    :return:
    """
    robot = init_robot()

    x, y, z, azimuth = -200, -200, -50, 0.0

    target_frame = robotmath.frame_to_pose(robotmath.xyz_to_frame(x, y, z))

    # Move robot to some position using tool1.
    robot.driver.move(target_frame, tool=robotmath.identity_frame(), kinematic_name="tool1")

    # 2-finger-dt homes x and y axes to maximum joint values and z-axis to minimum. Azimuth is homed to -90.
    robot.put_home()

    # Make sure robot joints are at correct positions after homing. This validates mainly simulator operation.
    assert robot.joint_position(joint='z') == 0.0
    assert robot.joint_position(joint='azimuth') == -90.0

    assert robot.joint_position(joint='x') == 600.0
    assert robot.joint_position(joint='y') == 600.0

def test_separation():
    """
    Test finger separation setting.
    :return:
    """
    robot = init_robot()
    separation_offset = 10
    assert robot.driver.separation == separation_offset

    robot.set_speed(speed=100, acceleration=500)

    limits = robot.get_finger_separation_limits()
    limits = json.loads(limits[1].decode())

    # Small margin is used for actual axis limits.
    reference = [separation_offset + 0.001, 147 + separation_offset - 0.001]

    assert np.allclose(limits, reference)
    robot.put_finger_separation(distance=20)
    assert json.loads(robot.get_finger_separation()[1].decode()) == 20

def test_multifinger_fails():
    """
    Test that having multifinger causes exceptions in robot functions as intended.
    :return:
    """
    tip = Tip(name='Testtip')
    robot = init_robot()
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