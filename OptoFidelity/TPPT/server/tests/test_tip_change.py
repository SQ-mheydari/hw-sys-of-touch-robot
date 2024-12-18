from tntserver.Nodes.TnT.Tool import Tool
from tntserver.Nodes.TnT.Tip import Tip
from tntserver.Nodes.TnT.Tips import Tips
from tntserver.Nodes.TnT.Workspace import Workspace
from tntserver.Nodes.TnT.Tools import Tools
from tntserver.Nodes.Node import *
from tests.common import *
from tntserver.Nodes.Mount import Mount
import pytest
import os
import importlib

# this unit test to
# 1. test 3 robot methods
# - put_attach_tip()
# - put_detach_tip()
# - put_change_tip()
# 2. test one finger and multi-finger
# 3. test book keeping, meaning after tip change, if the states of robot and tip are correct. Also under error situation
# e.g. movement error ( robot tries to move above maximun value), states shoul remain unchanged.
# 4. test for 3 types of robots: TnT (3 axis), Synchro, TwoFingerDt. These robots have own tip_changer.


def init_robot(robot_model):
    """
    Parameters
        robot_model: robot model
    :Returns: none
    """
    module_name = 'tntserver.Nodes.' + robot_model + '.Robot'
    module = importlib.import_module(module_name)
    robot_cls = getattr(module, 'Robot')
    robot = robot_cls("Robot_" + robot_model)
    if robot_model == 'TnT':
        robot_model = "3axis"
    if robot_model == "TwoFingerDt":
        robot_model = 'two_finger_dt'
    robot._init(
        driver="golden",
        host="127.0.1",
        port=4001,
        model=robot_model.lower(),
        simulator=True,
        speed=200,
        acceleration=400,
        max_tip_change_speed=150,
        max_tip_change_acceleration=300,
        program_arguments=ProgramArguments()
    )

    # DT robot 'TwoFingerDT' object has no attribute '_comm'
    if robot_model != 'two_finger_dt':
        robot.driver._comm.simulate_duration = False

    if robot_model == 'Synchro':
        calibration_data = {"tool2_offset": [[1, 0, 0, 6.15],
                                            [0, 1, 0, -0.29],
                                            [0, 0, 1, 0],
                                            [0, 0, 0, 1]],
                            "tool1_offset": [[1, 0, 0, -5.23],
                                            [0, 1, 0, -0.072],
                                            [0, 0, 1, 0],
                                            [0, 0, 0, 1]]
                           }
        robot.calibration_data = calibration_data
    return robot


