from tntserver.Nodes.NodeIcons import NodeIcons
from tntserver.Nodes.Node import Node

import os
import cv2
import numpy as np
import json
import base64


ICON_DIRECTORY = os.path.join("tests", "data", "icons")


def create_png(name):
    img = np.ones((16, 16, 3), dtype=np.uint8) * 255

    cv2.imwrite(os.path.join(ICON_DIRECTORY, name + ".png"), img)


def test_icons():
    """
    Test all methods in NodeIcon and NodeIcons.
    Creates two icon PNG files during the test and finally removes them.
    """
    os.makedirs(ICON_DIRECTORY, exist_ok=True)

    # Make sure the directory is empty before the test.
    assert len(os.listdir(ICON_DIRECTORY)) == 0

    create_png("test_icon1")
    create_png("test_icon2")

    icons = NodeIcons("icons")

    Node.root = Node("root")
    Node.root.add_child(icons)

    icons.icon_folder_path = ICON_DIRECTORY

    icons._init()

    # Test that each image file produces an icon node.
    assert "test_icon1" in icons.children
    assert "test_icon2" in icons.children

    for icon_name in ["test_icon1", "test_icon2"]:
        icon = icons.children[icon_name]
        assert icon.name == icon_name
        assert icon.icons == icons
        assert icon.icon_folder_path == ICON_DIRECTORY
        assert icon.png_path == os.path.join(ICON_DIRECTORY, icon.name + ".png")
        assert icon.path == os.path.join(ICON_DIRECTORY, icon.name + ".shm")

        data = icon.get_self()

        assert data[0] == "application/json"

        data = json.loads(data[1].decode('utf-8'))

        assert data["name"] == icon_name
        assert data["png_path"] == os.path.abspath(os.path.join(ICON_DIRECTORY, icon.name + ".png"))
        assert data["shm_path"] == os.path.abspath(os.path.join(ICON_DIRECTORY, icon.name + ".shm"))

        png = icon.get_png()

        assert png[0] == "image/png"

        # Make sure the PNG data corresponds to white test image.
        png_array = cv2.imdecode(np.asarray(bytearray(png[1]), dtype=np.uint8), cv2.IMREAD_COLOR)
        assert np.allclose(png_array, np.ones((16, 16, 3), dtype=np.uint8) * 255)

        # Test that convert() executes without errors (does not actually convert if Halcon is not available).
        icon.convert(png_array)
        os.path.exists(icon.png_path)

        icon.put_convert(base64.encodebytes(png[1]).decode("ascii"))
        os.path.exists(icon.png_path)

        data = icon.get_extract_colors(num_colors=1)

        data = json.loads(data[1].decode('utf-8'))

        assert np.allclose(data, [255, 255, 255])

        icon.remove()

    assert len(icons.children) == 0
    assert len(os.listdir(ICON_DIRECTORY)) == 0
