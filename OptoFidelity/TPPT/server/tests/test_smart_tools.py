from tntserver.Nodes.TnT.Tools import SmartToolManager, Tools, Tool
import pytest


def create_manager():
    """
    Create SmartToolManager object than can be used in tests.
    """
    addresses = {"tool1_mount": 0, "tool2_mount": 1}
    manager = SmartToolManager(SmartToolManager.MODE_SIMULATOR, addresses, comm=None, ip_address=None)

    return manager


def test_smart_tool_verify_attached_tools():
    """
    Test verify_attached_tools() method.
    """

    manager = create_manager()

    tools = Tools("tools")

    # Smart tool.
    tool1 = Tool("tool1")
    tool1.smart = True
    tools.add_child(tool1)

    # Non-smart tool.
    tool2 = Tool("tool2")
    tools.add_child(tool2)

    # Write correct tool data.
    manager.write_memory_device_data("tool1_mount", {"name": "tool1"})

    # Smart tool is attached and data is correct.
    manager.verify_attached_tools({"tool1_mount": "tool1"}, tools)

    # Smart tool is connected but not attached according to TnT.
    with pytest.raises(Exception):
        manager.verify_attached_tools({"tool1_mount": None}, tools)

    # Smart tool is not connected but is attached according to TnT.
    manager.memory_managers["tool1_mount"].connected = False

    with pytest.raises(Exception):
        manager.verify_attached_tools({"tool1_mount": "tool1"}, tools)

    # Smart tool is not connected and not attached according to TnT.
    manager.verify_attached_tools({"tool1_mount": None}, tools)

    tool1.smart = False

    # Smart tool (tool1) is not connected and non-smart tool (tool2) is attached,
    manager.verify_attached_tools({"tool1_mount": "tool2"}, tools)

    # Smart tool (tool1) is connected and non-smart tool (tool2) is attached.
    manager.memory_managers["tool1_mount"].connected = True

    with pytest.raises(Exception):
        manager.verify_attached_tools({"tool1_mount": "tool2"}, tools)
