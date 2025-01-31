from tntserver.Nodes.TnT.Tips import SmartTipManager, Tips, Tip
import pytest


def create_manager():
    """
    Create SmartTipManager object than can be used in tests.
    """
    addresses = {"tool1": 0, "tool2": 1}
    manager = SmartTipManager(SmartTipManager.MODE_SIMULATOR, addresses, comm=None, ip_address=None)

    return manager


def test_is_device_connected():
    """
    Test is_device_connected() method.
    """
    manager = create_manager()

    assert manager.is_device_connected("tool1")
    assert manager.is_device_connected("tool2")

    with pytest.raises(Exception):
        assert manager.is_device_connected("non_existing_tool")


def test_memory_device_read_write():
    """
    Test reading and writing.
    """
    manager = create_manager()

    data = {"diameter": 10.2, "length": 5.42}

    for tool_name in ["tool1", "tool2"]:
        manager.write_memory_device_data(tool_name, data)

        result = manager.read_memory_device_data(tool_name)

        # Make sure we don't just get the same dict object.
        assert id(data) != id(result)

        assert data == result


def test_smart_tip_verify_attached_tips():
    """
    Test verify_attached_tips() method.
    """

    manager = create_manager()

    tips = Tips("tips")

    # Smart tip.
    tip1 = Tip("tip1")
    tip1.length = 10
    tip1.diameter = 12
    tip1.smart = True
    tips.add_child(tip1)

    # Non-smart tip.
    tip2 = Tip("tip2")
    tip2.length = 10
    tip2.diameter = 12
    tips.add_child(tip2)

    # Write correct tip data.
    manager.write_memory_device_data("tool1", {"name": "tip1", "properties": {"length": tip1.length, "diameter": tip1.diameter}})

    # Smart tip is attached and data is correct.
    manager.verify_attached_tips({"tool1": "tip1"}, tips)

    # Smart tip is attached and data is not correct.
    tip1.length = 20

    with pytest.raises(Exception):
        manager.verify_attached_tips({"tool1": "tip1"}, tips)

    tip1.length = 10

    # Smart tip is connected but not attached according to TnT.
    with pytest.raises(Exception):
        manager.verify_attached_tips({"tool1": None}, tips)

    # Smart tip is not connected but is attached according to TnT.
    manager.memory_managers["tool1"].connected = False

    with pytest.raises(Exception):
        manager.verify_attached_tips({"tool1": "tip1"}, tips)

    # Smart tip is not connected and not attached according to TnT.
    manager.verify_attached_tips({"tool1": None}, tips)

    tip1.smart = False

    # Smart tip (tip1) is not connected and non-smart tip (tip2) is attached,
    manager.verify_attached_tips({"tool1": "tip2"}, tips)

    # Smart tip (tip1) is connected and non-smart tip (tip2) is attached.
    manager.memory_managers["tool1"].connected = True

    with pytest.raises(Exception):
        manager.verify_attached_tips({"tool1": "tip2"}, tips)