def init(robot_model):
    """
    Initialize nodes: robot, tool, mount, tip.
    Parameters:
        robot_model: robot model
    :Returns: dict of initiated nodes
    """
    # use stub to avoid exception
    def save_stub():
        pass

    root = Node("root")
    Node.root = root

    ws = Workspace('ws')
    root.add_child(ws)

    tools = Tools("tools")
    ws.add_child(tools)

    tool = Tool("tool1")
    tools.add_child(tool)
    mount = Mount("tool_mount")
    mount.mount_point = "tool1"
    mount.add_child(tool)

    tips = Tips("tips")
    ws.add_child(tips)

    tip1 = Tip('tip1')
    tip2 = Tip('tip2')
    tip3 = Tip('tip3')
    tips.add_child(tip1)
    tips.add_child(tip2)
    tips.add_child(tip3)

    tip1.save = save_stub
    tip2.save = save_stub
    tip3.save = save_stub
    tool.save = save_stub

    # [x, y]
    tip1_slot_in = [120, 189]
    tip1_slot_out = [138, 189]
    tip2_slot_in = [284, 227]
    tip2_slot_out = [269, 227]

    # used to fake movement error when change tip
    y_false = 10000

    # DT robot uses negative values
    if robot_model == 'TwoFingerDt':
        for k in range(len(tip1_slot_in)):
            tip1_slot_in[k] = - tip1_slot_in[k]

        for k in range(len(tip1_slot_out)):
            tip1_slot_out[k] = - tip1_slot_out[k]

        for k in range(len(tip2_slot_in)):
            tip2_slot_in[k] = - tip2_slot_in[k]

        for k in range(len(tip2_slot_out)):
            tip2_slot_out[k] = - tip2_slot_out[k]

    tip1.slot_in = [[0.9, 0.5, 0, tip1_slot_in[0]],
                    [-0.5, 0.9, 0, tip1_slot_in[1]],
                    [-0, 0, 1, -65],
                    [0, 0, 0, 1]]

    tip1.slot_out = [[0.9, 0.5, 0, tip1_slot_out[0]],
                     [-0.5, 0.9, -0, tip1_slot_out[1]],
                     [-0, 0, 1, -65],
                     [0, 0, 0, 1]]

    tip2.slot_in = [[-1, -7e-05, 0, tip2_slot_in[0]],
                    [7e-05, -1, 0, tip2_slot_in[1]],
                    [-0, 0, 1, -85],
                    [0, 0, 0, 1]]

    tip2.slot_out = [[-1, 2e-05, -0, tip2_slot_out[0]],
                     [-2e-05, -1, 0, tip2_slot_out[1]],
                     [-0, 0, 1, -85],
                     [0, 0, 0, 1]]

    # tip3 is used to fake robot movement failure
    tip3.slot_in = [[-1, -7e-05, 0, 284],
                    [7e-05, -1, 0, y_false],
                    [-0, 0, 1, -85],
                    [0, 0, 0, 1]]

    tip3.slot_out = [[-1, 2e-05, -0, 269],
                     [-2e-05, -1, 0, y_false],
                     [-0, 0, 1, -85],
                     [0, 0, 0, 1]]

    tip_multifinger_1 = Tip('tipm1')
    tip_multifinger_1.model = 'Multifinger'
    tips.add_child(tip_multifinger_1)
    tip_multifinger_2 = Tip('tipm2')
    tip_multifinger_2.model = 'Multifinger'
    tips.add_child(tip_multifinger_2)
    tip_multifinger_1.save = save_stub
    tip_multifinger_2.save = save_stub

    tipm1_slot_in = [176, 400]
    tipm1_slot_out = [156, 400]
    tipm2_slot_in = [165, 400]
    tipm2_slot_out = [145, 400]

    # DT robot uses negative values
    if robot_model == 'TwoFingerDt':
        for k in range(len(tipm1_slot_in)):
            tipm1_slot_in[k] = - tipm1_slot_in[k]

        for k in range(len(tipm1_slot_out)):
            tipm1_slot_out[k] = - tipm1_slot_out[k]

        for k in range(len(tipm2_slot_in)):
            tipm2_slot_in[k] = - tipm2_slot_in[k]

        for k in range(len(tipm2_slot_out)):
            tipm2_slot_out[k] = - tipm2_slot_out[k]

    tip_multifinger_1.slot_in = [[-0, -1, 0, tipm1_slot_in[0]],
                                 [1, -0, 0, tipm1_slot_in[1]],
                                 [-0, 0, 1, -50],
                                 [0, 0, 0, 1]]
    tip_multifinger_1.slot_out = [[-0, -1, 0, tipm1_slot_out[0]],
                                  [1, -0, 0, tipm1_slot_out[1]],
                                  [-0, 0, 1, -50],
                                  [0, 0, 0, 1]]

    tip_multifinger_2.slot_in = [[-0, -1, 0, tipm2_slot_in[0]],
                                 [1, -0, 0, tipm2_slot_in[1]],
                                 [-0, 0, 1, -50],
                                 [0, 0, 0, 1]]
    tip_multifinger_2.slot_out = [[-0, -1, 0, tipm2_slot_out[0]],
                                  [1, -0, 0, tipm2_slot_out[1]],
                                  [-0, 0, 1, -50],
                                  [0, 0, 0, 1]]

    tip_multifinger_1.separation = 100
    tip_multifinger_2.separation = 100

    nodes = {}
    nodes['tool'] = tool
    nodes['tip1'] = tip1
    nodes['tip2'] = tip2
    nodes['tip3'] = tip3
    nodes['tip_multifinger_1'] = tip_multifinger_1
    nodes['tip_multifinger_2'] = tip_multifinger_2

    robot = init_robot(robot_model)
    ws.add_child(robot)
    robot.add_child(mount)
    nodes['robot_' + robot_model] = robot

    return nodes


