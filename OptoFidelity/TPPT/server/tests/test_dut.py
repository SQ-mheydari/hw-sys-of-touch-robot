from tntserver.Nodes.TnT.Dut import *
from tntserver.Nodes.TnT.Images import Images
from tntserver.Nodes.TnT.Detector import Detector
from tntserver.Nodes.TnT.Detectors import Detectors
from tntserver.Nodes.NodeIcons import NodeIcons
from tntserver.Nodes.NodeIcon import NodeIcon
from .test_camera import create_ocr_nodes, init_camera, calibrate_camera, PyfreStub, init_robot
from tests.test_tnt_robot_node import from_jsonout
from .test_icon_detection import icon_file

import cv2
import numpy as np
import pytest
import os

# -------------------------------------------------
# Pre-calculated DUTs for reference
# -------------------------------------------------
# Very basic perfectly aligned DUT
dut0 = {'tl': {'x': 20, 'y': 20, 'z': -50},
        'tr': {'x': 90, 'y': 20, 'z': -50},
        'bl': {'x': 20, 'y': 120, 'z': -50},
        'height': 100,
        'width': 70,
        'frame': [[1.0, 0.0, 0.0, 20.0],
                  [0.0, 1.0, 0.0, 20.0],
                  [0.0, 0.0, 1.0, -50.0],
                  [0.0, 0.0, 0.0, 1.0]],
        'map_to': {'x': 73.4, 'y': 107.2, 'z': -73.4, 'azimuth': -0.0, 'tilt': -0.0},
        'map_from': {'x': 64.7, 'y': -2.8000000000000007, 'z': 37.4, 'azimuth': -0.0, 'tilt': 0.0}
        }

# dut0 with little variation in z
dut1 = {'tl': {'x': 20, 'y': 20, 'z': -51},
        'tr': {'x': 90, 'y': 20, 'z': -50},
        'bl': {'x': 20, 'y': 120, 'z': -52},
        'height': 100.005,
        'width': 70.007,
        'frame': [[9.99897982e-01, 7.14104276e-05, -1.42835428e-02, 20.0],
                  [7.14141434e-05, 9.99950011e-01, 9.99847994e-03, 20.0],
                  [1.42835428e-02, -9.99847997e-03, 9.99847994e-01, -51.0],
                  [0.0, 0.0, 0.0, 1.0]],
        'map_to': {'x': 73.73501415289115, 'y': 106.9654900787808, 'z': -74.50556932614194,
                   'azimuth': -0.004092146478769556, 'tilt': -0.818414546485867},
        'map_from': {'x': 65.2416875465057, 'y': -3.179181407910281, 'z': 37.44202200282085,
                     'azimuth': -0.0040919335580471864, 'tilt': 0.81841454755039}
        }

# DUT that is rotated 35 degrees counter-clockwise
dut2 = {'tl': {'x': 30, 'y': 50, 'z': -30},
        'tr': {'x': 95.532, 'y': 4.114, 'z': -30},
        'bl': {'x': 81.622, 'y': 123.724, 'z': -30},
        'height': 90,
        'width': 80,
        'frame': [[0.81915231, 0.57357606, 0.0, 30.0],
                  [-0.57357606, 0.81915231, 0.0, 50.0],
                  [0.0, 0.0, 1.0, -30.0],
                  [0.0, 0.0, 0.0, 1.0]],
        'map_to': {'x': 123.75856566310982, 'y': 90.80111965125869, 'z': -53.400000000000006,
                   'azimuth': 34.99997366749321, 'tilt': -0.0},
        'map_from': {'x': 63.620926006027275, 'y': 4.506414776249575, 'z': 17.399999999999995,
                     'azimuth': -34.99997366749322, 'tilt': 0.0}
        }

# dut2 with z-variation
dut3 = {'tl': {'x': 30, 'y': 50, 'z': -32},
        'tr': {'x': 95.532, 'y': 4.114, 'z': -31},
        'bl': {'x': 81.622, 'y': 123.724, 'z': -30},
        'height': 90.022,
        'width': 80.006,
        'frame': [[8.19008725e-01, 5.73320781e-01, -2.29780617e-02, 30.0],
                  [-5.73644977e-01, 8.19029779e-01, -1.10300139e-02, 50.0],
                  [1.24959806e-02, 2.22149272e-02, 9.99675121e-01, -32.0],
                  [0.0, 0.0, 0.0, 1.0]],
        'map_to': {'x': 124.26632462767515, 'y': 91.04485730017994, 'z': -52.787970810005376,
                   'azimuth': 35.00792749072297, 'tilt': -0.7159855841886238},
        'map_from': {'x': 63.85775450062318, 'y': 4.927439546126112, 'z': 18.49858182827564,
                     'azimuth': -34.992709143157285, 'tilt': 1.3166618367278498}
        }

