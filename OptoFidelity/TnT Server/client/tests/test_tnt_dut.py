from tntclient.tnt_dut_client import TnTDUTClient
from tntclient.tnt_robot_client import TnTRobotClient
from tntclient.tnt_client import *
import pytest
import os
import numpy as np

def init():
    dut_name = 'dut1'
    simu_dut = 'simu_dut'
    dut_client = TnTDUTClient(dut_name)
    simu_dut_client = TnTDUTClient(simu_dut)
    robot_name = 'Robot1'
    robot_client = TnTRobotClient(robot_name)
    tntclient = TnTClient()
    nodes = {}
    nodes['dut_name'] = dut_name
    nodes['simu_dut'] = simu_dut
    nodes['dut_client'] = dut_client
    nodes['simu_dut_client'] = simu_dut_client
    nodes['robot_name'] = robot_name
    nodes['robot_client'] = robot_client
    nodes['tntclient'] = tntclient
    return nodes


def verify_attribute(obj, attr_name):
    value = getattr(obj, attr_name)
    if value is not None:
        value_new = getattr(obj, attr_name) + 3
    else:
        value_new = 5

    setattr(obj, attr_name, value_new)
    assert getattr(obj, attr_name) == value_new


def set_svg():
    nodes = init()
    svg_file = os.path.abspath(os.path.join('..', '..', '..', '..', '..', 'data', 'dut_svg', 'simu_dut.svg'))
    with open(svg_file, 'rb') as f:
        content = f.read()

    nodes['simu_dut_client'].set_svg_data(base64_data=content)


def test_dut_properties():
    """
    Test that DUT properties can be read without errors.
    Read properties as they are in server to catch errors in case they have incorrect type
    due to e.g. configuration file issues. It once happened that ruamel.yaml introduced some custom
    types for floats which caused errors in tnt client.
    """
    tntclient = TnTClient()
    dut = tntclient.dut("dut1")

    assert isinstance(dut.width, float)
    assert isinstance(dut.height, float)


def test_numerical_attributes():
    tntclient = TnTClient()
    dut = tntclient.add_dut("client_test_dut")

    attributes = ('base_distance', 'height', 'width')
    for a in attributes:
        verify_attribute(dut, a)

    dut.remove()


# Those DEPRECATED ones fail: bottom_left, top_left, top_right.
def test_positional_attributes():
    tntclient = TnTClient()
    dut = tntclient.add_dut("client_test_dut")

    attributes = ('bl', 'tl', 'tr')
    position_list = {'x': 110, 'y': 309, 'z': -20}

    for a in attributes:
        position = getattr(dut, a)
        if position is not None:
            position_new = {"x": position['x'] + 0.1,
                            "y": position['y'] + 0.3,
                            "z": position['z'] - 0.2}
        else:
            position_new = position_list

        setattr(dut, a, position_new)
        result = getattr(dut, a)
        for k in result.keys():
            assert result[k] == pytest.approx(position_new[k])

    result = dut.bottom_right
    assert result is not None

    result = dut.br
    assert result is not None

    result = dut.position
    assert result is not None

    dut.remove()


