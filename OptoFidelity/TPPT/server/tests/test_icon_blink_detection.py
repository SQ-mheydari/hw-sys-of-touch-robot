import cv2
import numpy as np
import os

from hsup.utils import apply_roi
from tests.common import from_jsonout
from tntserver import Node
from tntserver.Nodes.NodeIcon import NodeIcon
from tntserver.Nodes.NodeIcons import NodeIcons
from tntserver.Nodes.TnT.Analyzer import Analyzer
from tntserver.Nodes.TnT.Analyzers import Analyzers
from tntserver.Nodes.TnT.Camera import Camera, per_pixel_maximum
from tntserver.Nodes.TnT.Detector import Detector
from tntserver.Nodes.TnT.Detectors import Detectors
from tntserver.Nodes.TnT.Dut import Dut
from tntserver.Nodes.TnT.Images import Images
from tntserver.drivers.cameras.camera import CameraFrame

image_path = os.path.abspath(os.path.join(os.getcwd(), 'tests', 'images'))
icon_path = os.path.abspath(os.path.join(os.getcwd(), 'data', 'icons'))
screenshots_folder = os.path.abspath(os.path.join(os.getcwd(), 'tests', 'data', 'screenshots'))


def init_all(simulator=True):
    """
    Initiate following nodes for unit test:
    - Detectors
    - Halcon detector
    - Icons
    - Dut
    - Camera
    - Images
    - Analyzers
    - BlinkDetector analyzer
    :return: Root node
    """

    root = Node('root')
    Node.root = root

    detectors = Detectors('detectors')
    root.add_child(detectors)

    halcon = Detector('halcon')
    halcon._init(driver='Halcon', simulator=simulator)
    detectors.add_child(halcon)

    icons = NodeIcons('icons')
    icons._init()
    root.add_child(icons)

    dut = Dut('dut')
    dut.tl = {"x": 20, "y": 30, "z": -10}
    dut.tr = {"x": 100, "y": 30, "z": -10}
    dut.bl = {"x": 20, "y": 130, "z": -10}
    root.add_child(dut)

    # Dut screenshot needs this
    calibration = {'intrinsic': [[6242, 0, 1295], [0, 6236, 971], [0, 0, 1]],
                   'dist_coeffs': [-1.4469, 5, 0, 0, 26],
                   'ppmm': 16}

    camera = Camera("Camera1")
    camera._init(driver="test")
    camera.calibration = calibration
    root.add_child(camera)

    images = Images('images')
    os.makedirs(screenshots_folder, exist_ok=True)
    images.image_folder_path = screenshots_folder
    root.add_child(images)

    analyzers = Analyzers('analyzers')
    root.add_child(analyzers)

    blink_detector = Analyzer('blink_detector')
    blink_detector._init(driver='BlinkDetector')
    analyzers.add_child(blink_detector)

    return root


