from tntserver.Nodes.TnT.Dut import *
from tntserver.Nodes.TnT.Duts import Duts
from tntserver.Nodes.TnT.Tools import Tools
from tntserver.Nodes.TnT.Workspace import Workspace
from tntserver.Nodes.Synchro.Robot import *
from tntserver.Nodes.Mount import *
from .test_gestures import ProgramArguments, GestureRecorder, _test_gestures, AXIS_DATA_PATH, record_base_gestures
from tntserver.Nodes.Synchro.Gestures import *
from tntserver.drivers.robots.goldenmov.open_loop_force import VoicecoilForce

import os.path


def create_synchro_environment():
    """
    Create simple environment for running synchro robot simulator.
    """

    root = Node("root")
    Node.root = root

    ws = Workspace('ws')
    root.add_child(ws)

    tools = Tools("tools")
    ws.add_child(tools)

    tool1 = Tool("tool1")
    tools.add_child(tool1)
    tool2 = Tool("tool2")
    tools.add_child(tool2)

    mount1 = Mount("tool1_mount")
    mount1.mount_point = "tool1"
    mount1.add_child(tool1)

    mount2 = Mount("tool2_mount")
    mount2.mount_point = "tool2"
    mount2.add_child(tool2)

    mid_mount = Mount("mid_mount")
    mid_mount.mount_point = "mid"

    synchro_mount = Mount("synchro_mount")
    synchro_mount.mount_point = "synchro"

    tool1_offset = robotmath.xyz_to_frame(-5.2290681, -0.07199028, 0).tolist()
    tool2_offset = robotmath.xyz_to_frame(6.15097277, -0.02862004, 0).tolist()

    robot = Robot("Robot1")
    robot.max_robot_velocity = 10000

    robot.calibration_data = {"tool1_offset": tool1_offset, "tool2_offset": tool2_offset}

    robot._init(
        driver="golden",
        host="127.0.0.1",
        port=4001,
        model="synchro",
        simulator=True,
        speed=200,
        acceleration=400,
        force_driver="open_loop_force",
        program_arguments=ProgramArguments()
    )

    robot.force_calibration_table = {"voicecoil1": {"force": [20.0, 600.0], "current": [100.0, 1300.0]},
                                     "voicecoil2": {"force": [20.0, 600.0], "current": [100.0, 1300.0]}}

    # There's no reason to simulate duration when testing gesture positions.
    robot.driver._comm.simulate_duration = False

    axis_specs = robot.driver._kinematics.specs()
    axis_specs[11]['press_margin'] = 5
    axis_specs[12]['press_margin'] = 5

    robot.driver._kinematics.set_specs(axis_specs)

    robot.add_child(mount1)
    robot.add_child(mount2)
    robot.add_child(mid_mount)
    robot.add_child(synchro_mount)
    ws.add_child(robot)

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