def test_dut_gestures():
    nodes = init()
    robot = nodes['robot_client']
    robot.set_speed(speed=250, acceleration=100000)

    # Robot must have tip to reach DUT surface.
    robot.change_tip("tip1", attach_manually=True)

    dut = nodes['dut_client']

    x, y, z = 10, 20, 0
    x1, y1 = 29, 52
    x2, y2 = 12, 42
    point = TnTDutPoint(x, y, z).to_dict()
    point1 = TnTDutPoint(x1, y1, z).to_dict()
    point2 = TnTDutPoint(x2, y2, z).to_dict()

    result = dut.circle(x, y, r=10)
    assert result.lower() == 'ok'
    #skip because of TOUCH5705-956
    result = dut.circle(x, y, r=15, n=2, z=15, tilt=5, azimuth=1, clockwise=True)
    assert result.lower() == 'ok'

    result = dut.compass(x, y, 0, 0, 25)
    assert result.lower() == 'ok'
    result = dut.compass(x, y, 5, 10, 25)
    assert result.lower() == 'ok'
    result = dut.compass_tap(x, y, 0, 45, 25, 10)
    assert result.lower() == 'ok'
    result = dut.compass_tap(x, y, azimuth1=-45, azimuth2=0, separation=30, tap_azimuth_step=10,
                                 z=0.7, tap_with_stationary_finger=True, clearance=0.3)
    assert result.lower() == 'ok'
    result = dut.double_tap(x, y)
    assert result.lower() == 'ok'
    result = dut.double_tap(x, y, z=0.4, tilt=12, azimuth=5, clearance=0.2, duration=0.1, interval=0.2)
    assert result.lower() == 'ok'
    result = dut.drag(x1, y1, x2, y2)
    assert result.lower() == 'ok'
    result = dut.drag(x1, y1, x2, y2, z=3, tilt1=11, tilt2=21, azimuth1=0, azimuth2=1, clearance=0.3,
                                      predelay=0.02, postdelay=0.05)
    assert result.lower() == 'ok'
    result = dut.drag_force(x1, y1, x2, y2, force=100)
    assert result.lower() == 'ok'
    result = dut.drag_force(x1, y1, x2, y2, force=100, z=1, tilt1=11, tilt2=21, azimuth1=0, azimuth2=1)
    assert result.lower() == 'ok'
    result = dut.drumroll(x, y, azimuth=0, separation=30, tap_count=3, tap_duration=1, clearance=0.8)
    assert result.lower() == 'ok'
    result = dut.fast_swipe(x1, y1, x2, y2, separation1=30, separation2=50, speed=600, acceleration=100000)
    assert result.lower() == 'ok'
    result = dut.fast_swipe(x1, y1, x2, y2, separation1=40, separation2=60, speed=800, acceleration=100000,
                                tilt1=11, tilt2=21, clearance=0.9, radius=11)
    assert result.lower() == 'ok'
    result = dut.jump(x, y)
    assert result.lower() == 'ok'
    result = dut.jump(x, y, z=0.3, jump_height=3)
    assert result.lower() == 'ok'
    result = dut.line_tap(x1, y1, x2, y2, tap_distances=[0.02, 10, 15])
    assert result.lower() == 'ok'
    result = dut.line_tap(x1, y1, x2, y2, tap_distances=[0.02, 12, 16],
                              separation=30, azimuth=6, z=2, clearance=1)
    assert result.lower() == 'ok'

    # Note: multi_tap() does not currently return 'ok'.
    result = dut.multi_tap(points=(point, point1, point2))
    result = dut.multi_tap(points=(point, point1, point2), lift=3, clearance=1)

    result = dut.pinch(x, y, d1=40, d2=70, azimuth=0)
    assert result.lower() == 'ok'
    result = dut.pinch(x, y, d1=70, d2=40, azimuth=30, z=1, clearance=0.8)
    assert result.lower() == 'ok'
    result = dut.press(x, y, force=100)
    assert result.lower() == 'ok'
    result = dut.press(x, y, force=100, z=1.2, tilt=5, azimuth=12, duration=0.2, press_depth=-1.5)
    assert result.lower() == 'ok'

    # Note: rotate() does not currently return 'ok'.
    result = dut.rotate(x, y, azimuth1=0, azimuth2=45, separation=50)
    result = dut.rotate(x, y, azimuth1=0, azimuth2=-45, separation=60, z=1, clearance=1)

    result = dut.spin_tap(x, y)
    assert result.lower() == 'ok'
    result = dut.spin_tap(x, y, z, tilt=5,  azimuth1=0, azimuth2=120, clearance=0.8, duration=0.1,
                                 spin_at_contact=False)
    assert result.lower() == 'ok'
    result = dut.swipe(x1, y1, x2, y2)

    assert result.lower() == 'ok'
    result = dut.swipe(x1, y1, x2, y2, tilt1=5, tilt2=12, azimuth1=0, azimuth2=30, clearance=0.8, radius=9)
    assert result.lower() == 'ok'
    result = dut.tap(x, y)
    assert result.lower() == 'ok'
    result = dut.tap(x1, y1, tilt=5, azimuth=5, clearance=0.8, duration=0.3)
    assert result.lower() == 'ok'
    result = dut.touch_and_drag(x, y, x1, y1, x2, y2)
    assert result.lower() == 'ok'
    result = dut.touch_and_drag(x, y, x1, y1, x2, y2, z=1, clearance=0.8)
    assert result.lower() == 'ok'
    result = dut.touch_and_tap(x, y, x+40, y+10)
    assert result.lower() == 'ok'
    result = dut.touch_and_tap(x, y, x + 40, y + 11, z=1, number_of_taps=2, tap_predelay=0.01,
                                      tap_duration=0.3, tap_interval=0.1, clearance=0.3)
    assert result.lower() == 'ok'
    result = dut.path(points=(point, point1, point2))
    assert result.lower() == 'ok'
    result = dut.path(points=(point, point1, point2), clearance=0.3)
    assert result.lower() == 'ok'

    result = dut.watchdog_tap(x, y)
    assert result.lower() == 'ok'