# Combining all pre-calculated DUTs into one list
duts = [dut0, dut1, dut2, dut3]


# -------------------------------------------
# Auxiliary functions
# -------------------------------------------


def decode_json_out(data):
    """
    Decode actual data from @json_out functions
    :param data: json formatted data
    :return: actual data
    """
    return json.loads(data[1].decode('utf-8'))


def dict_allclose_assert(dict0, dict1, equal=True):
    """
    Check if the numerical values are the same with numpy allclose
    for two one-dimensional dicts
    :param dict0: first dictionary for comparison
    :param dict1:  second dictionary for comparison
    :param equal: if true check that all the values are the same, if
    false check that none of the values is the same
    """
    # Go through dictionary items and compare them
    for key, value in dict0.items():
        if equal:
            assert np.allclose(value, dict1[key])
        else:  # dict values should not be equal
            assert not np.allclose(value, dict1[key])


# ------------------------------------------
# Stubs
# ------------------------------------------


class DutServer(Node):
    """
    Stub for DutServer.
    """

    def __init__(self, name):
        super().__init__(name)
        self.show_image_called = False
        self.show_positioning_image_called = False
        self.image = None

    def show_image(self, dut, image):
        """
        Stub for show_image().
        """
        self.show_image_called = True
        self.image = image

    def show_positioning_image(self, dut):
        """
        Stub for show_positioning_image().
        """
        self.show_positioning_image_called = True


# -------------------------------------------
# The actual test cases
# -------------------------------------------

def test_show_image():
    """
    Test show_image() and show_positioning_image().
    """
    # Initializing node tree for testing.
    dut = Dut("dut")

    Node.root = Node("tnt")

    dutserver = DutServer("DutServer")

    Node.root.add_child(dutserver)

    # Loading reference image.
    ref_image_path = os.path.join(os.getcwd(), 'tests', 'images', "dut_still_ref.png")
    ref_image_arr = cv2.imread(ref_image_path, cv2.IMREAD_UNCHANGED)

    dut.show_image(image=ref_image_arr)
    assert dutserver.show_image_called
    assert np.allclose(dutserver.image, ref_image_arr)

    dut.show_positioning_image()
    assert dutserver.show_positioning_image_called


def test_setters_and_getters():
    """
    Testing all the setters and getters that are linked to
    DUT positioning and, in addition, for name property
    :return:
    """
    dut = Dut("dut")
    new_touch_distance = 31.4
    assert not np.isclose(dut.touch_distance, new_touch_distance)
    dut.touch_distance = new_touch_distance
    assert np.isclose(dut.touch_distance, new_touch_distance)

    new_base_distance = 15.9
    assert not np.isclose(dut.base_distance, new_base_distance)
    dut.base_distance = new_base_distance
    assert np.isclose(dut.base_distance, new_base_distance)

    new_tl = {'x': 26.5, 'y': 35.8, 'z': -97.9}
    # The coordinates should not be the same to start with
    dict_allclose_assert(dut.tl, new_tl, equal=False)
    # Setting new coordinates
    dut.tl = new_tl
    # The coordinates should be the same
    dict_allclose_assert(dut.tl, new_tl, equal=True)

    new_tr = {'x': 32.3, 'y': 84.6, 'z': -26.4}
    # The coordinates should not be the same to start with
    dict_allclose_assert(dut.tr, new_tr, equal=False)
    # Setting new coordinates
    dut.tr = new_tr
    # The coordinates should be the same
    dict_allclose_assert(dut.tr, new_tr, equal=True)

    new_bl = {'x': 33.8, 'y': 32.7, 'z': -95.0}
    # The coordinates should not be the same to start with
    dict_allclose_assert(dut.bl, new_bl, equal=False)
    # Setting new coordinates
    dut.bl = new_bl
    # The coordinates should be the same
    dict_allclose_assert(dut.bl, new_bl, equal=True)

    new_name = 'new_dut0'
    assert dut.name != new_name
    dut.name = new_name
    assert dut.name == new_name

    new_width = 288.4
    assert not np.isclose(dut.width, new_width)
    dut.width = new_width
    assert np.isclose(dut.width, new_width)

    new_height = 197.1
    assert not np.isclose(dut.height, new_height)
    dut.height = new_height
    assert np.isclose(dut.height, new_height)


