from tntserver.Nodes.TnT.Tools import Tools
from tntserver.Nodes.TnT.Tool import Tool
from tntserver.Nodes.TnT.Workspace import Workspace
from tntserver.Nodes.TnT.Robot import Robot
from tntserver.Nodes.Mount import Mount
from .test_gestures import ProgramArguments
from tntserver.Nodes.Synchro.Gestures import *
from .common import from_jsonout


def create_environment() -> Robot:
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

    robot = Robot("Robot1")

    robot._init(
        driver="golden",
        host="127.0.0.1",
        port=4001,
        model="3axis",
        simulator=True,
        speed=200,
        acceleration=400,
        force_driver="open_loop_force",
        program_arguments=ProgramArguments()
    )

    robot.add_child(mount1)
    ws.add_child(robot)

    return robot


def test_attach_detach_tool():
    robot = create_environment()

    # No tool is attached at this point.
    result = from_jsonout(robot.get_attached_tools())

    # Value should be None when there is not tool.
    assert result["tool1_mount"] is None

    robot.put_attach_tool(tool_name="tool1")

    result = from_jsonout(robot.get_attached_tools())

    assert result["tool1_mount"] == "tool1"

    robot.put_detach_tool()

    result = from_jsonout(robot.get_attached_tools())

    # Value should be None when there is not tool.
    assert result["tool1_mount"] is None