############################################
# check book keeping
############################################
def attach_detach(is_multi_finger=False, robot_model='TnT'):
    """
    Run put_attach_tip(), put_detach_tip(). This is called by test_change_tip_book_keeping()
    Parameters
        is_multi_finger: bool
        robot_model: robot model
    Returns: none
    """
    nodes = init(robot_model)
    robot = nodes['robot_' + robot_model]

    if is_multi_finger:
        tip_1 = nodes['tip_multifinger_1']
        tip_2 = nodes['tip_multifinger_2']
        nodes['tool'].can_attach_multifinger_tip = True
    else:
        tip_1 = nodes['tip1']
        tip_2 = nodes['tip2']
        tip_3 = nodes['tip3']

    # before attach, make sure the tip is not attached
    assert robot.active_tip is None
    assert tip_1.is_attached is False
    assert tip_2.is_attached is False

    # attach tip which is not attached
    result = robot.put_attach_tip(tip_1.name)
    result_tip = from_jsonout(result)['tip']
    assert tip_1.name == result_tip.lower().strip()
    assert tip_1.name == robot.active_tip.name
    assert tip_1.is_attached is True
    assert tip_2.is_attached is False

    # attach tip which is already attached
    result = robot.put_attach_tip(tip_1.name)
    result_tip = from_jsonout(result)['tip']
    assert tip_1.name == result_tip.lower().strip()
    assert tip_1.name == robot.active_tip.name
    assert tip_1.is_attached is True
    assert tip_2.is_attached is False

    # attach non exist tip
    with pytest.raises(Exception):
        robot.put_attach_tip('xyz')

    # attach None tip
    with pytest.raises(Exception):
        robot.put_attach_tip(None)

    # attach tip to non exist tool
    with pytest.raises(Exception):
        robot.put_attach_tip(tip_id=tip_1.name, tool_name='xyz')

    # attach multifinger tip to tool can_attach_multifinger_tip is false
    if tip_1.is_multifinger:
        nodes['tool'].can_attach_multifinger_tip = False
        with pytest.raises(Exception):
            robot.put_attach_tip(tip_id=tip_1.name)

    # fake movement error (move above max value), check book keeping remain unchanged
    if not is_multi_finger:
        # before attach
        robot.put_detach_tip()
        assert robot.active_tip is None
        assert tip_3.is_attached is False
        # attach tip
        with pytest.raises(Exception):
            robot.put_attach_tip(tip_id=tip_3.name)
        # after attach, state should be unchanged
        assert robot.active_tip is None
        assert tip_3.is_attached is False

    # detach tip which is attached
    if tip_1.is_multifinger:
        nodes['tool'].can_attach_multifinger_tip = True
    robot.put_attach_tip(tip_id=tip_1.name)
    result = robot.put_detach_tip()
    result_tip = from_jsonout(result)['tip']
    assert result_tip is None
    assert robot.active_tip is None
    assert tip_1.is_attached is False
    assert tip_2.is_attached is False

    # detach tip which is not attached
    result = robot.put_detach_tip()
    result_tip = from_jsonout(result)['tip']
    assert result_tip is None
    assert robot.active_tip is None
    assert tip_1.is_attached is False
    assert tip_2.is_attached is False

    # fake movement error (move above max value), check book keeping remain unchanged
    # first attach tip_3 with correct slot values.
    # Then assign incorrect slot values, try to detach it.
    if not is_multi_finger:
        # before detach
        # assign correct value
        tip3_slot_in_erroneous = [284, 127]
        tip3_slot_out_erroneous = [269, 127]

        # DT robot uses negative values
        if robot_model == 'TwoFingerDt':
            for k in range(len(tip3_slot_in_erroneous)):
                tip3_slot_in_erroneous[k] = - tip3_slot_in_erroneous[k]
            for k in range(len(tip3_slot_out_erroneous)):
                tip3_slot_out_erroneous[k] = - tip3_slot_out_erroneous[k]

        tip_3.slot_in = [[-1, -7e-05, 0, tip3_slot_in_erroneous[0]],
                        [7e-05, -1, 0, tip3_slot_in_erroneous[1]],
                        [-0, 0, 1, -85],
                        [0, 0, 0, 1]]

        tip_3.slot_out = [[-1, 2e-05, -0, tip3_slot_out_erroneous[0]],
                         [-2e-05, -1, 0, tip3_slot_out_erroneous[1]],
                         [-0, 0, 1, -85],
                         [0, 0, 0, 1]]
        robot.put_attach_tip(tip_id=tip_3.name)
        assert tip_3.name == robot.active_tip.name
        assert tip_3.is_attached is True
        # detach tip
        # assign incorrect value, y value large than max

        # used to fake movement error when change tip
        y_false = 10000

        tip_3.slot_in = [[-1, -7e-05, 0, 284],
                         [7e-05, -1, 0, y_false],
                         [-0, 0, 1, -85],
                         [0, 0, 0, 1]]

        tip_3.slot_out = [[-1, 2e-05, -0, 269],
                          [-25e-05, -1, 0, y_false],
                          [-0, 0, 1, -85],
                          [0, 0, 0, 1]]
        with pytest.raises(Exception):
            robot.put_detach_tip()
        # after detach, state should be unchanged
        assert tip_3.name == robot.active_tip.name
        assert tip_3.is_attached is True


