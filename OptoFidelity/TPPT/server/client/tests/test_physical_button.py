from tntclient.tnt_client import *
import pytest


def init_physical_button():
    physical_button_name = 'physical_button1'
    tntclient = TnTClient()
    return physical_button_name, tntclient


def define_button():
    """
    All these (need to connect to server) now are put into the method. Otherwise, jenkins would try to connect to server
    during loading test cases before server starts.
    Returns: TnTPhysicalButtonClient
    -------

    """
    physical_button_name, tntclient = init_physical_button()
    buttons = tntclient.physical_buttons()
    button_names = [button.name for button in buttons]
    if physical_button_name not in button_names:
        tntclient.add_physical_button(physical_button_name)
    button_test = tntclient.physical_button(physical_button_name)
    return button_test


def test_approach_position():
    button_test = define_button()
    pos =   [[1, 0, 0, 30],
             [0, 1, 0, 60],
             [0, 0, 1, -20],
             [0, 0, 0, 0]]

    button_test.approach_position = pos
    result = button_test.approach_position
    for i in range(len(result)):
        assert result[i] == pytest.approx(pos[i])


def test_jump_height():
    button_test = define_button()
    value = 0.3
    button_test.jump_height = value
    result = button_test.jump_height
    assert value == pytest.approx(result)


def test_pressed_position():
    button_test = define_button()
    pos =   [[1, 0, 0, 31],
             [0, 1, 0, 62],
             [0, 0, 1, -21],
             [0, 0, 0, 0]]

    button_test.pressed_position = pos
    result = button_test.pressed_position
    for i in range(len(result)):
        assert result[i] == pytest.approx(pos[i])


def test_remove():
    physical_button_name, tntclient = init_physical_button()
    button_test = define_button()
    button_test.remove()
    buttons_new = tntclient.physical_buttons()
    button_names_new = [button.name for button in buttons_new]
    assert physical_button_name not in button_names_new

