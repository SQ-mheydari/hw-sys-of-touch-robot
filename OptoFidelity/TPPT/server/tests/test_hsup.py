import logging
import time
import types

import cv2
import diskcache
import numpy as np
import pytest
import sys

from tntserver.Nodes.Node import Node
from tntserver.Nodes.TnT.Analyzer import Analyzer
from tntserver.Nodes.TnT.Analyzers import Analyzers
from tntserver.Nodes.TnT.Camera import Camera
from tntserver.Nodes.TnT.Robot import Robot
from tntserver.Nodes.NodeTriggerSensor import NodeTriggerSensor
from tests.test_gestures import ProgramArguments

# replace check_license_feature method for testing purposes
import tntserver.license
def do_not_check_license_feature(*args, **kwargs):
    return True
tntserver.license.check_license_feature = do_not_check_license_feature
# replacing check_license_feature has to be before Hsup import
from tntserver.drivers.analyzers.Hsup import Hsup
from tntserver.drivers.cameras.camera_simulator import Yasler_image_stub

IMAGES_COUNT = 0
ROOT_NODE = None
IMAGE_HEIGHT = 100
IMAGE_WIDTH = 100
TEST_TIMEOUT = 60.0  # Total time spent in analysis and storing results cannot be bigger than this

# HSUP tests cause seg fault with Python 3.7 on macos build machine.
if not sys.platform.startswith("win"):
    pytest.skip("skipping windows-only tests", allow_module_level=True)


@pytest.fixture(scope="session")
def nodes():
    """
    Initialize nodes for testing
    :return:
    """
    global IMAGES_COUNT
    global ROOT_NODE
    IMAGES_COUNT = 0
    ROOT_NODE = Node('root')
    Node.root = ROOT_NODE

    robot = Robot("Robot1")
    robot._init(
        driver="golden",
        host="127.0.0.1",
        port=4001,
        model="3axis",
        simulator=True,
        speed=200,
        acceleration=400,
        program_arguments=ProgramArguments()
    )

    hsup_camera_simulator = Camera('hsup_camera')
    hsup_camera_simulator._init(driver='simulator')

    ROOT_NODE.add_child(hsup_camera_simulator)

    watchdog_analyzer = Analyzer(name='watchdog')
    watchdog_analyzer._init(driver='Hsup', camera='hsup_camera', analysis='Watchdog')

    analyzers = Analyzers(name='analyzers')
    analyzers.add_child(watchdog_analyzer)

    ROOT_NODE.add_child(analyzers)

    triggersensor = MockTriggerSensor(name="triggersensor")
    triggersensor._init(driver=StubTriggerSensorDriver())
    ROOT_NODE.add_child(triggersensor)
    return ROOT_NODE


class MockTriggerSensor(NodeTriggerSensor):

    def __init__(self, name):
        super().__init__(name)
        self._bl_period = None

    def _init(self, driver, backlight_period=5.0):
        self._driver = driver
        self._bl_period = backlight_period

    def set_trigger_mode_backlight_encoder(self):
        pass

    def open_camera_trigger_app(self):
        pass

    def exit_application(self):
        pass

    def set_trigger_backlight_rising(self):
        pass

    def set_trigger_backlight_falling(self):
        pass

    @property
    def bl_period(self):
        return self._bl_period

    @bl_period.setter
    def bl_period(self, value):
        self._bl_period = value

    def backlight_period_ms(self):
        return self._bl_period


class StubTriggerSensorDriver:

    def __init__(self):
        pass

    def reset_encoder_value(self):
        pass

    def set_trigger_touch_end(self):
        pass

    def set_trigger_touch_start(self):
        pass