def change_tip (is_multi_finger=False, robot_model='TnT'):
    """
    Run put_change_tip(). This is called by test_change_tip_book_keeping()
    Parameters
        is_multi_finger: bool
        robot_model: robot model
    :Returns: none
    """
    nodes = init(robot_model)
    robot = nodes['robot_' + robot_model]

    if is_multi_finger:
        tip_1 = nodes['tip_multifinger_1']
        tip_2 = nodes['tip_multifinger_2']
        nodes['tool'].can_attach_multifinger_tip = True
    else:
        tip_1 = nodes['tip1']
        tip_2 = nodes['tip2']
        tip_3 = nodes['tip3']

    # attach tip1
    robot.put_attach_tip(tip_1.name)
    assert tip_1.is_attached is True
    assert tip_2.is_attached is False

    # change tip 2 to attach to robot
    result = robot.put_change_tip(tip=tip_2.name)
    result_tip = from_jsonout(result)['tip']
    assert tip_2.name == result_tip.lower().strip()
    assert tip_2.name == robot.active_tip.name
    assert tip_2.is_attached is True
    assert tip_1.is_attached is False

    # change tip with the same tip
    result = robot.put_change_tip(tip=tip_2.name)
    result_tip = from_jsonout(result)['tip']
    assert tip_2.name == result_tip.lower().strip()
    assert tip_2.name == robot.active_tip.name
    assert tip_2.is_attached is True
    assert tip_1.is_attached is False

    # change non exist tip
    with pytest.raises(Exception):
        robot.put_change_tip(tip='xyz')

    # fake movement error (move above max value), check book keeping remain unchanged
    # try to change from tip_3 to tip_2
    if not is_multi_finger:
        # before change
        # attach tip_3 with correct slot values
        tip3_slot_in_erroneous = [284, 127]
        tip3_slot_out_erroneous = [269, 127]
        # DT robot uses negative values
        if robot_model == 'TwoFingerDt':
            for k in range(len(tip3_slot_in_erroneous)):
                tip3_slot_in_erroneous[k] = - tip3_slot_in_erroneous[k]
            for k in range(len(tip3_slot_out_erroneous)):
                tip3_slot_out_erroneous[k] = - tip3_slot_out_erroneous[k]
        tip_3.slot_in = [[-1, -7e-05, 0, tip3_slot_in_erroneous[0]],
                         [7e-05, -1, 0, tip3_slot_in_erroneous[1]],
                         [-0, 0, 1, -85],
                         [0, 0, 0, 1]]

        tip_3.slot_out = [[-1, 2e-05, -0, tip3_slot_out_erroneous[0]],
                          [-2e-05, -1, 0, tip3_slot_out_erroneous[1]],
                          [-0, 0, 1, -85],
                          [0, 0, 0, 1]]

        robot.put_attach_tip(tip_id=tip_3.name)

        assert tip_1.is_attached is False
        assert tip_2.is_attached is False
        assert tip_3.is_attached is True
        assert tip_3.name == robot.active_tip.name
        # try to change from tip_3 to tip_2
        # assign tip_3 incorrect slot values which would cause movement error when do detach

        # used to fake movement error when change tip
        y_false = 10000

        tip_3.slot_in = [[-1, -7e-05, 0, 284],
                         [7e-05, -1, 0, y_false],
                         [-0, 0, 1, -85],
                         [0, 0, 0, 1]]

        tip_3.slot_out = [[-1, 2e-05, -0, 269],
                          [-1e-05, -1, 0, y_false],
                          [-0, 0, 1, -85],
                          [0, 0, 0, 1]]

        with pytest.raises(Exception):
            robot.put_change_tip(tip=tip_2.name)
        # after change, state should be unchanged
        assert tip_1.is_attached is False
        assert tip_2.is_attached is False
        assert tip_3.is_attached is True
        assert tip_3.name == robot.active_tip.name


