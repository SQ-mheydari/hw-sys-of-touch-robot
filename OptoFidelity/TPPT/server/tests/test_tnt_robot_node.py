from tntserver.Nodes.TnT.Robot import *
from tntserver.Nodes.Node import *
import json
import pytest


@json_out
def to_jsonout(data_input):
    """
    Changes input to @json_out function format
    :param input: data to be converted
    :param data_input: data to be converted
    :return: input in @json_out format tuple
    """
    return data_input


def from_jsonout(jsonout_input):
    """
    Changes @json_out formatted input back to python form
    NOTE: might not handle for example None well
    :param input: @json_out formatted tuple
    :param jsonout_input: @json_out formatted tuple
    :return: the python form of the binary part
    """
    return json.loads(jsonout_input[1].decode('utf-8'))


class ProgramArguments:
    def __init__(self):
        self.visual_simulation = False


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
        driver="golden",
        host="127.0.0.1",
        port=4001,
        model="3axis",
        simulator=True,
        speed=200,
        acceleration=400,
        program_arguments=ProgramArguments(),
        **kwargs
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


def test_effective_pose():
    """
    Test robot effective pose by first checking the initialization value and then
    moving the robot and checking if pose changes.
    """
    robot = init_robot()
    start_pose = np.matrix([[1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
    end_pose = np.matrix([[1, 0, 0, 30],
                          [0, 1, 0, 20],
                          [0, 0, 1, -40],
                          [0, 0, 0, 1]])
    assert np.allclose(start_pose, robot.effective_pose())

    robot._move(x=end_pose[0, 3], y=end_pose[1, 3], z=end_pose[2, 3])

    assert np.allclose(end_pose, robot.effective_pose())


def test_set_effective_pose():
    """
    Test set_effective_pose
    """
    robot = init_robot()
    ok_pose = np.matrix([[1, 0, 0, 0],
                         [0, 1, 0, 0],
                         [0, 0, 1, 0],
                         [0, 0, 0, 1]])
    too_large_pose = np.matrix([[1, 0, 0, 0, 0],
                                [0, 1, 0, 0, 0],
                                [0, 0, 1, 0, 0],
                                [0, 0, 0, 1, 0]])
    too_small_pose = np.matrix([[1, 0, 20],
                                [0, 1, 20],
                                [0, 0, 20],
                                [0, 0, 1]])

    robot.set_effective_pose(robot, ok_pose)

    assert np.allclose(ok_pose, robot.effective_pose())

    with pytest.raises(Exception):
        robot.set_effective_pose(robot, too_large_pose)
        robot.set_effective_pose(robot, too_small_pose)


def test_move_frame():
    """
    Test move_frame
    """
    robot = init_robot()
    ok_frame = np.matrix([[1, 0, 0, -20],
                          [0, 1, 0, 20],
                          [0, 0, 1, -20],
                          [0, 0, 0, 1]])
    ok_effective_frame = np.matrix([[-1, 0, 0, -20],
                                    [0, 1, 0, 20],
                                    [0, 0, -1, -20],
                                    [0, 0, 0, 1]])
    too_large_frame = np.matrix([[1, 0, 0, -20, 0],
                                 [0, 1, 0, 20, 0],
                                 [0, 0, 1, -20, 0],
                                 [0, 0, 0, 1, 0]])
    too_small_frame = np.matrix([[1, 0, -20],
                                 [0, 1, 20],
                                 [0, 0, -20],
                                 [0, 0, 1]])

    robot.move_frame(ok_frame, robot)
    assert np.allclose(ok_effective_frame, robot.effective_frame)

    with pytest.raises(Exception):
        robot.move_frame(robot, too_large_frame)
        robot.move_frame(robot, too_small_frame)


def test_move_error():
    """
    Test _move assertion errors, the correct functionality
    testing is included in other tests
    """
    robot = init_robot()

    with pytest.raises(Exception):
        robot._move(x="str", y=1.0, z=1.0, x_roll=1.0, y_roll=1.0, z_roll=1.0, tilt=1.0, azimuth=1.0, spin=1.0)
        robot._move(x=1.0, y="str", z=1.0, x_roll=1.0, y_roll=1.0, z_roll=1.0, tilt=1.0, azimuth=1.0, spin=1.0)
        robot._move(x=1.0, y=1.0, z="str", x_roll=1.0, y_roll=1.0, z_roll=1.0, tilt=1.0, azimuth=1.0, spin=1.0)
        robot._move(x=1.0, y=1.0, z=1.0, x_roll="str", y_roll=1.0, z_roll=1.0, tilt=1.0, azimuth=1.0, spin=1.0)
        robot._move(x=1.0, y=1.0, z=1.0, x_roll=1.0, y_roll="str", z_roll=1.0, tilt=1.0, azimuth=1.0, spin=1.0)
        robot._move(x=1.0, y=1.0, z=1.0, x_roll=1.0, y_roll=1.0, z_roll="str", tilt=1.0, azimuth=1.0, spin=1.0)
        robot._move(x=1.0, y=1.0, z=1.0, x_roll=1.0, y_roll=1.0, z_roll=1.0, tilt="str", azimuth=1.0, spin=1.0)
        robot._move(x=1.0, y=1.0, z=1.0, x_roll=1.0, y_roll=1.0, z_roll=1.0, tilt=1.0, azimuth="str", spin=1.0)
        robot._move(x=1.0, y=1.0, z=1.0, x_roll=1.0, y_roll=1.0, z_roll=1.0, tilt=1.0, azimuth=1.0, spin="str")


def test_kinematic_name():
    """
    Test kinematic name functions
    """
    default_kinematic_name = "tool1"
    new_kinematic_name = "test_tool"

    robot = init_robot()
    assert robot.kinematic_name == default_kinematic_name

    robot.put_kinematic_name(new_kinematic_name)
    assert robot.kinematic_name == new_kinematic_name
    assert robot.get_kinematic_name() == to_jsonout(new_kinematic_name)

    with pytest.raises(Exception):
        # test non-string kinematic name
        robot.kinematic_name = 123


def test_put_active_finger():
    """
    Test put_active_finger()
    """
    robot = init_robot()
    finger_name = "tool2"
    finger_id = 1
    robot.put_active_finger(finger_id)
    assert robot.kinematic_name == finger_name

    with pytest.raises(Exception):
        robot.put_active_finger("not_int")
        robot.put_active_finger(1.0)


def test_get_active_finger():
    """
    Test get_active_finger()
    """
    robot = init_robot()
    finger_name = "tool1"
    finger_id = 0
    robot.kinematic_name = finger_name
    assert robot.get_active_finger() == to_jsonout(finger_id)


def test_put_home():
    """
    Test put_home()
    """
    robot = init_robot()
    home_pose = np.matrix([[1, 0, 0, 0],
                           [0, 1, 0, 0],
                           [0, 0, 1, 0],
                           [0, 0, 0, 1]])

    robot._move(x=30, y=20, z=-40)
    robot.put_home()
    assert np.allclose(home_pose, robot.effective_pose())


def test_put_speed_get_speed():
    """
    Test put_speed() and get_speed()
    """
    speed = 50.0
    acceleration = 100.0

    robot = init_robot()

    # Making sure we are not testing with default values
    assert speed != robot.robot_velocity
    assert acceleration != robot.robot_acceleration

    robot.put_speed(speed=speed, acceleration=acceleration)

    speed_values = from_jsonout(robot.get_speed())

    assert np.isclose(speed_values["speed"], speed)
    assert np.isclose(speed_values["acceleration"], acceleration)

    with pytest.raises(Exception):
        robot.put_speed(speed="str", acceleration=acceleration)
        robot.put_speed(speed=speed, acceleration="str")


def test_has_tooltip():
    """
    Test has_tooltip()
    """
    robot = init_robot()
    has_tool_tip = from_jsonout(robot.get_has_tool_tip())
    assert has_tool_tip["tool"] == "tool1"
    assert has_tool_tip["tip"] is None


def test_tool_frame_no_tip():
    """
    Test tool_frame() without any tip attached
    """
    robot = init_robot()
    test_frame = np.matrix([[1, 0, 0, 20],
                            [0, 1, 0, 30],
                            [0, 0, 1, 40],
                            [0, 0, 0, 1]])
    robot.active_tool.frame = test_frame
    assert np.allclose(robot.tool_frame(), test_frame)


def test_tool_frame_with_tip():
    """
    test_tool_frame() with a tip attached
    :return:
    """
    robot = init_robot()

    tool_frame = np.matrix([[1, 0, 0, 40],
                            [0, 1, 0, 30],
                            [0, 0, 1, 20],
                            [0, 0, 0, 1]])
    tip_frame = np.matrix([[1, 0, 0, 30],
                           [0, 1, 0, 20],
                           [0, 0, 1, 40],
                           [0, 0, 0, 1]])
    result_frame = tool_frame * tip_frame

    # adding frame to active tool
    robot.active_tool.frame = tool_frame
    # adding tip with frame to active tool
    tip = Tip("tip1")
    tip.frame = tip_frame
    robot.active_tool.add_child(tip)

    assert np.allclose(robot.tool_frame(), result_frame)


def test_robot_frame_with_tool_frame():
    """
    Test that robot effective frame is calculated correctly with
    non-identity tool frame
    """
    robot = init_robot()
    tool_frame = np.matrix([[1, 0, 0, 30],
                            [0, 1, 0, 20],
                            [0, 0, 1, 40],
                            [0, 0, 0, 1]])
    robot_frame = np.matrix([[-1, 0, 0, -30],
                             [0, 1, 0, 20],
                             [0, 0, -1, -40],
                             [0, 0, 0, 1]])
    robot.active_tool.frame = tool_frame

    assert np.allclose(robot.effective_frame, robot_frame)


def test_robot_frame_with_tip_frame():
    """
    Test that robot effective frame is calculated correctly with
    non-identity tip frame
    """
    robot = init_robot()
    tip_frame = np.matrix([[1, 0, 0, 10],
                           [0, 1, 0, 20],
                           [0, 0, 1, 30],
                           [0, 0, 0, 1]])
    robot_frame = np.matrix([[-1, 0, 0, -10],
                             [0, 1, 0, 20],
                             [0, 0, -1, -30],
                             [0, 0, 0, 1]])
    # Attaching the tip to the tool
    tip = Tip("tip1")
    tip.frame = tip_frame
    robot.active_tool.add_child(tip)

    assert np.allclose(robot.effective_frame, robot_frame)


def test_robot_frame_with_tip_and_tool_frame():
    """
    Test that robot effective frame is calculated correctly with
    non-identity tool and tip frame combined
    """
    robot = init_robot()
    tip_frame = np.matrix([[1, 0, 0, 20],
                           [0, 1, 0, 30],
                           [0, 0, 1, 40],
                           [0, 0, 0, 1]])
    tool_frame = np.matrix([[1, 0, 0, 10],
                            [0, 1, 0, 50],
                            [0, 0, 1, 60],
                            [0, 0, 0, 1]])
    robot_frame = np.matrix([[-1, 0, 0, -30],
                             [0, 1, 0, 80],
                             [0, 0, -1, -100],
                             [0, 0, 0, 1]])
    # setting the tool frame
    robot.active_tool.frame = tool_frame
    # attaching the tip and setting the frame
    tip = Tip("tip1")
    tip.frame = tip_frame
    robot.active_tool.add_child(tip)

    assert np.allclose(robot.effective_frame, robot_frame)


def test_find_mount():
    """
    Test find_mount() so that there are multiple mounts
    """
    robot = init_robot()

    # adding another mount to robot in addition to the one
    # added in init_robot()
    tool_2 = Tool("tool2")
    mount_2 = Mount("tool2_mount")
    mount_2.mount_point = "tool2"
    mount_2.add_child(tool_2)
    robot.add_child(mount_2)

    assert robot.find_mount("tool2") == mount_2


def test_active_tool():
    """
    Test active_tool()
    """
    robot = init_robot()

    # adding another mount with tool to robot in addition to the one added
    # in init_robot() so that we can compare to correct object
    tool_2 = Tool("tool2")
    mount_2 = Mount("tool2_mount")
    mount_2.mount_point = "tool2"
    mount_2.add_child(tool_2)
    robot.add_child(mount_2)

    # selecting the just created tool to be active
    robot.kinematic_name = "tool2"

    assert robot.active_tool == tool_2


def test_active_tip():
    """
    Test active_tip()
    """
    robot = init_robot()

    # adding another mount with tool and tip to robot in addition to the one added
    # in init_robot() so that we can compare to correct object
    tool_2 = Tool("tool2")
    tip_2 = Tip("tip2")
    tool_2.add_child(tip_2)
    mount_2 = Mount("tool2_mount")
    mount_2.mount_point = "tool2"
    mount_2.add_child(tool_2)
    robot.add_child(mount_2)

    # selecting the newly created tool to be active
    robot.kinematic_name = "tool2"

    assert robot.active_tip == tip_2


def test_has_multifinger():
    """
    Test has_multifinger()
    """
    robot = init_robot()

    assert robot.has_multifinger() is None

    # attaching tip to tool
    tip_2 = Tip("tip2")
    robot.active_tool.add_child(tip_2)
    # making the tip multifinger
    robot.active_tip.model = "Multifinger"

    assert robot.has_multifinger()


def test_get_attached_tips():
    """
    Test get_attached_tips().
    """
    robot = init_robot()

    # No tip attached.
    result = from_jsonout(robot.get_attached_tips())
    assert result["tool1"] is None

    tool1 = robot.find("tool1")
    tip1 = Tip("tip1")
    tool1.add_object_child(tip1)

    # Tip is attached.
    result = from_jsonout(robot.get_attached_tips())
    assert result["tool1"] == "tip1"

    # Add second tool.
    tool2 = Tool("tool2")

    mount2 = Mount("tool2_mount")
    mount2.mount_point = "tool2"
    mount2.add_child(tool2)
    robot.add_child(mount2)

    # Tip attached to tool1 but not to tool2.
    result = from_jsonout(robot.get_attached_tips())
    assert result["tool1"] == "tip1" and result["tool2"] is None

    tip2 = Tip("tip2")
    tool2.add_object_child(tip2)

    # Tips attached to both tools.
    result = from_jsonout(robot.get_attached_tips())
    assert result["tool1"] == "tip1" and result["tool2"] == "tip2"

    # Make sure there is nothing extra.
    assert len(result.keys()) == 2

    tip1.remove_object_from_parent()
    tip2.remove_object_from_parent()

    # No tips attached.
    result = from_jsonout(robot.get_attached_tips())
    assert result["tool1"] is None and result["tool2"] is None


def test_camera_capture_preparations():
    """
    Test camera_capture_preparations().
    :return:
    """
    robot = init_robot()

    # Add some node to represent camera. Does not have to be actual camera node.
    camera = Node("Camera1")
    Node.root.add_child(camera)

    original_pose = robot.effective_pose()

    # This should do nothing by default
    robot.camera_capture_preparations("Camera1")

    pose = robot.effective_pose()

    assert np.allclose(pose, original_pose)


def test_camera_capture_preparations_2():
    """
    Test camera_capture_preparations().
    :return:
    """
    camera_capture_position = {"x": 50, "y": 70, "z": -20}

    robot = init_robot(camera_capture_positions={"Camera1": camera_capture_position})

    # Add some node to represent camera. Does not have to be actual camera node.
    camera = Node("Camera1")
    Node.root.add_child(camera)

    # This should move robot to camera_capture_position.
    robot.camera_capture_preparations("Camera1")

    pose = robot.effective_pose()

    assert np.allclose(pose, robotmath.xyz_to_frame(
        camera_capture_position["x"], camera_capture_position["y"], camera_capture_position["z"]))

def test_smart_tips():
    """
    Test reading and writing smart tip data.
    """
    robot = init_robot(smart_tip={"mode": "simulator", "addresses": {"tool1": 8}})

    data = {"diameter": 12, "length": 8}

    robot.put_write_smart_tip_data("tool1", data)

    result = robot.get_read_smart_tip_data("tool1")
    result = from_jsonout(result)

    assert id(result) != id(data)
    assert result == data
