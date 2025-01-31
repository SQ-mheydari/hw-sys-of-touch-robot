from tntclient.tnt_camera_client import TnTCameraClient
import pytest


def init_camera():
    camera_name = 'Camera1'
    camera_clt = TnTCameraClient(camera_name)
    return camera_name, camera_clt


def test_open_close():
    name, camera_client = init_camera()
    camera_client.open()
    camera_client.close()


@pytest.mark.skip(reason='Jenkins has no support for icon detection')
def test_detect_icon():
    pass


def test_focus_height():
    name, camera_client = init_camera()
    result = camera_client.focus_height()
    assert result is not None


def test_get_set_parameters():
    name, camera_client = init_camera()
    param_name1 = 'gain'
    param_name2 = 'exposure'
    result = camera_client.get_parameter(param_name1)
    assert result['status'].lower() == 'ok'
    value_new = result['params'][param_name1] + 2
    result = camera_client.set_parameter(param_name1, value_new)
    assert result['status'].lower() == 'ok'
    result = camera_client.get_parameter(param_name1)
    assert result['status'].lower() == 'ok'
    assert result['params'][param_name1] == value_new

    value1 = 7
    value2 = 0.01

    param_names = {param_name1: 0, param_name2: 0}
    result = camera_client.get_parameters(param_names)
    assert result['status'].lower() == 'ok'

    params = {param_name1: value1, param_name2: value2}
    result = camera_client.set_parameters(params)
    assert result['status'].lower() == 'ok'

    result = camera_client.get_parameters(param_names)
    assert result['status'].lower() == 'ok'
    assert result['params'][param_name1] == value1
    assert result['params'][param_name2] == value2


def test_move():
    name, camera_client = init_camera()
    x, y, z = 5, 80, -50
    camera_client.move(x=x, y=y, z=z, context='dut1')


def test_start_stop_continuous():
    name, camera_client = init_camera()
    # use default parameters
    camera_client.start_continuous()
    camera_client.stop_continuous()

    # use other than default
    camera_client.start_continuous(width=150, height=260, zoom=2, undistorted=True, exposure=10, gain=3.5, scaling=3,
                                   interpolation='linear', target_context_margin=1)
    camera_client.stop_continuous()


def test_take_still():
    name, camera_client = init_camera()
    result = camera_client.take_still()
    assert result is not None


@pytest.mark.skip(reason='Jenkins has no support for text detection')
def test_read_text():
    pass