def test_put_bl_tl_tr():
    """
    Testing put functions for all the corners
    :return:
    """
    dut = Dut('dut')

    # the put functions are supposed to call save()
    # and we need this little trick to check if it happens
    was_saved = False

    def save():
        nonlocal was_saved
        was_saved = True

    # Monkey patching the real save function to our own version
    dut.save = save

    dut.put_tl(dut3['tl']['x'], dut3['tl']['y'], dut3['tl']['z'])
    assert was_saved
    was_saved = False
    dut.put_tr(dut3['tr']['x'], dut3['tr']['y'], dut3['tr']['z'])
    assert was_saved
    was_saved = False
    dut.put_bl(dut3['bl']['x'], dut3['bl']['y'], dut3['bl']['z'])
    assert was_saved

    # Checking from frame that all the values are set correctly and that
    # DUT is calculated as it should be
    assert np.allclose(dut.frame, dut3['frame'])

    # Writing again all the corners with no values should change nothing
    dut.put_tl()
    dut.put_tr()
    dut.put_bl()

    # Checking from frame that all the values are set correctly and that
    # DUT is calculated as it should be
    assert np.allclose(dut.frame, dut3['frame'])


def test_put_name():
    """
    Test put_name()
    """
    # Creating the dut
    old_name = 'old_dut0'
    dut = Dut(old_name)

    # Building necessary node tree
    parent = Node("parent")
    parent.add_child(dut)

    # the put_name function is supposed to call save()
    # and we need this little trick to check if it happens
    was_saved = False

    def save():
        nonlocal was_saved
        was_saved = True

    # Monkey patching the real save function to our own version
    dut.save = save

    new_name = 'new_name0'
    reply = decode_json_out(dut.put_name(new_name))
    assert was_saved
    assert reply == {'old_name': old_name, 'name': new_name}
    assert dut.name == new_name


def test_dut_positioning():
    """
    Test dut positioning by setting the corners and comparing the resulting dut
    properties to pre-calculated values
    """
    for comp_dut in duts:
        dut = Dut("dut")
        dut.tl, dut.tr, dut.bl = comp_dut['tl'], comp_dut['tr'], comp_dut['bl']

        assert np.isclose(dut.height, comp_dut['height'])
        assert np.isclose(dut.width, comp_dut['width'])
        assert np.allclose(dut.frame, comp_dut['frame'])


def test_get_map_to():
    """
    Test get_map_to() with pre-calculated reference values
    """
    # The arbitrary test coordinates
    coords = [53.4, 87.2, -23.4]  # x, y, z
    # Going through all the DUTs in the list
    for comp_dut in duts:
        # "Positioning" the dut
        dut = Dut("dut")
        dut.tl, dut.tr, dut.bl = comp_dut['tl'], comp_dut['tr'], comp_dut['bl']
        # Calculating the map
        map = decode_json_out(dut.get_map_to(coords[0], coords[1], coords[2]))
        # Comparing pre-calculated values with newly calculated values
        dict_allclose_assert(map, comp_dut['map_to'], equal=True)


def test_get_map_from():
    """
    Test get_map_from() with pre-calculated reference values
    """
    # The arbitrary test coordinates
    coords = [84.7, 17.2, -12.6]  # x, y, z
    # Going through all the DUTs in the list
    for comp_dut in duts:
        # "Positioning" the dut
        dut = Dut("dut")
        dut.tl, dut.tr, dut.bl = comp_dut['tl'], comp_dut['tr'], comp_dut['bl']
        # Calculating the map
        map = decode_json_out(dut.get_map_from(coords[0], coords[1], coords[2]))
        # Comparing pre-calculated values with newly calculated values
        dict_allclose_assert(map, comp_dut['map_from'], equal=True)


def test_get_position():
    """
    Test get_position() with one pre-calculated DUT (that should be enough to check
    the function)
    """
    # Creating the dut
    dut = Dut("dut")
    dut.tl, dut.tr, dut.bl = dut3['tl'], dut3['tr'], dut3['bl']
    # Comparing the pre-calculated value to the newly calculated one
    position_comp = {'x': 30.0, 'y': 50.0, 'z': -32.0}
    position = decode_json_out(dut.get_position())
    dict_allclose_assert(position_comp, position, equal=True)


