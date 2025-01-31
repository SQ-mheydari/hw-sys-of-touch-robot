from . import ListingNode
from tntserver.Nodes.TnT.Workspace import get_node_workspace
from tntserver.Nodes.Node import *
from tntserver.Nodes.TnT.Tool import Tool
from tntserver.memorydevice import MemoryDeviceManager
import logging

log = logging.getLogger(__name__)


class Tools(ListingNode):
    """
    Container for Tool nodes.
    """
    resources = {
        'Tool': Tool
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, resources=Tools.resources, **kwargs)


class ToolChanger:
    """
    Class for managing changing of robot tools.
    A Tool node can be parented to robot Mount node to indicate that the tool is attached
    to robot.
    """

    def __init__(self, robot):
        self._robot = robot

    def attach_tool(self, tool_name: str, mount_name: str = "tool1_mount"):
        """
        Attach tool to mount that matches given kinematic name.
        :param tool_name: Name of tool node to attach.
        :param mount_name: Name of Mount node where tool is attached.
        """
        ws = get_node_workspace(self._robot)

        tool = Node.find_from(ws, tool_name)
        mount = Node.find_from(self._robot, mount_name)

        if tool is None:
            raise NodeException("Tool attach error: tool {} not found.".format(tool_name))

        current_tool = self._robot.active_tool

        if current_tool is not None:
            if current_tool.name == tool_name:
                log.warning("Tool {} already mounted.".format(tool_name))
                return

            self.detach_tool(mount_name)

        log.info("Attaching tool %s", tool_name)

        self._robot.send_message("tools", "attach_tool {} {}".format(tool_name, mount_name))

        # Connect tool node to mount node.
        mount.add_object_child(tool)

        # Save the changed parent-child relations.
        mount.save()
        tool.save()

    def detach_tool(self, mount_name: str = "tool1"):
        """
        Detach tool from mount that matches given kinematic name.
        :param mount_name: Name of Mount node where tool is currently attached.
        """
        mount = Node.find_from(self._robot, mount_name)

        tool = mount.tool

        if tool is None:
            raise NodeException("Tool detach error: no tool is currently attached.")

        log.info("Detaching tool %s", tool.name)

        # Notify simulator that tool was detached.
        self._robot.send_message("tools", "detach_tool {}".format(tool.name))

        # Detach tool by making the object parent the Tools node of the workspace.
        # Object parent can't be set to None because tip-tool relation could not be established when
        # saving to config file.
        ws = get_node_workspace(self._robot)
        tools = Node.find_from(ws, "tools")
        tools.add_object_child(tool)

        # Save changed parent-child relations.
        tool.save()
        mount.save()


class SmartToolManager(MemoryDeviceManager):
    def __init__(self, mode, addresses, comm=None, ip_address=None, id_chip_address=7, hot_changing=False):
        """
        Initialize smart tool manager.
        :param mode: Operation mode. One of MODE_NORMAL, MODE_EXTERNAL, MODE_SIMULATOR.
        :param addresses: Dictionary of mount name - motherboard address pairs e.g. {"tool1": 8}.
        :param comm: Pre-initialized OptoMotionComm object when using normal mode.
        :param ip_address: IP address of motherboard when using external mode.
        :param id_chip_address: Last digit of ID chip part number is used as its memory address.
        :param hot_changing: If true, TnT tool attach status is automatically changed to match smart tool HW status.
        """
        super().__init__(mode, addresses, comm, ip_address, id_chip_address)
        self.hot_changing = hot_changing

    def verify_attached_tools(self, attached_tools, tools_node, tool_data=None):
        """
        Verify that the tools that are attached to robot according to SW book-keeping match
        the physically attached tool. This is only possible when using smart tools that have
        capability to return stored data.
        Raises exception if verification fails.
        :param attached_tools: Dictionary of attached tools to each mount e.g. {"tool1_mount": "tool11"}.
        :param tools_node: Tools node object. Only tools under this node are considered.
        :param tool_data: Dictionary where key is mount name and value is data read via read_memory_device_data().
        This allows reading the data only once if other operations need to be performed with the data.
        """

        if tool_data is None:
            tool_data = {}

            for name in self.names:
                tool_data[name] = None
                try:
                    tool_data[name] = self.read_memory_device_data(name)
                except:
                    pass

        # Make sure that the state of currently attached tools match smart tool data.
        for mount_name, tool_name in attached_tools.items():
            if tool_name is None:
                # If tool_name is None, no tool is attached to the tool. Make sure that smart tool is not connected.
                if mount_name in self.names and tool_data[mount_name] is not None:
                    raise Exception("Smart tool is physically attached to {} but not attached "
                                    "according to TnT Server. Detach the tool and try again.".format(mount_name))
            else:
                tool = Node.find_from(tools_node, tool_name)

                if tool.smart:
                    # If smart tool is attached to the mount, compare the attributes.
                    data = tool_data[mount_name]

                    if data is None:
                        log.error("Could not read smart tool data. Tool might not be attached to the robot.")
                        raise Exception("Could not read smart tool data. Tool might not be attached to the robot.")

                    smart_tool_name = data["name"]

                    # Check that smart tool name matches current tool resource name.
                    if smart_tool_name != tool.name:
                        raise Exception("Current tool name {} does not match smart tool name {}.".
                                        format(tool.name, smart_tool_name))
                else:
                    # A non-smart tool is attached to the tool. Make sure that a smart tool is not physically
                    # attached to the tool.
                    if tool_data[mount_name] is not None:
                        raise Exception("Smart tool is physically attached to {} but another tool is attached "
                                        "according to TnT Server. Change the tool and try again.".format(mount_name))
