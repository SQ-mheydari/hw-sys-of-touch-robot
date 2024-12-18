from tntclient.tnt_robot_client import TnTRobotClient
from tntclient.tnt_client import *
import pytest
import time

def init_nodes():
    tip_name = 'tip1'
    physical_button_name = 'physical_button1'
    robot_name = 'Robot1'
    robot_client = TnTRobotClient(robot_name)
    tntclient = TnTClient()
    return tip_name, physical_button_name, robot_name, robot_client, tntclient


def init_robot_tip():
    """
    All these (need to connect to server) now are put into the method. Otherwise, jenkins would try to connect to server
    during loading test cases before server starts.
    Returns: TnTRobotClient (just for test cases to use)
    -------

    """
    tip_name, physical_button_name, robot_name, robot_client, tntclient = init_nodes()
    robot_client.set_speed(speed=50000, acceleration=100000)
    tips = tntclient.tips()
    if tips is not None:
        if len(tips) > 0:
            tip_names = [tip.name for tip in tips]
            if tip_name not in tip_names:
                tntclient.add_tip(tip_name)
    else:
        tntclient.add_tip(tip_name)
    return robot_client


def test_tip():
    tip_name, physical_button_name, robot_name, robot_client, tntclient = init_nodes()
    # test get/set active finger
    result = robot_client.get_active_finger()
    finger_new = abs(result - 1)
    robot_client.set_active_finger(finger_new)

    result = robot_client.get_active_finger()
    assert result == finger_new

    # test change tip
    # first detach all tips
    result = robot_client.detach_tip(finger_id=finger_new)
    assert result['tip'] is None

    # set tip1 to active tip
    robot_client.change_tip(tip=tip_name, finger_id=finger_new)
    # now change active tip as tip2
    tip_new = 'tip2'
    result = robot_client.change_tip(tip=tip_new, finger_id=finger_new)
    assert result['tip'] == tip_new

    # test get/set finger separation
    d = robot_client.get_finger_separation()
    # get new value to be set
    d_new = 20.226
    # seems speed and acceleration would affect results
    # these values taken are the same as in unit test test_synchro_robot_node.py
    robot_client.set_speed(speed=100, acceleration=500)
    robot_client.set_finger_separation(d_new)

    result = robot_client.get_finger_separation()
    # the difference comes from the last point and target value. It is a known issue. And no plan to change it.
    # if there is some significant difference between these numbers that is expected.
    assert round(result) == round(d_new)


def test_get_position():
    robot_client = init_robot_tip()
    x, y, z = 100, 200, -50
    # get home position
    robot_client.go_home()
    result_home = robot_client.get_position()
    assert 'position' in result_home.keys()
    assert result_home['status'] == 'ok'

    # move to a position
    result_move = robot_client.move(x=x, y=y, z=z)
    assert pytest.approx(result_move['position']['x']) == x
    assert pytest.approx(result_move['position']['y']) == y
    assert pytest.approx(result_move['position']['z']) == z
    result_move_pos = robot_client.get_position()
    assert pytest.approx(result_move_pos['position']['x']) == x
    assert pytest.approx(result_move_pos['position']['y']) == y
    assert pytest.approx(result_move_pos['position']['z']) == z

    # move relatively to a position
    d_x, d_y, d_z = 50, 60, 3
    robot_client.move_relative(x=d_x, y=d_y, z=d_z)
    result_move_pos_relative = robot_client.get_position()
    assert pytest.approx(result_move_pos_relative['position']['x']) == x + d_x
    assert pytest.approx(result_move_pos_relative['position']['y']) == y + d_y
    assert pytest.approx(result_move_pos_relative['position']['z']) == z + d_z

    # go home
    robot_client.go_home()
    result_go_home_pos = robot_client.get_position()
    assert result_go_home_pos['position']['x'] == pytest.approx(result_home['position']['x'])
    assert result_go_home_pos['position']['y'] == pytest.approx(result_home['position']['y'])
    assert result_go_home_pos['position']['z'] == pytest.approx(result_home['position']['z'])

def test_speed():
    robot_client = init_robot_tip()
    values = robot_client.get_speed()
    speed_new = values['speed'] - 10
    acceleration_new = values['acceleration'] - 15
    robot_client.set_speed(speed=speed_new, acceleration=acceleration_new)
    result = robot_client.get_speed()
    assert result['speed'] == speed_new
    assert result['acceleration'] == acceleration_new


def test_reset_robot_error():
    robot_client = init_robot_tip()
    robot_client.reset_robot_error()


def test_press_physical_button():
    tip_name, physical_button_name, robot_name, robot_client, tntclient = init_nodes()
    buttons = tntclient.physical_buttons()
    button_names = [button.name for button in buttons]
    if physical_button_name not in button_names:
        tntclient.add_physical_button(physical_button_name)

    button_test = tntclient.physical_button(physical_button_name)
    if button_test.approach_position is None:
        button_test.approach_position = [[1, 0, 0, 30],
                                         [0, 1, 0, 60],
                                         [0, 0, 1, -20],
                                         [0, 0, 0, 0]]

    if button_test.pressed_position is None:
        button_test.pressed_position = [[1, 0, 0, 33],
                                         [0, 1, 0, 61],
                                         [0, 0, 1, -21],
                                         [0, 0, 0, 0]]

    if button_test.jump_height is None:
        button_test.jump_height = 0.5

    result = robot_client.press_physical_button(button_name=physical_button_name, duration=0.1)
    assert result == 'ok'
