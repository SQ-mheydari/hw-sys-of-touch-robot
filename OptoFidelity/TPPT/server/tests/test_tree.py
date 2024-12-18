from tntserver.Tree import *
import pytest


def test_get_node_path():
    paths = {
        "tnt",
        "tnt.workspaces",
        "tnt.workspaces.ws"
    }

    # Test trivial matches.
    assert get_node_path("tnt", paths) == "tnt"
    assert get_node_path("tnt.workspaces", paths) == "tnt.workspaces"
    assert get_node_path("tnt.workspaces.ws", paths) == "tnt.workspaces.ws"

    # Test legacy support.
    assert get_node_path("ws", paths) == "tnt.workspaces.ws"
    assert get_node_path("workspaces.ws", paths) == "tnt.workspaces.ws"

    with pytest.raises(Exception):
        get_node_path("ws2", paths)


def test_get_live_node_full_parent_name():
    root = Node("root")
    Node.root = root

    workspaces = Node("workspaces")
    root.add_child(workspaces)

    ws = Node("ws")
    workspaces.add_child(ws)

    robot = Node("robot")
    ws.add_child(robot)

    camera = Node("camera")
    ws.add_child(camera)

    tool = Node("tool")
    robot.add_child(tool)

    assert get_live_node_full_parent_name(root) is None
    assert get_live_node_full_parent_name(workspaces) == "root"
    assert get_live_node_full_parent_name(ws) == "root.workspaces"
    assert get_live_node_full_parent_name(robot) == "root.workspaces.ws"
    assert get_live_node_full_parent_name(camera) == "root.workspaces.ws"
    assert get_live_node_full_parent_name(tool) == "root.workspaces.ws.robot"


def test_get_live_node_full_object_parent_name():
    root = Node("root")
    Node.root = root

    workspaces = Node("workspaces")
    root.add_object_child(workspaces)

    ws = Node("ws")
    workspaces.add_object_child(ws)

    robot = Node("robot")
    ws.add_object_child(robot)

    camera = Node("camera")
    ws.add_object_child(camera)

    tool = Node("tool")
    robot.add_object_child(tool)

    assert get_live_node_full_object_parent_name(root) is None
    assert get_live_node_full_object_parent_name(workspaces) == "root"
    assert get_live_node_full_object_parent_name(ws) == "root.workspaces"
    assert get_live_node_full_object_parent_name(robot) == "root.workspaces.ws"
    assert get_live_node_full_object_parent_name(camera) == "root.workspaces.ws"
    assert get_live_node_full_object_parent_name(tool) == "root.workspaces.ws.robot"
