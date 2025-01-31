from tntserver.Nodes.NodeVideoSensor import NodeVideoSensor


def test_node_init_and_functions():

    vm_node = NodeVideoSensor(name="NodeVideoSensor")
    vm_node._init(port="COM1", watchdog_enabled=False, simulation=True)

    vm_node.get_backlight_period()
    vm_node.put_set_trigger_mode_backlight()
    vm_node.init_auto_trigger()
    vm_node.backlight_period_ms()
    vm_node.reset_encoder_value()

    vm_node.set_encoder_trigger_threshold(value=123)
    assert vm_node.get_encoder_trigger_threshold() == 123

    vm_node.set_trigger_backlight_rising()
    vm_node.set_trigger_backlight_falling()
    vm_node.set_trigger_touch_start()
    vm_node.set_trigger_touch_end()
    vm_node.set_trigger_mode_frames()
    vm_node.set_trigger_mode_backlight()
    vm_node.set_trigger_mode_backlight_encoder()
    vm_node.exit_application()
    vm_node.open_camera_trigger_app()