@pytest.mark.parametrize("is_multi_finger", [True, False])
@pytest.mark.parametrize("robot_model", ['TnT', 'Synchro', 'TwoFingerDt'])
def test_change_tip_book_keeping(is_multi_finger, robot_model):
    """
    Run tests of change tip, check if book keepings are correct or not
    Parameters
        is_multi_finger: bool
        robot_model: robot model
    :Returns: none
    """
    attach_detach(is_multi_finger, robot_model)
    change_tip(is_multi_finger, robot_model)


############################################
# check movements
############################################
def check_movements(json_ref, json_temp, robot_model):
    """
    Compare reference json file and json file generated from test. This is called by record_movement()
    Parameters
        json_ref: reference json file
        json_temp: json file generated from test
        robot_model: robot model
    :Returnss: none
    """

    if json_ref and json_temp:
        with open(json_ref, 'r') as f1:
            movement_ref = json.load(f1)

        with open(json_temp, 'r') as f2:
            movement_temp = json.load(f2)

        if len(movement_ref) != len(movement_temp):
            assert False
        else:
            for i in range(len(movement_ref)):
                if robot_model == 'TwoFingerDt':
                    if movement_temp[i][0] == 'Robot_SaveLocation':
                        assert movement_temp[i][1] == pytest.approx(movement_ref[i][1])
                else:
                    compare_axes(movement_ref[i], movement_temp[i])
    else:
        assert False


def record_movement(action, is_multi_finger=False, robot_model='TnT'):
    """
    Call change tip methods, record movement. This is called by test_change_tip_movement()
    Parameters
        action: attach or detach, or change
        is_multi_finger: bool
        robot_model: robot model
    :Returns: none
    """
    nodes = init(robot_model)
    robot = nodes['robot_' + robot_model]

    if is_multi_finger:
        tip_1 = nodes['tip_multifinger_1']
        tip_2 = nodes['tip_multifinger_2']
        nodes['tool'].can_attach_multifinger_tip = True
    else:
        tip_1 = nodes['tip1']
        tip_2 = nodes['tip2']

    # start point should be the same as the one when reference file is generated
    if action == 'attach':
        robot.put_home()
    else:
        robot.put_attach_tip(tip_1.name)

    path_temp = os.path.abspath(os.path.join(os.getcwd(), 'tests', action + '_tip_temp.json'))

    if robot_model == 'TwoFingerDt':
        try:
            robot.driver.client.start_recording_commands()
            if action == 'attach':
                robot.put_attach_tip(tip_1.name)
            elif action == 'detach':
                robot.put_detach_tip()
            elif action == 'change':
                robot.put_change_tip(tip_2.name)
            executed_commands = robot.driver.client.executed_commands
        finally:
            robot.driver.client.stop_recording_commands()
        with open(path_temp, "w") as f:
            f.write(json.dumps(executed_commands))
    else:
        robot.put_start_recording_axes()
        if action == 'attach':
            robot.put_attach_tip(tip_1.name)
        elif action == 'detach':
            robot.put_detach_tip()
        elif action == 'change':
            robot.put_change_tip(tip_2.name)

        robot.put_save_recorded_axes(path_temp)
        robot.put_stop_recording_axes()

    # compare recorded movement with reference
    if is_multi_finger:
        file_name = action + '_tip_multifg_ref.json'
    else:
        file_name = action + '_tip_ref.json'
    path_reference = os.path.abspath(
        os.path.join(os.getcwd(), 'tests', 'axis_data', 'tip_change', robot_model, file_name))
    check_movements(path_reference, path_temp, robot_model)

    # delete json files generated from test
    if os.path.exists(path_temp):
        try:
            os.remove(path_temp)
        except:
            pass


