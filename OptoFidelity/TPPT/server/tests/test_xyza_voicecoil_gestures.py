from tntserver.Nodes.TnT.Dut import *
from tntserver.Nodes.TnT.Robot import *
from tntserver.Nodes.Mount import *
from tntserver.Nodes.TnT.Workspace import Workspace
from .test_gestures import ProgramArguments, GestureRecorder, _test_gestures, AXIS_DATA_PATH, record_base_gestures
from tntserver.Nodes.TnT.Gestures import *

import os.path


def create_xyza_voicecoil_environment():
    """
    Create simple environment for running xyza_voicecoil robot simulator
    """
    root = Node("root")
    Node.root = root

    ws = Workspace('ws')
    root.add_child(ws)

    tool = Tool("tool1")

    mount = Mount("tool1_mount")
    mount.mount_point = "tool1"
    mount.add_child(tool)

    robot = Robot("Robot1")
    robot._init(
        driver="golden",
        host="127.0.0.1",
        port=4001,
        model="xyza_voicecoil",
        simulator=True,
        speed=200,
        acceleration=400,
        program_arguments=ProgramArguments()
    )

    # There's no reason to simulate duration when testing gesture positions.
    robot.driver._comm.simulate_duration = False

    robot.add_child(mount)
    ws.add_child(robot)

    dut = Dut("dut")
    dut.tl = {"x": 100, "y": 100, "z": -40}
    dut.tr = {"x": 150, "y": 100, "z": -40}
    dut.bl = {"x": 100, "y": 150, "z": -40}

    ws.add_child(dut)

    gestures = Gestures("Gestures")
    dut.add_child(gestures)
    gestures._init()

    return robot, gestures


def record_xyza_voicecoil_gestures():
    recorder = GestureRecorder(os.path.join(AXIS_DATA_PATH, "xyza_voicecoil_gestures"),
                               create_xyza_voicecoil_environment)

    record_base_gestures(recorder)

    recorder.record("put_spin_tap", {"x": 3, "y": 4, "z": 5, "azimuth1": 0, "azimuth2": 30, "clearance": -1,
                                     "duration": 0.3, "spin_at_contact": False})

    recorder.record("put_spin_tap", {"x": 3, "y": 4, "z": 5, "azimuth1": 0, "azimuth2": 30, "clearance": -1,
                                     "duration": 0.3, "spin_at_contact": True})


def test_xyza_voicecoil_gestures():
    # record_xyza_voicecoil_gestures()
    _test_gestures("xyza_voicecoil_gestures", create_xyza_voicecoil_environment)


def test_spin_tap_azimuth_ranges():
    robot, gestures = create_xyza_voicecoil_environment()
    gestures.put_spin_tap(x=0, y=0, z=10, tilt=0, azimuth1=0, azimuth2=30, clearance=0, duration=0,
                          spin_at_contact=False)

    # Error is expected when azimuth range exceeds over 179 degrees.
    try:
        gestures.put_spin_tap(x=0, y=0, z=10, tilt=0, azimuth1=10, azimuth2=190, clearance=0, duration=0,
                              spin_at_contact=False)
    except ValueError:
        pass
    else:
        assert False, 'Azimuth rotation over 179 degrees was accepted'