def show_image(image):
    cv2.namedWindow("", cv2.WINDOW_NORMAL)
    cv2.imshow("", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def generate_image(self):
    global IMAGES_COUNT
    analysis_type = self.analysis
    img_shape = (IMAGE_HEIGHT, IMAGE_WIDTH)
    if analysis_type == 'Watchdog':
        img = np.zeros(img_shape)
        if IMAGES_COUNT % 50 == 0 and IMAGES_COUNT != 0:
            img[40:50, 40:50] = 255
    elif analysis_type == 'SPA':
        img = np.zeros(img_shape)
        if IMAGES_COUNT % 9 == 0:
            img[:, :] = 255
    else:
        img = np.zeros(img_shape)
    IMAGES_COUNT = IMAGES_COUNT + 1
    return img


def capture_thread_runner(self):
    """
    Called by start_continuous() to capture image and call callback
    References: none
    """
    while self._is_grabbing:
        img = self._capture_image()
        image = Yasler_image_stub(img, timestamp=time.time(), exposure=30, offset_x=0, offset_y=0)
        try:
            self._callback(image, None)
        except Exception as e:
            logging.error('Call back fails: ' + str(e))
        time.sleep(1/self.frame_rate)


def wait_for_analysis_to_finish(hsup):
    t_0 = time.time()
    while t_0 + TEST_TIMEOUT > time.time():
        status = hsup.status()
        if status['status_analysis'] == 'stopped' and status['status_results_storage'] == 'stopped':
            break
        time.sleep(0.5)
    return status


@pytest.mark.parametrize('analysis_type', ('Watchdog', 'SPA'))
def test_analysis(nodes, analysis_type):
    """
    There is modification in simulator camera which takes frame_rate into account, uses timeout 1/frame_rate
    """
    global IMAGES_COUNT
    IMAGES_COUNT = 0
    FRAMERATE = 100
    TIMEOUT = 3
    parameters = {'camera':
                      {'image_height': IMAGE_HEIGHT, 'image_width': IMAGE_WIDTH,
                       'exposure': None, 'frame_rate': FRAMERATE},
                  'analysis':
                      {'analysis_type': analysis_type, 'event_distance_ms': 1.0, 'threshold': 0.1,
                       'timeout': TIMEOUT, 'camera_trigger_mode': 'Manual', 'display_backlight_sync': False}}
    hsup = Hsup(camera='hsup_camera', analysis=analysis_type)
    hsup._camera.analysis = analysis_type
    # Line below is to connect generate_image method to hsup._camera object instance
    # otherwise it wouldn't get self as the first argument
    hsup._camera._capture_image = types.MethodType(generate_image, hsup._camera)
    hsup._camera.capture_thread_runner = types.MethodType(capture_thread_runner, hsup._camera)
    hsup.start_measurement(params=parameters)
    status = wait_for_analysis_to_finish(hsup)
    results = hsup.results()
    # images_count might be bigger by 1 than status['images_total'] because
    # camera_simulator.stop_continuous changes _callback method and it can happen
    # between image capture and passing it to the _callback
    assert IMAGES_COUNT == status['images_total'] or IMAGES_COUNT - 1 == status['images_total']
    logging.debug("Generated {} images, results has {} images".format(IMAGES_COUNT, status['images_total']))
    # Verify analysis specific statistics
    # Those depend very much on the machine running the test and CPU cycles available, so I'll make them
    # very loose requirement here to minimize issues with Jenkins builds
    assert results['status'] == 'OK'
    if analysis_type == 'SPA':
        assert 0.01 * FRAMERATE < results['results']['statistics']['average'] < 0.15 * FRAMERATE
    elif analysis_type == 'Watchdog':
        assert 50 / FRAMERATE < results['results']['statistics']['delay_change_start'] < TIMEOUT * 1.1
        assert 50 / FRAMERATE < results['results']['statistics']['delay_change_finished'] < TIMEOUT * 1.1
    # verify that raw and analysed images are stored
    storage_directory = hsup._storage_directory
    analysed_images_directory = hsup._analysed_images_directory
    storage_dc = diskcache.Cache(directory=storage_directory)
    analysed_images_dc = diskcache.Cache(directory=analysed_images_directory)
    assert len(storage_dc) == status['images_total']
    assert len(analysed_images_dc) == status['images_total']


@pytest.mark.parametrize('analysis_type', ('Watchdog', 'SPA', 'P2I'))
def test_analysis_negative_timeout(nodes, analysis_type):
    parameters = {'camera':
                      {'image_height': IMAGE_HEIGHT, 'image_width': IMAGE_WIDTH, 'exposure': None, 'frame_rate': 100},
                  'analysis':
                      {'analysis_type': analysis_type, 'event_distance_ms': 5.0, 'threshold': 0.1,
                       'timeout': -1.0, 'camera_trigger_mode': 'Manual', 'display_backlight_sync': False}}
    hsup = Hsup(camera='hsup_camera', analysis=analysis_type)
    hsup._camera.analysis = analysis_type
    # Line below is to connect generate_image method to hsup._camera object instance
    # otherwise it wouldn't get self as the first argument
    hsup._camera._capture_image = types.MethodType(generate_image, hsup._camera)
    hsup._camera.capture_thread_runner = types.MethodType(capture_thread_runner, hsup._camera)
    with pytest.raises(Exception) as excinfo:
        hsup.start_measurement(params=parameters)
    assert "Timeout must be higher than zero." in str(excinfo.value)


@pytest.mark.parametrize('analysis_type', ('Watchdog', 'SPA', 'P2I'))
def test_analysis_no_parameters(nodes, analysis_type):
    parameters = {}
    hsup = Hsup(camera='hsup_camera', analysis=analysis_type)
    hsup._camera.analysis = analysis_type
    # Line below is to connect generate_image method to hsup._camera object instance
    # otherwise it wouldn't get self as the first argument
    hsup._camera._capture_image = types.MethodType(generate_image, hsup._camera)
    hsup._camera.capture_thread_runner = types.MethodType(capture_thread_runner, hsup._camera)
    with pytest.raises(Exception) as excinfo:
        hsup.start_measurement(params=parameters)
    assert "No measurement parameters given. Aborting measurement." in str(excinfo.value)


@pytest.mark.parametrize('analysis_type', ('Watchdog', 'SPA', 'P2I'))
@pytest.mark.parametrize('bl_sync', [False, True])
def test_triggersensor(nodes, analysis_type, bl_sync):
    parameters = {'camera':
                      {'image_height': IMAGE_HEIGHT, 'image_width': IMAGE_WIDTH, 'exposure': None, 'frame_rate': 100},
                  'analysis':
                      {'analysis_type': analysis_type, 'event_distance_ms': 5.0, 'threshold': 0.1,
                       'timeout': 1.0, 'camera_trigger_mode': 'Automatic', 'display_backlight_sync': bl_sync}}

    hsup = Hsup(camera='hsup_camera', analysis=analysis_type, triggersensor='triggersensor', videosensor='triggersensor')
    hsup._camera.analysis = analysis_type
    # Line below is to connect generate_image method to hsup._camera object instance
    # otherwise it wouldn't get self as the first argument
    hsup._camera._capture_image = types.MethodType(generate_image, hsup._camera)
    hsup._camera.capture_thread_runner = types.MethodType(capture_thread_runner, hsup._camera)
    hsup.start_measurement(params=parameters)


@pytest.mark.parametrize('analysis_type', ('Watchdog', 'SPA', 'P2I'))
def test_too_slow_camera(nodes, analysis_type):
    global ROOT_NODE

    parameters = {'camera':
                      {'image_height': IMAGE_HEIGHT, 'image_width': IMAGE_WIDTH, 'exposure': None, 'frame_rate': 100},
                  'analysis':
                      {'analysis_type': analysis_type, 'event_distance_ms': 5.0, 'threshold': 0.1,
                       'timeout': 1.0, 'camera_trigger_mode': 'Automatic', 'display_backlight_sync': True}}

    hsup = Hsup(camera='hsup_camera', analysis=analysis_type, triggersensor='triggersensor', videosensor='triggersensor')
    hsup._camera.analysis = analysis_type
    # Line below is to connect generate_image method to hsup._camera object instance
    # otherwise it wouldn't get self as the first argument
    hsup._camera._capture_image = types.MethodType(generate_image, hsup._camera)
    hsup._camera.capture_thread_runner = types.MethodType(capture_thread_runner, hsup._camera)

    # Set backlight period to a fast value (1 ms = 1000 Hz.)
    triggersensor = ROOT_NODE.find("triggersensor")
    triggersensor.bl_period = 1

    with pytest.raises(Exception) as excinfo:
        hsup.start_measurement(params=parameters)

    assert "is too low at current settings to capture" in str(excinfo.value)


@pytest.mark.parametrize('analysis_type', ('Watchdog', 'SPA', 'P2I'))
@pytest.mark.parametrize('bl_value', [-1.0, 0])
def test_bl_period_fail(nodes, analysis_type, bl_value):
    global ROOT_NODE

    parameters = {'camera':
                      {'image_height': IMAGE_HEIGHT, 'image_width': IMAGE_WIDTH, 'exposure': None, 'frame_rate': 100},
                  'analysis':
                      {'analysis_type': analysis_type, 'event_distance_ms': 5.0, 'threshold': 0.1,
                       'timeout': 1.0, 'camera_trigger_mode': 'Automatic', 'display_backlight_sync': True}}

    hsup = Hsup(camera='hsup_camera', analysis=analysis_type, triggersensor='triggersensor', videosensor='triggersensor')
    hsup._camera.analysis = analysis_type
    # Line below is to connect generate_image method to hsup._camera object instance
    # otherwise it wouldn't get self as the first argument
    hsup._camera._capture_image = types.MethodType(generate_image, hsup._camera)
    hsup._camera.capture_thread_runner = types.MethodType(capture_thread_runner, hsup._camera)

    triggersensor = ROOT_NODE.find("triggersensor")
    triggersensor.bl_period = bl_value

    with pytest.raises(Exception):
        hsup.start_measurement(params=parameters)