def test_frame_to_orientation():
    """
    Test frame_to_orientation() with one pre-calculated DUT (that should be enough to check
    the function)
    """
    # Creating the DUT
    dut = Dut("dut")
    dut.tl, dut.tr, dut.bl = dut3['tl'], dut3['tr'], dut3['bl']
    # Calculating orientation and checking that it is correct
    orientation_comp = {'j': [-0.5736449769615818, 0.8190297791904834, -0.011030013868301403],
                        'k': [0.01249598061113347, 0.022214927246976175, 0.9996751209647958],
                        'i': [0.8190087245416333, 0.5733207808954774, -0.022978061669500068]}
    orientation = dut.frame_to_orientation_json(frame=None)
    dict_allclose_assert(orientation, orientation_comp, equal=True)


def test_frame_to_position_xyz():
    """
    Test frame_to_position() with one pre-calculated DUT (that should be enough to check
    the function)
    """
    # Creating the DUT
    dut = Dut("dut")
    dut.tl, dut.tr, dut.bl = dut3['tl'], dut3['tr'], dut3['bl']
    # Calculating orientation and checking that it is correct
    x, y, z = dut.frame_to_position_xyz(frame=None)
    assert np.isclose(x, 30.0)
    assert np.isclose(y, 50.0)
    assert np.isclose(z, -32.0)


def test_get_self():
    """
    Test get_self() with one pre-calculated DUT (that should be enough to check
    the function)
    """
    # Creating the DUT
    dut = Dut("dut0")
    dut.tl, dut.tr, dut.bl = dut0['tl'], dut0['tr'], dut0['bl']

    data = decode_json_out(dut.get_self())

    # Compare all the values that should be included with data
    assert data['kind'] == 'dut'
    assert data['name'] == 'dut0'
    assert data['type'] == 'Dut'

    properties = data['properties']
    assert properties['top_left'] == dut0['tl']
    assert properties['top_right'] == dut0['tr']
    assert properties['bottom_left'] == dut0['bl']
    assert np.isclose(properties['touch_distance'], 0)
    assert np.isclose(properties['width'], dut0['width'])
    assert np.isclose(properties['height'], dut0['height'])
    assert properties['relation'] is None
    assert np.isclose(properties['base_distance'], 10)
    assert properties['data'] == {'image_width': {'value': '0'}, 'screen_height': {'value': '0'},
                                  'image_height': {'value': '0'}, 'screen_width': {'value': '0'}}
    orientation_comp = {'k': [0.0, 0.0, 1.0], 'j': [0.0, 1.0, 0.0], 'i': [1.0, 0.0, 0.0]}
    orientation = properties['orientation']
    dict_allclose_assert(orientation, orientation_comp, equal=True)


def test_corner_properties():
    dut = Dut("dut0")
    dut.tl, dut.tr, dut.bl = dut0['tl'], dut0['tr'], dut0['bl']

    for tl in [dut.tl, dut.top_left]:
        assert np.allclose([tl["x"], tl["y"], tl["z"]], [20, 20, -50])

    for tr in [dut.tr, dut.top_right]:
        assert np.allclose([tr["x"], tr["y"], tr["z"]], [90, 20, -50])

    for bl in [dut.bl, dut.bottom_left]:
        assert np.allclose([bl["x"], bl["y"], bl["z"]], [20, 120, -50])

    for br in [dut.br, dut.bottom_right]:
        assert np.allclose([br["x"], br["y"], br["z"]], [90, 120, -50])

    position = dut.position

    assert np.allclose([position["top_left"]["x"], position["top_left"]["y"], position["top_left"]["z"]], [20, 20, -50])
    assert np.allclose([position["top_right"]["x"], position["top_right"]["y"], position["top_right"]["z"]], [90, 20, -50])
    assert np.allclose([position["bottom_left"]["x"], position["bottom_left"]["y"], position["bottom_left"]["z"]], [20, 120, -50])
    assert np.allclose([position["bottom_right"]["x"], position["bottom_right"]["y"], position["bottom_right"]["z"]], [90, 120, -50])