def record_synchro_gestures():
    """
    Run a fixed set of gestures and save the axes data to file record.
    This is intended to be used when updating the record.
    Not ran as part of unit tests.
    """
    recorder = GestureRecorder(os.path.join(AXIS_DATA_PATH, "synchro_gestures"), create_synchro_environment)

    # Record the base gestures which are supported by synchro although result in different axis positions.
    record_base_gestures(recorder)

    recorder.record("put_pinch", {"x": 3, "y": 4, "d1": 30, "d2": 60, "azimuth": 30, "z": 10, "clearance": -1})

    recorder.record("put_drumroll", {"x": 3, "y": 4, "azimuth": 30, "separation": 40, "tap_count": 4, "tap_duration": 1.0, "clearance": -1})

    recorder.record("put_compass", {"x": 3, "y": 4, "azimuth1": 30, "azimuth2": 90, "separation": 30, "z": 10,
                     "clearance": -1, "kinematic_name": "tool1"})

    recorder.record("put_compass_tap", {"x": 3, "y": 4, "azimuth1": 10, "azimuth2": 90, "separation": 30,
                                        "tap_azimuth_step": 15, "z": 10, "tap_with_stationary_finger": False,
                                        "clearance": -1})

    recorder.record("put_compass_tap", {"x": 3, "y": 4, "azimuth1": 30, "azimuth2": 90, "separation": 30,
                                        "tap_azimuth_step": 15, "z": 10, "tap_with_stationary_finger": True,
                                        "clearance": -1})

    recorder.record("put_touch_and_tap", {"touch_x": 3, "touch_y": 4, "tap_x": 30, "tap_y": 35, "z": 10,
                                          "number_of_taps": 1, "tap_predelay": 0.5, "tap_duration": 0.3,
                                          "tap_interval": 0.2, "clearance": -1})

    recorder.record("put_touch_and_tap", {"touch_x": 3, "touch_y": 4, "tap_x": 30, "tap_y": 35, "z": 10,
                                          "number_of_taps": 2, "tap_predelay": 0.5, "tap_duration": 0.3,
                                          "tap_interval": 0.2, "clearance": -1})

    recorder.record("put_line_tap", {"x1": 3, "y1": 4, "x2": 30, "y2": 60, "tap_distances": [10, 20, 30], "separation": 30,
                                     "azimuth": 30, "z": 10, "clearance": -1})

    recorder.record("put_press", {"x": 3, "y": 4, "force": 300, "z": 10, "tilt": 0, "azimuth": 30,
                                  "duration": 0.5, "press_depth": -1})

    recorder.record("put_fast_swipe", {"x1": 3, "y1": 4, "x2": 40, "y2": 60, "separation1": 30, "separation2": 100,
                                       "speed": 400, "acceleration": 800, "tilt1": 0, "tilt2": 0,"clearance": -1,
                                         "radius": 10})

    recorder.record("put_rotate", {"x": 3, "y": 4, "azimuth1": 80, "azimuth2": 200, "separation": 60, "z": 10,
                                   "clearance": -1})

    recorder.record("put_touch_and_drag", {"x0": 12, "y0": 34, "x1": 42, "y1": 12, "x2": 50, "y2": 53, "z": 10,
                                   "clearance": -1})

    recorder.record("put_smooth_path", {"points":
                                 [
                                     {"x": 10, "y": 10, "z": 1, "tilt": 0, "azimuth": 0},
                                     {"x": 40, "y": 45, "z": 2, "tilt": 0, "azimuth": 45},
                                     {"x": 30, "y": 10, "z": 3, "tilt": 0, "azimuth": 60},
                                     {"x": 20, "y": 40, "z": 4, "tilt": 0, "azimuth": 90}
                                 ], "clearance": -1})

    recorder.record("put_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": -1, "duration": 0.3, "separation": 30, "tool_name": "tool1"})
    recorder.record("put_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": -1, "duration": 0.3, "separation": 30, "tool_name": "tool2"})
    recorder.record("put_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": -1, "duration": 0.3, "separation": 30, "tool_name": "both"})
    recorder.record("put_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 90, "clearance": -1, "duration": 0.3, "separation": 30, "tool_name": "both"})

    recorder.record("put_double_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": -1, "duration": 0.2, "interval": 1.0, "separation": 30, "tool_name": "tool1"})
    recorder.record("put_double_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": -1, "duration": 0.2, "interval": 1.0, "separation": 30, "tool_name": "tool2"})
    recorder.record("put_double_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": -1, "duration": 0.2, "interval": 1.0, "separation": 30, "tool_name": "both"})
    recorder.record("put_double_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 90, "clearance": -1, "duration": 0.2, "interval": 1.0, "separation": 30, "tool_name": "both"})

    recorder.record("put_swipe", {"x1": 3, "y1": 4, "x2": 50, "y2": 60, "tilt1": 0, "tilt2": 0, "azimuth1": 0, "azimuth2": 0, "clearance": -1, "radius": 10, "separation": 30, "tool_name": "tool1"})
    recorder.record("put_swipe", {"x1": 3, "y1": 4, "x2": 50, "y2": 60, "tilt1": 0, "tilt2": 0, "azimuth1": 0, "azimuth2": 0, "clearance": -1, "radius": 10, "separation": 30, "tool_name": "tool2"})
    recorder.record("put_swipe", {"x1": 3, "y1": 4, "x2": 50, "y2": 60, "tilt1": 0, "tilt2": 0, "azimuth1": 0, "azimuth2": 0, "clearance": -1, "radius": 10, "separation": 30, "tool_name": "both"})
    recorder.record("put_swipe", {"x1": 3, "y1": 4, "x2": 50, "y2": 60, "tilt1": 0, "tilt2": 0, "azimuth1": 90, "azimuth2": 90, "clearance": -1, "radius": 10, "separation": 30, "tool_name": "both"})

    recorder.record("put_touch_and_tap", {"touch_x": 3, "touch_y": 4, "tap_x": 30, "tap_y": 35, "z": 10,
                                          "number_of_taps": 2, "tap_predelay": 0.5, "tap_duration": 0.3,
                                          "tap_interval": 0.2, "clearance": -1, "touch_duration": 0.1})

    recorder.record("put_touch_and_drag", {"x0": 12, "y0": 34, "x1": 42, "y1": 12, "x2": 50, "y2": 53, "z": 10,
                                           "clearance": -1, "delay": 1.0, "touch_duration": 0.5})

    # Test also case where touch_duration exceeds secondary finger motion.
    recorder.record("put_touch_and_tap", {"touch_x": 3, "touch_y": 4, "tap_x": 30, "tap_y": 35, "z": 10,
                                          "number_of_taps": 2, "tap_predelay": 0.5, "tap_duration": 0.3,
                                          "tap_interval": 0.2, "clearance": -1, "touch_duration": 3.0})

    recorder.record("put_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": 0, "duration": 0,
                                "separation": 50, "tool_name": "tool1", "kinematic_name": "tool2"})

    recorder.record("put_drag", {"x1": 3, "y1": 4, "x2": 50, "y2": 60, "tilt1": 0, "tilt2": 0, "azimuth1": 0,
                                 "azimuth2": 0, "clearance": -1, "predelay": 0.3, "postdelay": 0.6,
                                 "separation":30, "tool_name": "tool1"})
    recorder.record("put_drag", {"x1": 3, "y1": 4, "x2": 50, "y2": 60, "tilt1": 0, "tilt2": 0, "azimuth1": 0,
                                 "azimuth2": 0, "clearance": -1, "predelay": 0.3, "postdelay": 0.6,
                                 "separation": 30, "tool_name": "tool2"})
    recorder.record("put_drag", {"x1": 3, "y1": 4, "x2": 50, "y2": 60, "tilt1": 0, "tilt2": 0, "azimuth1": 0,
                                 "azimuth2": 0, "clearance": -1, "predelay": 0.3, "postdelay": 0.6,
                                 "separation": 30, "tool_name": "both"})

    recorder.record("put_circle", {"x": 20, "y": 25, "r": 15, "n": 2, "angle": 45, "z": 10,
                                   "tilt": 0, "azimuth": 0, "clearance": -1, "clockwise": False,
                                   "separation": 30, "tool_name": "tool1"})
    recorder.record("put_circle", {"x": 20, "y": 25, "r": 15, "n": 2, "angle": 45, "z": 10,
                                   "tilt": 0, "azimuth": 0, "clearance": -1, "clockwise": False,
                                   "separation": 30, "tool_name": "tool2"})
    recorder.record("put_circle", {"x": 20, "y": 25, "r": 15, "n": 2, "angle": 45, "z": 10,
                                   "tilt": 0, "azimuth": 0, "clearance": -1, "clockwise": False,
                                   "separation": 30, "tool_name": "both"})

    recorder.record("put_multiswipe", {"x1": 3, "y1": 4, "x2": 50, "y2": 55, "z": 10,
                                       "tilt": 0, "azimuth": 0, "clearance": -1, "n": 3,
                                       "separation": 30, "tool_name": "tool1"})
    recorder.record("put_multiswipe", {"x1": 3, "y1": 4, "x2": 50, "y2": 55, "z": 10,
                                       "tilt": 0, "azimuth": 0, "clearance": -1, "n": 3,
                                       "separation": 30, "tool_name": "tool2"})
    recorder.record("put_multiswipe", {"x1": 3, "y1": 4, "x2": 50, "y2": 55, "z": 10,
                                       "tilt": 0, "azimuth": 0, "clearance": -1, "n": 3,
                                       "separation": 30, "tool_name": "both"})

    points = [
            {"x": 3, "y": 4, "z": 1, "tilt": 0, "azimuth": 0},
            {"x": 40, "y": 45, "z": 1, "tilt": 0, "azimuth": 0},
            {"x": 40, "y": 0, "z": 1, "tilt": 0, "azimuth": 0},
            {"x": 3, "y": 4, "z": 1, "tilt": 0, "azimuth": 0}
        ]
    recorder.record("put_path", {"points": points, "clearance": -1, "separation": 30, "tool_name": "tool1"})
    recorder.record("put_path", {"points": points, "clearance": -1, "separation": 30, "tool_name": "tool2"})
    recorder.record("put_path", {"points": points, "clearance": -1, "separation": 30, "tool_name": "both"})

    recorder.record("put_press", {"x": 3, "y": 4, "force": 300, "z": 10, "tilt": 0, "azimuth": 30,
                                  "duration": 0.5, "press_depth": -1, "separation": 30, "tool_name": "tool1"})
    recorder.record("put_press", {"x": 3, "y": 4, "force": 300, "z": 10, "tilt": 0, "azimuth": 30,
                                  "duration": 0.5, "press_depth": -1, "separation": 30, "tool_name": "tool2"})
    recorder.record("put_press", {"x": 3, "y": 4, "force": 300, "z": 10, "tilt": 0, "azimuth": 30,
                                  "duration": 0.5, "press_depth": -1, "separation": 30, "tool_name": "both"})

    recorder.record("put_drag_force", {"x1": 3, "y1": 4, "x2": 20, "y2": 23, "force": 300, "z": 10, "tilt1": 0,
                                       "tilt2":0, "azimuth1": 0, "azimuth2": 0, "separation": 30, "tool_name": "tool1"})
    recorder.record("put_drag_force", {"x1": 3, "y1": 4, "x2": 20, "y2": 23, "force": 300, "z": 10, "tilt1": 0,
                                       "tilt2":0, "azimuth1": 0, "azimuth2": 0, "separation": 30, "tool_name": "tool2"})
    recorder.record("put_drag_force", {"x1": 3, "y1": 4, "x2": 20, "y2": 23, "force": 300, "z": 10, "tilt1": 0,
                                       "tilt2":0, "azimuth1": 0, "azimuth2": 0, "separation": 30, "tool_name": "both"})


def test_synchro_gestures():
    #record_synchro_gestures()
    _test_gestures("synchro_gestures", create_synchro_environment)


def test_voicecoil_force():
    """
    Test class VoicecoilForce.
    """
    class RobotStub:
        def __init__(self):
            self.torques = {"axis1": 5, "axis2": 6}

        def read_torque_limit(self, axis):
            return self.torques[axis]

        def set_force_limit(self, axis_name, force_grams):
            # This sets torque directly as force value i.e. simulates identity mapping.
            # This is ok as the test applies only to class VoicecoilForce so this mapping is not relevant.
            self.torques[axis_name] = force_grams

        def set_torque_limit(self, axis_name, torque):
            self.torques[axis_name] = torque

    robot = RobotStub()

    assert robot.torques["axis1"] == 5 and robot.torques["axis2"] == 6

    with VoicecoilForce(robot, {"axis1": 10, "axis2": 20}):
        assert robot.torques["axis1"] == 10 and robot.torques["axis2"] == 20

    assert robot.torques["axis1"] == 5 and robot.torques["axis2"] == 6