@pytest.mark.parametrize("is_multi_finger", [True, False])
@pytest.mark.parametrize("robot_model", ['TnT', 'Synchro', 'TwoFingerDt'])
def test_change_tip_movement(is_multi_finger, robot_model):
    """
    Run test tip change, compare movements to reference files
    Only for TnT and Synchro robots, not for TwoFinger Dt which doesn't have axis recording
    Parameters
        is_multi_finger: is multi-finger
        robot_model: robot model
    :Returns: none
    """
    record_movement('attach', is_multi_finger, robot_model)
    record_movement('detach', is_multi_finger, robot_model)
    record_movement('change', is_multi_finger, robot_model)


############################################
# Below is not used in test.
# It is used only for generate reference movement json files
# for robots except two finger Dt robot
############################################
def generate_reference_movements():
    """
    Generate reference. This is not used in the test
    :Returns: none
    """
    robot_models = ('TnT', 'Synchro')
    actions = ('attach', 'detach', 'change')
    finger_type = (False, True)
    for robot_model in robot_models:
        for is_multi_finger in finger_type:
            for action in actions:
                nodes = init(robot_model)
                robot = nodes['robot_' + robot_model]

                path_reference = os.path.abspath(
                    os.path.join(os.getcwd(), 'tests', 'axis_data', 'tip_change', robot_model))

                if not os.path.exists(path_reference):
                     os.makedirs(path_reference, exist_ok=True)

                nodes['tool'].can_attach_multifinger_tip = True

                if is_multi_finger:
                    tip_1 = nodes['tip_multifinger_1']
                    tip_2 = nodes['tip_multifinger_2']
                    nodes['tool'].can_attach_multifinger_tip = True
                else:
                    tip_1 = nodes['tip1']
                    tip_2 = nodes['tip2']

                if action == 'attach':
                    robot.put_home()
                else:
                    robot.put_attach_tip(tip_1.name)

                robot.put_start_recording_axes()

                if action == 'attach':
                    robot.put_attach_tip(tip_1.name)
                elif action == 'detach':
                    robot.put_detach_tip()
                elif action == 'change':
                    robot.put_change_tip(tip_2.name)

                if is_multi_finger:
                    file_ref = os.path.join(path_reference, action + '_tip_multifg_ref.json')
                else:
                    file_ref = os.path.join(path_reference, action + '_tip_ref.json')
                robot.put_save_recorded_axes(file_ref)
                robot.put_stop_recording_axes()


############################################
# Below is not used in test.
# It is used only for generate reference movement json files
# for two finger Dt robot
############################################
def generate_reference_movements_dt():
    """
    Generate reference. This is not used in the test
    :Returns: none
    """
    actions = ('attach', 'detach', 'change')
    finger_type = (False, True)

    for is_multi_finger in finger_type:
        for action in actions:
            robot_model = 'TwoFingerDt'
            nodes = init(robot_model)
            robot = nodes['robot_' + robot_model]

            path_reference = os.path.abspath(
                os.path.join(os.getcwd(), 'tests', 'axis_data', 'tip_change', robot_model))

            if not os.path.exists(path_reference):
                os.makedirs(path_reference, exist_ok=True)

            nodes['tool'].can_attach_multifinger_tip = True

            if is_multi_finger:
                tip_1 = nodes['tip_multifinger_1']
                tip_2 = nodes['tip_multifinger_2']
                nodes['tool'].can_attach_multifinger_tip = True
            else:
                tip_1 = nodes['tip1']
                tip_2 = nodes['tip2']

            if action == 'attach':
                robot.put_home()
            else:
                robot.put_attach_tip(tip_1.name)

            try:
                robot.driver.client.start_recording_commands()
                if action == 'attach':
                    robot.put_attach_tip(tip_1.name)
                elif action == 'detach':
                    robot.put_detach_tip()
                elif action == 'change':
                    robot.put_change_tip(tip_2.name)
                executed_commands = robot.driver.client.executed_commands
            finally:
                robot.driver.client.stop_recording_commands()

            if is_multi_finger:
                file_ref = os.path.join(path_reference, action + '_tip_multifg_ref.json')
            else:
                file_ref = os.path.join(path_reference, action + '_tip_ref.json')

            with open(file_ref, "w") as f:
                f.write(json.dumps(executed_commands))