def test_post_screenshot():
    """
    Test post_get_screenshot() API method.
    """
    # Initializing the system to be able to take screenshot.
    Node.root = Node("tnt")
    camera = init_camera()
    calibrate_camera(camera)

    robot = init_robot(camera)

    images = Images("images")
    images.image_folder_path = os.path.join(os.getcwd(), 'tests', 'images')
    Node.root.add_child(images)

    dut = Dut("Dut1")
    dut.tl = {"x": 100, "y": 100, "z": -50}
    dut.tr = {"x": 200, "y": 100, "z": -50}
    dut.bl = {"x": 200, "y": 200, "z": -50}

    # Taking screenshot and comparing it to the reference image. The screenshot
    # is cropped to avoid extensive memory usage.
    screenshot_name = decode_json_out(dut.post_screenshot(crop_lower=300, crop_unit='pix'))
    screenshot_path = os.path.join(images.image_folder_path, screenshot_name+'.png')
    screenshot_arr = cv2.imread(screenshot_path, cv2.IMREAD_UNCHANGED)

    ref_image_path = os.path.join(images.image_folder_path, "dut_screenshot_ref.png")
    ref_image_arr = cv2.imread(ref_image_path, cv2.IMREAD_UNCHANGED)

    images.children[screenshot_name].remove()

    assert np.allclose(screenshot_arr, ref_image_arr)

    # Checking that robot has moved correctly to take the screenshot.
    position = decode_json_out(robot.get_position())

    assert np.isclose(position["position"]["x"], 173.2537)
    assert np.isclose(position["position"]["y"], 146.1940)
    assert np.isclose(position["position"]["z"], -50.0)


def test_get_still():
    """
    Test get_still() API method of dut.
    """
    # Initializing the system to be able to take screenshot.
    Node.root = Node("tnt")
    camera = init_camera()
    calibrate_camera(camera)

    robot = init_robot(camera)

    # The robot is moved to get a part of DUT to show in the image.
    robot.move_relative(150, 150, -50)

    dut = Dut("Dut1")
    dut.tl = {"x": 100, "y": 100, "z": -50}
    dut.tr = {"x": 200, "y": 100, "z": -50}
    dut.bl = {"x": 200, "y": 200, "z": -50}

    # Taking still and comparing it to the reference image.
    _, still_png = dut.get_still(filetype="png", undistorted=True)

    # Only part of the still capture is used to avoid extensive memory usage.
    still_arr = cv2.imdecode(still_png, cv2.IMREAD_UNCHANGED)[0:300]

    ref_image_path = os.path.join(os.getcwd(), 'tests', 'images', "dut_still_ref.png")
    ref_image_arr = cv2.imread(ref_image_path, cv2.IMREAD_UNCHANGED)

    assert np.allclose(still_arr, ref_image_arr)

    # Check that robot position has not changed when taking still.
    position = decode_json_out(robot.get_position())

    assert np.isclose(position["position"]["x"], 150)
    assert np.isclose(position["position"]["y"], 150)
    assert np.isclose(position["position"]["z"], -50)


