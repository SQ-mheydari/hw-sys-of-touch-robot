from tntclient.tnt_image_client import TnTImageClient
from tntclient.tnt_client import TnTClient
import os
import pytest


def init_nodes():
    image_name = 'image1'
    image_client = TnTImageClient(image_name)
    tntclient = TnTClient()
    return image_name, image_client, tntclient


def define_image():
    """
    All these (need to connect to server) now are put into the method. Otherwise, jenkins would try to connect to server
    during loading test cases before server starts.
    Returns
    -------

    """
    image_name, image_client, tntclient = init_nodes()
    images = tntclient.images()
    if images is not None:
        if len(images) > 0:
            image_names = [image.name for image in images]
            if image_name not in image_names:
                tntclient.add_image(image_name)
    else:
        tntclient.add_image(image_name)


@pytest.mark.skip(reason='Jenkins has no support for object detection')
def test_find_objects():
    pass


def test_width_height():
    image_name, image_client, tntclient = init_nodes()
    define_image()
    image_client.height
    image_client.width


def test_jpeg():
    image_name, image_client, tntclient = init_nodes()
    define_image()
    file_path = os.path.dirname(os.path.abspath(__file__))
    image_file = os.path.abspath(os.path.join(file_path, 'data', 'logo.jpg'))

    with open(image_file, "rb") as file:
        data = file.read()

    image_client.set_jpeg(data)
    result = image_client.jpeg()
    assert result is not None


def test_png_filter():
    image_name, image_client, tntclient = init_nodes()
    define_image()
    file_path = os.path.dirname(os.path.abspath(__file__))
    image_file = os.path.abspath(os.path.join(file_path, 'data', 'png_test.png'))

    with open(image_file, "rb") as file:
        data = file.read()

    image_client.set_png(data)
    result = image_client.png()
    assert result is not None

    image_client.filter('ocr')


def test_remove():
    image_name, image_client, tntclient = init_nodes()
    define_image()
    image_client.remove()
    image_names_new = []

    images_new = tntclient.images()
    if images_new is not None:
        if len(images_new) > 0:
            image_names_new = [image.name for image in images_new]

    assert image_name not in image_names_new
    # add image back to enable other test cases to continue
    tntclient.add_image(image_name)


@pytest.mark.skip(reason='Jenkins has no support for text detection')
def test_search_text():
    pass
