from tntserver.Nodes.Node import *


class Workspace(Node):
    """
    Workspace defines a set of resources that function together.
    Usually this matches some real life robot workspace that can consist
    of the robot, tips, DUTs, physical buttons etc.
    """


def get_node_workspace(node : Node):
    """
    Get the Workspace node of given node.
    This is usually the object parent or parent up in the hierarchy.
    :param node: Node whose workspace to find.
    :return: Workspace node.
    """
    ws = node.find_object_parent_by_class_name("Workspace")

    if ws is None:
        ws = node.find_parent_by_class_name("Workspace")

    return ws