def test_search_text():
    """
    Test Dut.post_search_text() API method.
    Does not test OCR itself only data processing in between Abbyy and REST API.
    Note that the reference results used here are bound to the camera stub resolution and DUT positioning with
    respect to camera.
    """
    camera = init_camera()

    calibrate_camera(camera)

    Node.root = Node("tnt")

    # Put Camera node in tree root -> camera_mount -> camera
    # and use some translation to simulate translated camera. This affects read_text() results.
    camera_mount = Node("camera_mount")
    camera_mount.frame = robotmath.xyz_to_frame(150, 150, -10)
    Node.root.add_child(camera_mount)
    camera_mount.add_child(camera)

    create_ocr_nodes(Node.root)

    images = Images("images")
    images.image_folder_path = os.path.join(os.getcwd(), 'tests', 'images')
    Node.root.add_child(images)

    existing_images = list(images.children.keys())

    dut = Dut("Dut1")
    dut.tl = {"x": 100, "y": 100, "z": -50}
    dut.tr = {"x": 200, "y": 100, "z": -50}
    dut.bl = {"x": 200, "y": 200, "z": -50}

    Node.root.add_child(dut)

    # Search all text.
    # Define cropping parameters to make sure cropping code is also executed. Use crop
    # parameters that should not affect the results.
    results_base = dut.post_search_text(".*", regexp=True, case_sensitive=False,
                                   crop_left=0, crop_right=100, crop_upper=0, crop_lower=100, crop_unit="mm")

    results_no_regexp = dut.post_search_text(".*", regexp=False, case_sensitive=False,
                                   crop_left=0, crop_right=100, crop_upper=0, crop_lower=100, crop_unit="mm")

    results_case_sensitive_false = dut.post_search_text("three", regexp=False, case_sensitive=False,
                                                        crop_left=0, crop_right=100, crop_upper=0, crop_lower=100, crop_unit="mm")

    results_case_sensitive_true = dut.post_search_text("three", regexp=False, case_sensitive=True, min_score=0.95,
                                                       crop_left=0, crop_right=100, crop_upper=0, crop_lower=100, crop_unit="mm")

    results_base = from_jsonout(results_base)
    results_no_regexp = from_jsonout(results_no_regexp)
    results_case_sensitive_false = from_jsonout(results_case_sensitive_false)
    results_case_sensitive_true = from_jsonout(results_case_sensitive_true)

    screenshot = results_base['screenshot']
    img = Node.find(screenshot)
    assert img is not None

    screenshot = results_no_regexp['screenshot']
    img = Node.find(screenshot)
    assert img is not None

    screenshot = results_case_sensitive_false['screenshot']
    img = Node.find(screenshot)
    assert img is not None

    screenshot = results_case_sensitive_true['screenshot']
    img = Node.find(screenshot)
    assert img is not None

    # Remove image created by screenshot().
    new_images = [name for name in images.children.keys() if name not in existing_images]

    for image_name in new_images:
        images.children[image_name].remove()

    assert results_base["success"]
    assert results_no_regexp["success"]
    assert results_case_sensitive_false["success"]
    assert results_case_sensitive_true["success"]

    results_base = results_base["results"]
    results_no_regexp = results_no_regexp["results"]
    results_case_sensitive_false = results_case_sensitive_false["results"]
    results_case_sensitive_true = results_case_sensitive_true["results"]

    # Going through the base test results.
    num_result_keys = 14

    result = results_base[0]
    assert np.allclose([result["topLeftX"], result["topLeftY"], result["bottomRightX"], result["bottomRightY"]],
                        [0.3333333333333333, 0.6666666666666666, 3.3333333333333335, 2.6666666666666665])
    assert np.allclose([result["centerX"], result["centerY"]], [1.8333333333333335, 1.6666666666666665])
    assert np.allclose([result["topLeftX_px"], result["topLeftY_px"], result["bottomRightX_px"], result["bottomRightY_px"]],
                       [10, 20, 100, 80])
    assert np.allclose([result["centerX_px"], result["centerY_px"]], [55, 50])
    assert result["score"] == pytest.approx(1.0)
    assert result["text"] == "One"
    assert len(result.keys()) == num_result_keys

    result = results_base[1]
    assert np.allclose([result["topLeftX"], result["topLeftY"], result["bottomRightX"], result["bottomRightY"]],
                       [5.0, 0.7333333333333333, 8.666666666666666, 2.7])
    assert np.allclose([result["centerX"], result["centerY"]], [6.833333333333333, 1.7166666666666668])
    assert np.allclose([result["topLeftX_px"], result["topLeftY_px"], result["bottomRightX_px"], result["bottomRightY_px"]],
                       [150, 22, 260, 81])
    assert np.allclose([result["centerX_px"], result["centerY_px"]], [205, 52])
    assert result["score"] == pytest.approx(1.0)
    assert result["text"] == "Two"
    assert len(result.keys()) == num_result_keys

    result = results_base[2]
    assert np.allclose([result["topLeftX"], result["topLeftY"], result["bottomRightX"], result["bottomRightY"]],
                       [0.4, 3.3333333333333335, 3.6666666666666665, 5.0])
    assert np.allclose([result["centerX"], result["centerY"]], [2.033333333333333, 4.166666666666667])
    assert np.allclose([result["topLeftX_px"], result["topLeftY_px"], result["bottomRightX_px"], result["bottomRightY_px"]],
                       [12, 100, 110, 150])
    assert np.allclose([result["centerX_px"], result["centerY_px"]], [61, 125])
    assert result["score"] == pytest.approx(1.0)
    assert result["text"] == "Three"
    assert len(result.keys()) == num_result_keys

    result = results_base[3]
    assert np.allclose([result["topLeftX"], result["topLeftY"], result["bottomRightX"], result["bottomRightY"]],
                       [4.666666666666667, 3.3333333333333335, 9.0, 5.0])
    assert np.allclose([result["centerX"], result["centerY"]], [6.833333333333334, 4.166666666666667])
    assert np.allclose([result["topLeftX_px"], result["topLeftY_px"], result["bottomRightX_px"], result["bottomRightY_px"]],
                       [140, 100, 270, 150])
    assert np.allclose([result["centerX_px"], result["centerY_px"]], [205, 125])
    assert result["score"] == pytest.approx(1.0)
    assert result["text"] == "Four"
    assert len(result.keys()) == num_result_keys

    # Going through non-regex test results.
    assert len(results_no_regexp) == 0

    # Going through case sensitive False test.
    assert len(results_case_sensitive_false) == 1
    result = results_case_sensitive_false[0]
    assert np.allclose([result["topLeftX"], result["topLeftY"], result["bottomRightX"], result["bottomRightY"]],
                       [0.4, 3.3333333333333335, 3.6666666666666665, 5.0])
    assert np.allclose([result["centerX"], result["centerY"]], [2.033333333333333, 4.166666666666667])
    assert np.allclose(
        [result["topLeftX_px"], result["topLeftY_px"], result["bottomRightX_px"], result["bottomRightY_px"]],
        [12, 100, 110, 150])
    assert np.allclose([result["centerX_px"], result["centerY_px"]], [61, 125])
    assert result["score"] == pytest.approx(1.0)
    assert result["text"] == "Three"
    assert len(result.keys()) == num_result_keys

    # Going through case sensitive True test.
    assert len(results_case_sensitive_true) == 0

    # TODO: test "paragraph" type


