from tntserver.drivers.robots.goldenmov import GoldenMovRecorder
from tntserver.Nodes.Node import Node
from tntserver.Nodes.TnT.Workspace import Workspace
from tntserver.Nodes.TnT.PhysicalButtons import PhysicalButtons
from tntserver.Nodes.TnT.PhysicalButton import PhysicalButton
from tntserver.robotmath import xyz_to_frame
from tests.test_3axis_gestures import create_3axis_environment
from tests.test_synchro_gestures import create_synchro_environment
from tests.test_gestures import compare_axes, AXIS_DATA_PATH
from tests.test_tnt_robot_node import from_jsonout

import os
import json


def create_press_environment(robot_type: str):
    if robot_type == '3axis':
        robot, gestures = create_3axis_environment()
    elif robot_type == 'synchro':
        robot, gestures = create_synchro_environment()
    else:
        raise Exception('Unknown robot type')

    dut = Node.find('dut')
    ws = Node.find('ws')

    buttons = PhysicalButtons('physical_buttons')
    ws.add_child(buttons)

    # Create a button with workspace connection
    ws_button = PhysicalButton('ws_button')
    buttons.add_child(ws_button)
    ws_button._init()
    ws_button.approach_position = xyz_to_frame(0, 0, -20).tolist()
    ws_button.pressed_position = xyz_to_frame(0, 0, -30).tolist()
    ws_button.jump_height = 10.0
    # Use add_object_child instead of put_set_connection since that saves and would require a configuration manager
    ws.add_object_child(ws_button)

    # Create a second button for testing listing
    ws_button2 = PhysicalButton('ws_button2')
    buttons.add_child(ws_button2)
    ws.add_object_child(ws_button2)

    # Create a button with dut connection, with the same parameters to ensure that context handling works
    dut_button = PhysicalButton('dut_button')
    buttons.add_child(dut_button)
    dut_button._init()
    dut_button.approach_position = xyz_to_frame(0, 0, -20).tolist()
    dut_button.pressed_position = xyz_to_frame(0, 0, -30).tolist()
    dut_button.jump_height = 10.0
    dut.add_object_child(dut_button)

    return robot


def test_physical_button_movements():
    """
    Test physical button pressing axis movements for all robot types and different button parents
    :return:
    """
    robot_types = ['3axis', 'synchro']
    buttons = ['ws_button', 'dut_button']

    for robot_type in robot_types:
        robot = create_press_environment(robot_type)
        for button in buttons:
            path = os.path.join(AXIS_DATA_PATH, 'press_tests', '{}_{}.json'.format(robot_type, button))
            with open(path, 'r') as f:
                data = json.loads(f.read())

            robot.put_home()
            with GoldenMovRecorder(robot.driver):
                robot.press_physical_button(button)
                executed_axes = robot.driver.executed_axes

            for i in range(len(executed_axes)):
                compare_axes(executed_axes[i], data['buffered_motions'][i])


def test_physical_button_listing():
    """
    Test that querying buttons for connections work properly
    """
    # The button hierarchy is the same for both robot types, so it's enough to test just one
    robot = create_press_environment('3axis')

    buttons = Node.find('physical_buttons')

    ws_buttons = from_jsonout(buttons.get_list_buttons('ws'))
    assert sorted(['ws_button', 'ws_button2']) == sorted(ws_buttons)

    dut_buttons = from_jsonout(buttons.get_list_buttons('dut'))
    assert sorted(['dut_button']) == sorted(dut_buttons)


def record_press_movements():
    """
    Record press movements when the functionality is known to work to compare to later when changes are made.
    """
    robot_types = ['3axis', 'synchro']
    buttons = ['ws_button', 'dut_button']

    for robot_type in robot_types:
        robot = create_press_environment(robot_type)
        for button in buttons:
            robot.put_home()
            with GoldenMovRecorder(robot.driver):
                robot.press_physical_button(button)
                executed_axes = robot.driver.executed_axes

            path = os.path.join(AXIS_DATA_PATH, 'press_tests', '{}_{}.json'.format(robot_type, button))
            data = {
                'robot_type': robot_type,
                'button': button,
                'buffered_motions': executed_axes
            }

            with open(path, 'w') as f:
                f.write(json.dumps(data, indent=0))


def test_dut_physical_button_removal():
    """
    Test that all physical buttons related to dut are deleted when the dut is deleted.
    """

    # As we only test if the buttons are deleted it is enough to test with one robot.
    robot = create_press_environment('3axis')
    dut = Node.find('dut')
    dut.delete_self()
    buttons = Node.find('physical_buttons')
    dut_buttons = from_jsonout(buttons.get_list_buttons('dut'))
    assert len(dut_buttons) == 0


