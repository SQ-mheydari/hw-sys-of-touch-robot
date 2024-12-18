from tntserver.drivers.sensors.video import VideoSensor
import pytest


def test_init_and_functions(caplog):

    vm = VideoSensor(port="COM1", watchdog_enabled=False, simulation=True)

    # Make sure init doesn't produce any errors
    for record in caplog.records:
        assert record.levelname != "ERROR"

    caplog.clear()

    assert vm.go_to_home_page() == "OK \n\r\x00"
    assert vm.get_apps() != ""  # Some apps should be found
    vm.get_state()

    # Check that simulator battery is charged before proceeding with the test :)
    assert float(vm.get_battery_status()) == 100.0

    assert vm.get_backlight_period_us() == 1234.0
    assert vm.open_application("Test_app") == "OK \n\r\x00"
    assert vm.open_camera_trigger_app() == "OK \n\r\x00"
    assert vm.open_backlight_info_app() == "OK \n\r\x00"
    assert vm.exit_application() == "OK \n\r\x00"
    assert vm.reset_encoder_value() == "OK \n\r\x00"

    assert vm.set_config_param(ini_section="test", param_name="test", value=123) == "OK \n\r\x00"
    assert int(vm.get_config_param(ini_section="test", param_name="test")) == 123

    assert vm.set_encoder_trigger_threshold(value=100) == "OK \n\r\x00"
    assert vm.get_encoder_trigger_threshold() == 100

    for record in caplog.records:
        assert record.levelname != "ERROR"


def test_command_fail(caplog):
    vm = VideoSensor(port="COM1", watchdog_enabled=False, simulation=True)

    # Test that we get an error logged.
    caplog.clear()
    vm.write_to_vm("FAKE_CMD\r")
    for record in caplog.records:
        assert record.levelname == "ERROR"


def test_empty_read():
    vm = VideoSensor(port="COM1", watchdog_enabled=False, simulation=True)
    with pytest.raises(Exception):
        vm.read_from_vm()
