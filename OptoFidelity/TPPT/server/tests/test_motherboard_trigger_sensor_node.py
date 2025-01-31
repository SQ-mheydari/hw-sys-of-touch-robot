from tntserver.Nodes.NodeMotherboardTriggerSensor import NodeMotherboardTriggerSensor
from tests.test_synchro_robot_node import RobotStub
import pytest


def test_mb_trigger_node():

    mb_node = NodeMotherboardTriggerSensor(name="MotherboardTrigger1")

    # Create robot and node structure
    robot = RobotStub("Robot1")
    mb_node._init(robot="Robot1", io_dev_addr=31)

    # Test that base class functions can be called
    mb_node.init_auto_trigger()
    mb_node.reset_encoder_value()
    mb_node.set_trigger_touch_start()
    mb_node.set_trigger_touch_end()


def test_mb_init_fail_robot():

    mb_node = NodeMotherboardTriggerSensor(name="MotherboardTrigger1")
    robot = RobotStub("Robot1")

    # Init with non-existing robot name
    mb_node._init(robot="Robot123", io_dev_addr=31)

    # Base class call should fail
    with pytest.raises(Exception):
        mb_node.init_auto_trigger()


def test_mb_init_fail_comm_driver():

    mb_node = NodeMotherboardTriggerSensor(name="MotherboardTrigger1")
    robot = RobotStub("Robot1")
    robot.driver._comm = None

    # Init with non-existing communication driver
    mb_node._init(robot="Robot1", io_dev_addr=31)

    # Base class call should fail
    with pytest.raises(Exception):
        mb_node.init_auto_trigger()