def test_filter_lines():
    nodes = init()
    set_svg()
    x1 = [1, 0, 0, 29]
    y1 = [0, 1, 0, 300]

    x2 = [1, 0, 0, 190]
    y2 = [0, 1, 0, 130]

    result = nodes['simu_dut_client'].filter_lines(lines=(x1, y1, x2, y2), region='analysis_region')
    assert len(result) > 0
    result = nodes['simu_dut_client'].filter_lines(lines=(x1, y1, x2, y2), region='analysis_region', margin=1)
    assert len(result) > 0


def test_filter_points():
    nodes = init()
    set_svg()
    x1, y1 = 29, 300
    x2, y2 = 190, 130
    z = -10
    points = [(x1, y1), (x2, y2)]

    nodes['simu_dut_client'].filter_points(points=points, region='analysis_region')
    nodes['simu_dut_client'].filter_points(points=points, region='analysis_region', margin=2)


def test_region_contour():
    nodes = init()
    set_svg()
    num_points = 10
    result = nodes['simu_dut_client'].region_contour(region='analysis_region', num_points=num_points)
    assert len(result) == num_points


@pytest.mark.skip(reason='Jenkins has no support for object detection')
def test_find_objects():
    pass


@pytest.mark.skip(reason='Jenkins has no support for text detection')
def test_search_text():
    pass


def test_get_robot_position_move():
    nodes = init()
    x_new, y_new, z_new = 11, 21, 25
    nodes['dut_client'].move(x_new, y_new, z_new)
    result = nodes['dut_client'].get_robot_position()
    assert result['position']['x'] == pytest.approx(x_new)
    assert result['position']['y'] == pytest.approx(y_new)
    assert result['position']['z'] == pytest.approx(z_new)



@pytest.mark.skip(reason='server hangs, TOUCH5705-594')
def test_info():
    nodes = init()
    # have to use simu_dut for communication between dut and server
    result = nodes['simu_dut_client'].info()
    assert len(result) > 0



def test_list_buttons():
    nodes = init()
    result = nodes['dut_client'].list_buttons()
    assert result is not None


def test_orientation():
    nodes = init()
    result = nodes['dut_client'].orientation
    assert len(result) > 0

    assert np.allclose(result['i'], [1, 0, 0], atol=1e-03, rtol=1e-03)
    assert np.allclose(result['j'], [0, 1, 0], atol=1e-03, rtol=1e-03)
    assert np.allclose(result['k'], [0, 0, 1], atol=1e-03, rtol=1e-03)


def test_add_remove():
    tntclient = TnTClient()
    dut = tntclient.add_dut("client_test_dut")

    assert "client_test_dut" in [dut.name for dut in tntclient.duts()]

    dut.remove()

    assert "client_test_dut" not in [dut.name for dut in tntclient.duts()]


@pytest.mark.skip(reason='server hangs, same as info TOUCH5705-594')
def test_show_image():
    nodes = init()
    image_path = os.path.abspath(os.path.join('data', 'png_test.png'))

    with open(image_path, "rb") as f:
        im_data = f.read()

    result = nodes['simu_dut_client'].show_image(im_data)
    assert result.lower() == 'ok'


def test_screenshot():
    nodes = init()
    # first go to home position, either wise, other test cases move robot to some place,
    # when call screenshot(), robot needs to move camera. If robot is at some points, it would cause exception
    # that some axis tries to move below or above limits. Homing helps.
    nodes['robot_client'].go_home()
    result = nodes['simu_dut_client'].screenshot()
    assert result is not None
    # remove generated screenshot under data/images
    screenshot_file = os.path.abspath(os.path.join('..', '..', 'installer', 'dist', 'tnt_server',
                                                   'data', 'images', result + '.npy'))
    if os.path.exists(screenshot_file):
        try:
            os.remove(screenshot_file)
        except:
            pass


def test_svg_data():
    nodes = init()
    set_svg()
    result = nodes['simu_dut_client'].svg_data()
    assert result is not None
