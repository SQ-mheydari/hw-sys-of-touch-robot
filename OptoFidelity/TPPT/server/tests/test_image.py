from tntserver.Nodes.TnT.Image import *
from tntserver.Nodes.TnT.Images import Images
from tntserver.Nodes.TnT.Dut import Dut
from pytest import raises, approx

def test_convert_crop_to_pixels():
    """
    Test function convert_crop_to_pixels() with varying parameter combinations.
    """
    width = 100
    height = 60

    ppmm = 4

    # Test some erroneous parameters.
    with raises(Exception):
        convert_crop_to_pixels(None, None, None, None, width, height, ppmm, "foo")

    with raises(Exception):
        convert_crop_to_pixels(None, None, None, None, width, height, ppmm, None)

    with raises(Exception):
        convert_crop_to_pixels(20, 0, 10, height, width, height, ppmm, "pix")

    with raises(Exception):
        convert_crop_to_pixels(0, 30, width, 20, width, height, ppmm, "pix")

    # Test cropping with default parameters.
    for unit in ["pix", "per", "mm"]:
        left, upper, right, lower = convert_crop_to_pixels(None, None, None, None, width, height, ppmm, unit)
        assert left == approx(0) and upper == approx(0) and right == approx(width) and lower == approx(height)

    # Test cropping with explicit parameters.
    left, upper, right, lower = convert_crop_to_pixels(10, 20, 30, 40, width, height, ppmm, "pix")
    assert left == approx(10) and upper == approx(20) and right == approx(30) and lower == approx(40)

    left, upper, right, lower = convert_crop_to_pixels(0.1, 0.2, 0.9, 0.6, width, height, ppmm, "per")
    assert left == approx(10) and upper == approx(12) and right == approx(90) and lower == approx(36)

    left, upper, right, lower = convert_crop_to_pixels(5, 3, 20, 12, width, height, ppmm, "mm")
    assert left == approx(5 * ppmm) and upper == approx(3 * ppmm) and right == approx(20 * ppmm) and lower == approx(12 * ppmm)

    # Test cropping with parameters that will be clamped.
    left, upper, right, lower = convert_crop_to_pixels(-5, -10, 120, 80, width, height, ppmm, "pix")
    assert left == approx(0) and upper == approx(0) and right == approx(width) and lower == approx(height)


def test_crop():
    """
    Test Image.post_crop() in a case where image is a child of DUT node.
    In this case the cropping should update image.frame to maintain transformation from
    pixel coordinates to DUT coordinates.
    """
    dut = Dut("dut")
    dut.tl = {"x": 100, "y": 100, "z": -50}
    dut.tr = {"x": 200, "y": 100, "z": -50}
    dut.bl = {"x": 200, "y": 200, "z": -50}

    image = Image("test_image")

    # Image must be child of DUT to be able to transform points.
    dut.add_child(image)

    width = 200
    height = 100

    image.data = np.ones((height, width, 3), dtype=np.uint8)

    # This test only uses pixel cropping units as test_convert_crop_to_pixels() already tests other units.

    # Crop with default parameters it no cropping should be done.
    image.post_crop(None, None, None, None, "pix")
    assert image.width == approx(width) and image.height == approx(height)
    assert np.allclose(image.frame, robotmath.identity_frame())

    # Make sure origin maps to origin at this point.
    assert np.allclose(image.transform_point(0, 0), (0, 0))
    assert np.allclose(image.transform_point(10, 20), (10, 20))

    # Crop so that image origin is preserved. Should not affect frame but affects image size.
    image.post_crop(None, None, 100, 50, "pix")
    assert image.width == approx(100) and image.height == approx(50)
    assert np.allclose(image.frame, robotmath.identity_frame())

    # Check that new image size is preserved.
    image.post_crop(None, None, None, None, "pix")
    assert image.width == approx(100) and image.height == approx(50)

    # Crop so that new origin becomes (10, 20) in pixel coordinates. This also reduces image size.
    image.post_crop(10, 20, None, None, "pix")
    assert image.width == approx(90) and image.height == approx(30)

    # Point (0, 0) in cropped image should now map to (10, 20) that was the position in the uncropped image.
    assert np.allclose(image.transform_point(0, 0), (10, 20))

    # Test also how local point other than origin maps.
    assert np.allclose(image.transform_point(8, 9), (18, 29))

    # Crop again so that new origin becomes (5, 7) in pixel coordinates in relation to previous cropping.
    image.post_crop(5, 7, None, None, "pix")
    assert image.width == approx(90-5) and image.height == approx(30-7)

    # Point (0, 0) in cropped image should now map to (10 + 5, 20 + 7) that was the position in the uncropped image.
    assert np.allclose(image.transform_point(0, 0), (15, 27))


def test_save_image():
    """
    Test saving image to file.
    """
    images = Images("images")
    images.image_folder_path = os.path.join(os.getcwd(), 'tests', 'images')

    image_name = images.add("test_image")

    image = images.children[image_name]

    image.data = np.ones((100, 100, 3), dtype=np.uint8)

    assert not os.path.exists(os.path.join(images.image_folder_path, image.name))

    image.post_save_image()

    assert os.path.exists(os.path.join(images.image_folder_path, image.name + ".png"))

    image.remove()


def test_convert_to_gray_scale():
    """
    Test converting image to grayscale.
    Compares to reference image.
    """
    image = Image("test")
    image.data = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo.jpg'))

    image.post_convert_to_gray_scale()

    # Save reference data.
    #cv2.imwrite(os.path.join(os.getcwd(), 'tests', 'images', 'logo_gray.png'), image.data)

    reference = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo_gray.png'), cv2.IMREAD_GRAYSCALE)

    assert np.allclose(image.data, reference)


def test_invert():
    """
    Test inverting image colors.
    Compares to reference image.
    """
    image = Image("test")
    image.data = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo.jpg'))

    image.post_invert()

    # Save reference data.
    # cv2.imwrite(os.path.join(os.getcwd(), 'tests', 'images', 'logo_inv.png'), image.data)

    reference = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo_inv.png'))

    assert np.allclose(image.data, reference)


def test_crop_image_file():
    """
    Test cropping image that is loaded from file.
    Compares to reference image.
    """
    image = Image("test")
    image.data = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo.jpg'))

    image.crop(crop_left=80, crop_upper=10, crop_right=150, crop_lower=60, crop_unit="pix")

    # Save reference data.
    # cv2.imwrite(os.path.join(os.getcwd(), 'tests', 'images', 'logo_crop.png'), image.data)

    reference = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo_crop.png'))

    assert np.allclose(image.data, reference)

def test_resize():
    """
    Tests resizing the image.
    Compares to given values.
    """
    image = Image("test")
    image.data = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo.jpg'))
    height = 80
    width = 150
    image.post_resize(width=width, height=height)
    assert image.width == width
    assert image.height == height

    image.data = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo.jpg'))
    aspect_ratio = image.width / image.height
    height = max(1, int(round(150 / aspect_ratio)))
    width = 150
    image.post_resize(width=width)
    assert image.width == width
    assert image.height == height

    image.data = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo.jpg'))
    aspect_ratio = image.width / image.height
    height = 80
    width = max(1, int(round(80 * aspect_ratio)))
    image.post_resize(height=height)
    assert image.width == width
    assert image.height == height

    image.data = cv2.imread(os.path.join(os.getcwd(), 'tests', 'images', 'logo.jpg'))
    factor = 0.5
    height = max(1, int(round(image.height * factor)))
    width = max(1, int(round(image.width * factor)))
    image.post_resize(factor=factor)
    assert image.width == width
    assert image.height == height

