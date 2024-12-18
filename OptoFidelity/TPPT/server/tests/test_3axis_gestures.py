from tntserver.Nodes.TnT.Dut import *
from tntserver.Nodes.TnT.Duts import Duts
from tntserver.Nodes.TnT.Robot import *
from tntserver.Nodes.Mount import *
from tntserver.Nodes.TnT.Workspace import Workspace
from tntserver.Nodes.TnT.Tools import Tools
from .test_gestures import ProgramArguments, GestureRecorder, _test_gestures, AXIS_DATA_PATH, record_base_gestures
from tntserver.Nodes.TnT.Gestures import *

import os.path


def create_3axis_environment():
    """
    Create simple environment for running 3-axis robot simulator.
    """

    root = Node("root")
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

    robot = Robot("Robot1")
    robot.max_robot_velocity = 10000
    ws.add_child(robot)

    robot._init(
        driver="golden",
        host="127.0.0.1",
        port=4001,
        model="3axis",
        simulator=True,
        speed=200,
        acceleration=400,
        program_arguments=ProgramArguments()
    )

    # There's no reason to simulate duration when testing gesture positions.
    robot.driver._comm.simulate_duration = False

    robot.add_child(mount)

    dut = Dut("dut")
    dut.tl = {"x": 100, "y": 100, "z": -40}
    dut.tr = {"x": 150, "y": 100, "z": -40}
    dut.bl = {"x": 100, "y": 150, "z": -40}

    duts = Duts("duts")
    ws.add_child(duts)
    duts.add_child(dut)

    gestures = Gestures("Gestures")
    dut.add_child(gestures)
    gestures._init()

    return robot, gestures

def record_3axis_gestures():
    recorder = GestureRecorder(os.path.join(AXIS_DATA_PATH, "3axis_gestures"), create_3axis_environment)

    record_base_gestures(recorder)


def test_3axis_gestures():
    #record_3axis_gestures()
    _test_gestures("3axis_gestures", create_3axis_environment)