def test_cropping():
    """
    Test cropping in Dut.search_text() and Dut.find_objects().
    Test focuses only on verifying that if screenshot is cropped, the returned detection coordinates
    are calculated correctly.
    """
    camera = init_camera()

    calibrate_camera(camera)

    Node.root = Node("tnt")

    # Put Camera node in tree root -> camera_mount -> camera
    # and use some translation to simulate translated camera. This affects read_text() results.
    camera_mount = Node("camera_mount")
    camera_mount.frame = robotmath.xyz_to_frame(200, 300, -50)
    Node.root.add_child(camera_mount)
    camera_mount.add_child(camera)

    images = Images("images")
    images.image_folder_path = os.path.join(os.getcwd(), 'tests', 'images')
    Node.root.add_child(images)

    existing_images = list(images.children.keys())

    dut = Dut("Dut1")
    dut.tl = {"x": 100, "y": 100, "z": -50}
    dut.tr = {"x": 200, "y": 100, "z": -50}
    dut.bl = {"x": 200, "y": 200, "z": -50}

    Node.root.add_child(dut)

    detectors = Detectors("detectors")
    Node.root.add_child(detectors)

    pyfre = PyfreStub()

    detector = Detector("abbyy")
    detectors.add_child(detector)
    detector._init(driver="Abbyy", license="SWED-1000-0003-0684-9595-9238", pyfre_driver=pyfre)

    halcon = Detector(name='halcon')
    halcon._init(driver='Halcon', simulator=True)
    detectors.add_child(halcon)

    ppmm = camera.ppmm

    # Verify that detection result coordinates are correct when doing OCR or icon detection.
    # Reference coordinates are given in pixel units.
    def verify_detection(type, ref_tl_x, ref_tl_y, ref_br_x, ref_br_y, crop_left=None, crop_right=None, crop_upper=None, crop_lower=None):
        if type == "ocr":
            results = dut.post_search_text(".*", regexp=True, case_sensitive=False,
                                           crop_left=crop_left, crop_right=crop_right, crop_upper=crop_upper,
                                           crop_lower=crop_lower, crop_unit="pix")
        elif type == "icon":
            results = dut.post_find_objects(filename=icon_file, crop_left=crop_left, crop_right=crop_right,
                                            crop_upper=crop_upper, crop_lower=crop_lower, crop_unit="pix")
        else:
            assert False

        # There should be only one results in this test.
        results = from_jsonout(results)
        assert results["success"]
        results = results["results"]
        result = results[0]

        # Verify mm coordinates.
        assert np.allclose([result["topLeftX"], result["topLeftY"], result["bottomRightX"], result["bottomRightY"]],
                           [ref_tl_x / ppmm, ref_tl_y / ppmm, ref_br_x / ppmm, ref_br_y / ppmm])
        assert np.allclose([result["centerX"], result["centerY"]], [(ref_tl_x + ref_br_x) / (2 * ppmm), (ref_tl_y + ref_br_y) / (2 * ppmm)])

        # Verify pixel coordinates.
        assert np.allclose([result["topLeftX_px"], result["topLeftY_px"], result["bottomRightX_px"], result["bottomRightY_px"]],
                           [ref_tl_x, ref_tl_y, ref_br_x, ref_br_y])
        assert np.allclose([result["centerX_px"], result["centerY_px"]],
                           [(ref_tl_x + ref_br_x) / 2, (ref_tl_y + ref_br_y) / 2])

    # Pixel coordinates of OCR result corners in the image.
    tl_x = 150
    tl_y = 100
    br_x = 200
    br_y = 120
    pyfre.results = [PyfreStub.create_result(tl_x, tl_y, br_x, br_y, "Test", "Word")]

    # Simulate cropping where tl corner is cropped to pixel coordinates (20, 10) of the original image.
    # When detection is transformed to DUT context the image pixel coordinates should be also offset by (20, 10)
    # in relation to the cropped image. Note that right and lower cropping don't affect offset.
    verify_detection("ocr", tl_x + 20, tl_y + 10, br_x + 20, br_y + 10, crop_left=20, crop_right=300, crop_upper=10, crop_lower=200)

    # Pixel coordinates of icon detection result corners.
    # Note that these are defined by SimpleDetector stub class but are not directly accessable.
    tl_x = 10
    tl_y = 20
    br_x = 300
    br_y = 400

    # Simulate cropping where tl corner is cropped to pixel coordinates (5, 7) of the original image.
    # When detection is transformed to DUT context the image pixel coordinates should be also offset by (5, 7)
    # in relation to the cropped image.
    verify_detection("icon", tl_x + 5, tl_y + 7, br_x + 5, br_y + 7, crop_left=5, crop_right=300, crop_upper=7, crop_lower=400)

    new_images = [name for name in images.children.keys() if name not in existing_images]

    for image_name in new_images:
        images.children[image_name].remove()