def test_blink_detection():
    """
    Test blink detection by generating video data with a blinking icon and some random noise ontop.
    """

    init_all()

    resolution = (720, 1280, 3)
    off_image = 32 * np.ones(resolution, dtype=np.uint8)

    on_image = 32 * np.ones(resolution, dtype=np.uint8)
    rectangle_pos = 0.5 * np.array(on_image.shape[1::-1])
    rectangle_size = 100
    tl = tuple(map(int, rectangle_pos - rectangle_size))
    br = tuple(map(int, rectangle_pos + rectangle_size))
    cv2.rectangle(on_image, tl, br, (0, 200, 0), -1)

    # Setup timing information and amount of blinks (on-off cycles)
    sampling_rate = 50
    blink_frequency = 1.5  # Hz
    duration = 10.0  # seconds

    blink_period = 1.0 / blink_frequency  # seconds
    sample_spacing = 1.0 / sampling_rate

    image_list = []
    timestamps = []

    t = 0.0
    while t < duration:
        image = [off_image, on_image][round(t % blink_period / blink_period)]

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Add noise
        noise = np.random.uniform(0, 32, image.shape[0:2])
        v = np.array(np.clip(v + noise, 0, 255), dtype=np.uint8)

        final_hsv = cv2.merge((h, s, v))
        image = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)

        # cv2.imshow('frame', image)
        # cv2.waitKey(1)
        image_list.append(image)
        timestamps.append(t)
        t += sample_spacing

    blink_detector = Node.find('blink_detector')

    # Region of interest centered on icon
    roi = dict(tl=(tl[0] - 100, tl[1] - 100), br=(br[0] + 100, br[1] + 100))
    frames = [CameraFrame(apply_roi(image, roi), t) for image, t in zip(image_list, timestamps)]
    blink_frequency = blink_detector.analyze(frames=frames)["blink_frequency"]

    assert np.isclose(blink_frequency, blink_frequency, atol=0.1)

    # ROI is an empty region of the video
    roi = dict(tl=(0, 0), br=(100, 100))
    frames = [CameraFrame(apply_roi(image, roi), t) for image, t in zip(image_list, timestamps)]
    blink_frequency = blink_detector.analyze(frames=frames)["blink_frequency"]

    assert np.isclose(blink_frequency, 0.0)


def pad_frame(frame, pad=(50,), color=(0, 0, 0)):
    return np.dstack([np.pad(frame[:, :, c], pad, mode='constant', constant_values=color[c]) for c in range(3)])


def add_icon(icon_name):
    icons = Node.find('icons')

    icon = NodeIcon(icon_name)
    icons.add_child(icon)
    frame = cv2.imread(os.path.join(image_path, f'{icon_name}.png'))

    # Resize image to double
    # frame = cv2.resize(frame, (2 * frame.shape[1], 2 * frame.shape[0]))

    # Add padding
    # frame = pad_frame(frame)

    # Set the dark parts (i.e. background) to fully black
    # thresh = cv2.inRange(frame, (0, 0, 0), (50, 50, 50))
    # for c in range(3):
    #     frame[:, :, c][thresh == 255] = 0

    icon.convert(frame)


def add_icons(icon_names):
    # Add icons if they have not been taught to halcon already
    icons = Node.find('icons')
    for icon_name in icon_names:
        if not Node.find_from(icons, icon_name):
            add_icon(icon_name)


def test_blink_detection_dut():
    """
    Test dut interface for icon detection with duration and blink frequency calculation from detected region.
    """

    init_all()
    add_icons(['star_blue'])

    dut = Node.find('dut')

    icon_name = os.path.join(image_path, 'star_blue' + '.png')
    results = dut.post_find_objects(icon_name, duration=1.0)
    results = from_jsonout(results)

    # If there are multiple matches, take the one with the best score
    icon = max(results['results'], key=lambda x: x['score'])

    crop_left = icon['topLeftX_px']
    crop_upper = icon['topLeftY_px']
    crop_right = icon['bottomRightX_px']
    crop_lower = icon['bottomRightY_px']
    crop_unit = 'pix'

    results = dut.get_detect_blink_frequency(1.0, crop_left=crop_left, crop_upper=crop_upper, crop_right=crop_right,
                                             crop_lower=crop_lower, crop_unit=crop_unit)

    results = from_jsonout(results)
    freq = results['blink_frequency']
    assert np.isclose(freq, 0.0)


def test_per_pixel_maximum():
    """
    Test that the per pixel maximum gives the correct output.
    """

    # Set seed for random number generator to get the same input images.
    np.random.seed(0)

    # Generate input frames.
    frames = []
    for _ in range(10):
        img = np.array(np.random.uniform(0, 255, size=(1920, 1080, 3)), dtype=np.uint8)
        frames.append(CameraFrame(img))

    max_frame = per_pixel_maximum(frames)

    # Calculate the sum of all the pixels, should be identical for identical images.
    # Very unlikely to be identical for nonidentical images.
    val = sum(max_frame.flatten())
    assert val == 1145485814

    # Set the seed back to a random one to not affect anything else.
    np.random.seed()
