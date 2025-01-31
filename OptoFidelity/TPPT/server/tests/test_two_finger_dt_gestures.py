from tntserver.Nodes.TnT.Dut import *
from tntserver.Nodes.TwoFingerDt.Robot import *
from tntserver.Nodes.Mount import Mount
from tntserver.Nodes.TnT.Tool import Tool
from tntserver.Nodes.TnT.Tips import Tips
from .test_gestures import ProgramArguments, AXIS_DATA_PATH
from tntserver.Nodes.TnT.Gestures import *
from tntserver.Nodes.TnT.Workspace import Workspace
from tntserver.Nodes.TnT.Tools import Tools

import os.path
import glob

class TwoFingerDtGestureRecorder:
    """
    Record gesture parameters and produced robot API commands to files.
    This essentially provides counter for naming output files with increasing number postfix.
    """
    def __init__(self, directory, create_environment):
        self.counter = 0
        self.directory = directory
        self.create_environment = create_environment

    def record(self, gesture_name, gesture_args):
        # Create new environment for running each gesture.
        robot, gestures = self.create_environment()

        gesture_func = getattr(gestures, gesture_name)

        try:
            robot.driver.client.start_recording_commands()

            gesture_func(**gesture_args)

            executed_commands = robot.driver.client.executed_commands
        finally:
            robot.driver.client.stop_recording_commands()

        path = "gesture{}.json".format(self.counter)
        path = os.path.join(self.directory, path)

        data = {
            "gesture": gesture_name,
            "args": gesture_args,
            "executed_commands": executed_commands
        }

        with open(path, "w") as f:
            f.write(json.dumps(data, indent=0))

        self.counter += 1

        print("Recorded gesture {}: {} commands executed".format(gesture_name, len(executed_commands)))


def create_two_finger_dt_environment():
    """
    Create simple environment for running two-finger-dt robot simulator.
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

    tips = Tips("tips")
    ws.add_child(tips)

    mount1 = Mount("tool1_mount")
    mount1.mount_point = "tool1"
    mount1.add_child(tool1)

    mount2 = Mount("tool2_mount")
    mount2.mount_point = "tool2"
    mount2.add_child(tool2)

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
        program_arguments=ProgramArguments()
    )

    # TODO: DUT used in these tests has actually a wrong orientation. Should fix the DUT and update reference data.
    robot.maximum_dut_tilt_angle = 180

    robot.add_child(mount1)
    robot.add_child(mount2)
    ws.add_child(robot)

    dut = Dut("dut")
    dut.tl = {"x": -300, "y": -100, "z": -40}
    dut.tr = {"x": -200, "y": -100, "z": -40}
    dut.bl = {"x": -300, "y": -150, "z": -40}

    ws.add_child(dut)

    gestures = Gestures("Gestures")
    dut.add_child(gestures)
    gestures._init()

    return robot, gestures


def record_two_finger_dt_gestures():
    """
    Record gestures supported by two-finger-dt. These are currently almost all basic gestures except force gestures
    and circle (because arc primitive is not supported).
    This is not used during unit tests but can be used to update the test record.
    """
    recorder = TwoFingerDtGestureRecorder(os.path.join(AXIS_DATA_PATH, "two_finger_dt_gestures"), create_two_finger_dt_environment)

    recorder.record("put_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": -1, "duration": 0.3})

    recorder.record("put_double_tap", {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": -1,
                                       "duration": 0.2, "interval": 1.0})

    recorder.record("put_swipe", {"x1": 3, "y1": 4, "x2": 50, "y2": 60,
                                  "tilt1": 0, "tilt2": 0, "azimuth1": 0, "azimuth2": 0,
                                  "clearance": -1, "radius": 10})

    recorder.record("put_drag", {"x1": 3, "y1": 4, "x2": 50, "y2": 60,
                                 "tilt1": 0, "tilt2": 0, "azimuth1": 0, "azimuth2": 0,
                                 "clearance": -1, "predelay": 0.3, "postdelay": 0.6})

    recorder.record("put_jump", {"x": 3, "y": 4, "z": 10})
    recorder.record("put_jump", {"x": 3, "y": 4, "z": 10})
    recorder.record("put_jump", {"x": 3, "y": 4, "z": 10, "jump_height": 30})

    recorder.record("put_multiswipe", {"x1": 3, "y1": 4, "x2": 50, "y2": 55, "z": 10,
                                       "tilt": 0, "azimuth": 0, "clearance": -1, "n": 3})

    recorder.record("put_path", {"points":
        [
            {"x": 3, "y": 4, "z": 1, "tilt": 0, "azimuth": 0},
            {"x": 40, "y": 45, "z": 1, "tilt": 0, "azimuth": 0},
            {"x": 40, "y": 0, "z": 1, "tilt": 0, "azimuth": 0},
            {"x": 3, "y": 4, "z": 1, "tilt": 0, "azimuth": 0}
        ], "clearance": -1})

    recorder.record("put_pose", {"pose": robotmath.xyz_to_frame(20, 20, 0).tolist()})

    recorder.record("put_watchdog_tap",
                    {"x": 3, "y": 4, "z": 10, "tilt": 0, "azimuth": 0, "clearance": -1, "duration": 0.3})


def compare_nested_lists(list1, list2):
    """
    Compare recursively two lists of numbers that can contain other lists.
    In trivial case both parameters can also be numbers.
    :param list1: First list.
    :param list2: Second list.
    """
    if isinstance(list1, (float, int)):
        assert np.isclose(list1, list2, atol=1e-6)
        return

    assert len(list1) == len(list2)

    for i in range(len(list1)):
        compare_nested_lists(list1[i], list2[i])

def compare_commands(commands1, commands2):
    """
    Compare two commands recorded from two-finger-dt.
    :param commands1: First commands.
    :param commands2: Second commands.
    """
    assert len(commands1) == len(commands2)

    for i in range(len(commands1)):
        cmd1 = commands1[i]
        cmd2 = commands2[i]

        # Compare command names.
        assert cmd1[0] == cmd2[0]

        args1 = cmd1[1]
        args2 = cmd2[1]

        compare_nested_lists(args1, args2)


def test_two_finger_dt_gestures():
    """
    Test gestures by comparing commands to previously computed record.
    This is just an utility function used by the specific test cases.
    """

    #record_two_finger_dt_gestures()
    #return

    filenames = glob.glob(os.path.join(AXIS_DATA_PATH, "two_finger_dt_gestures", "*.json"))

    # In case the directory does not exist (e.g. if working directory is wrong) glob will not raise exception
    # but rather returns empty list. Make sure there are some tests to run.
    assert len(filenames) > 0

    # Loop through all axis data records and compare to ones generated by current code.
    for filename in filenames:
        with open(filename, "r") as f:
            data = json.loads(f.read())

        print("Testing gesture: " + data["gesture"])

        # Run each gesture in clean environment.
        robot, gestures = create_two_finger_dt_environment()

        # Run the gesture as specified by the record.
        gesture_func = getattr(gestures, data["gesture"])

        try:
            robot.driver.client.start_recording_commands()

            gesture_func(**data["args"])

            executed_commands = robot.driver.client.executed_commands
        finally:
            robot.driver.client.stop_recording_commands()

        compare_commands(executed_commands, data["executed_commands"])