def test_is_point_inside():
    """
    Test Dut.is_point_inside with varying parameters.
    """

    # Create DUT of width 100 and height 50.
    dut = Dut("Dut1")
    dut.tl = {"x": 100, "y": 100, "z": -50}
    dut.tr = {"x": 200, "y": 100, "z": -50}
    dut.bl = {"x": 100, "y": 150, "z": -50}

    # 0 margin.
    assert dut.is_point_inside(50, 25, 0)
    assert not dut.is_point_inside(-10, 25, 0)
    assert not dut.is_point_inside(110, 25, 0)
    assert not dut.is_point_inside(50, -10, 0)
    assert not dut.is_point_inside(50, 60, 0)

    # 20 margin with same points as previously.
    assert dut.is_point_inside(50, 25, 20)
    assert dut.is_point_inside(-10, 25, 20)
    assert dut.is_point_inside(110, 25, 20)
    assert dut.is_point_inside(50, -10, 20)
    assert dut.is_point_inside(50, 60, 20)

    # 20 margin with points that should be outside.
    assert not dut.is_point_inside(-30, 25, 20)
    assert not dut.is_point_inside(130, 25, 20)
    assert not dut.is_point_inside(50, -30, 20)
    assert not dut.is_point_inside(50, 80, 20)


def test_native_resolution_screenshot():
    """
    Test DUT screenshot mapping to native resolution if the resolution property is set.
    """
    camera = init_camera()
    calibrate_camera(camera)
    init_robot(camera)
    images = Images("images")
    images.image_folder_path = os.path.join(os.getcwd(), 'tests', 'images')
    Node.root.add_child(images)

    # Create DUT with no resolution property set.
    dut = Dut("Dut1")
    dut.tl = dict(x=0, y=0, z=0)
    dut.tr = dict(x=160, y=0, z=0)
    dut.bl = dict(x=0, y=90, z=0)
    Node.root.add_child(dut)

    # Test screenshot.
    screenshot = dut.screenshot("Camera1")
    assert screenshot.width == dut.width * camera.ppmm
    assert screenshot.height == dut.height * camera.ppmm
    assert screenshot.ppmm == camera.ppmm

    # Test get_still.
    _, png = dut.get_still()
    img = cv2.imdecode(png, cv2.IMREAD_UNCHANGED)
    height, width, _ = img.shape
    assert width == dut.width * camera.ppmm
    assert height == dut.height * camera.ppmm

    # Test record_video.
    video, _ = dut.record_video(1.0)
    height, width, _ = video[0].image.shape
    assert width == dut.width * camera.ppmm
    assert height == dut.height * camera.ppmm

    # Set DUT resolution.
    dut.resolution = (1920, 1080)

    # Test screenshot.
    screenshot = dut.screenshot("Camera1")
    assert screenshot.width == dut.resolution[0]
    assert screenshot.height == dut.resolution[1]
    assert screenshot.ppmm == dut.resolution[0] / dut.width
    assert screenshot.ppmm == dut.resolution[1] / dut.height

    # Test get_still.
    _, png = dut.get_still()
    img = cv2.imdecode(png, cv2.IMREAD_UNCHANGED)
    height, width, _ = img.shape
    assert width == dut.resolution[0]
    assert height == dut.resolution[1]

    # Test record_video.
    video, _ = dut.record_video(1.0)
    height, width, _ = video[0].image.shape
    assert width == dut.resolution[0]
    assert height == dut.resolution[1]
