import io
import json
import logging
import math
import os.path
import base64

import cv2
import numpy as np

from PIL import Image as PILImage

from tntserver.Nodes.Node import Node, out, json_out, private
from tntserver.Nodes.TnT import DeletableNode
from tntserver.drivers.detectors.Halcon import unique_quantized_colors

log = logging.getLogger(__name__)


class NodeIcon(DeletableNode):
    """
    Icon resource holding reference to Halcon Shapemodel file and to reference PNG image.
    """

    # Do not save icons to configuration file as there can be 1000+ icons.
    transient = True

    def __init__(self, name):
        super().__init__(name)

    def _init(self, **kwargs):
        pass

    @property
    @private
    def icons(self):
        """
        Icons node that is the container of this icon.
        """
        if self.parent is None or self.parent.__class__.__name__ != "NodeIcons":
            raise Exception("NodeIcon object must be a child of NodeIcons object.")

        return self.parent

    @property
    @private
    def icon_folder_path(self):
        """
        Path to icon folder.
        """
        # This is defined by NodeIcons node which should be the parent of Icon node.
        return self.icons.icon_folder_path

    @property
    @private
    def png_path(self):
        """
        Path to the icon PNG file. The PNG file is the primary icon resource.
        """
        return os.path.join(self.icon_folder_path, '{}.png'.format(self.name))

    @property
    @private
    def path(self):
        """
        Path to the icon model file. This file is basically cached resource data and can be
        recreated from the PNG file.
        """
        return os.path.join(self.icon_folder_path, '{}.shm'.format(self.name))

    @property
    @private
    def contours_path(self):
        """
        Path to the shape model contour file. This is created from the shape model file created
        from the PNG file.
        """
        return os.path.join(self.icon_folder_path, '{}.png'.format(self.name + '_contours'))

    @property
    @private
    def metadata_path(self):
        """
        Path to the metadata file. This file can contain additional data for icons.
        """
        return os.path.join(self.icon_folder_path, '{}.json'.format(self.name))

    @json_out
    def get_self(self):
        png_path = os.path.abspath(self.png_path)
        shm_path = os.path.abspath(self.path)
        contours_path = os.path.abspath(self.contours_path)
        metadata_path = os.path.abspath(self.metadata_path)
        return {
            'name': self.name,
            'png_path': png_path,
            'shm_path': shm_path,
            'contours_path': contours_path,
            'metadata_path': metadata_path
        }

    @out("image/png")
    def get_png(self):
        """
        Get icon PNG image.
        :return: PNG image.
        """
        try:
            with open(self.png_path, 'rb') as fh:
                return fh.read(), {'Content-Disposition': 'inline; filename="{}.png"'.format(self.name)}
        except FileNotFoundError:
            raise Exception("Can't get icon PNG image: Icon data does not exist.")

    @out("image/png")
    def get_contours_png(self):
        """
        Get shapemodel contours  as PNG image
        :return: PNG image.
        """
        try:
            with open(self.contours_path, 'rb') as fh:
                return fh.read(), {'Content-Type': 'image/png',
                                   'Content-Disposition': 'inline; filename="{}.png"'.format(self.name + '_contours')}
        except FileNotFoundError:
            raise Exception("Can't get contours PNG image: Icon data does not exist.")

    def remove(self):
        """
        Remove icon resource.
        Deletes also associated icon files.
        """
        try:
            os.remove(self.png_path)
        except FileNotFoundError:
            pass  # It is ok if file does not exist in case user has deleted it.

        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass  # It is ok if file does not exist in case user has deleted it.

        try:
            os.remove(self.contours_path)
        except FileNotFoundError:
            pass  # It is ok if file does not exist in case user has deleted it.

        try:
            os.remove(self.metadata_path)
        except FileNotFoundError:
            pass  # It is ok if file does not exist in case user has deleted it.

        return super().remove()

    def convert(self, image):
        """
        Convert icon from numpy array into Halcon shape model. Icon model is stored as SHM file.
        :param image: Icon image as numpy array.
        :param camera_name: Name of the camera that is used for taking images in icon teaching.
        """

        image_height, image_width = image.shape[:2]

        log.info("Converting icon of size %d x %d to shapemodel", image_width, image_height)

        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        try:
            # TODO: Detector name could be made configurable to support multiple icon detection drivers.
            detector_node = Node.find("halcon")

            if detector_node is None:
                raise Exception("Could not find Detector. Revise server configuration.")

            driver = detector_node.driver

            driver.create_scaled_shape_model(icon_img=image, shm_path=self.path, contour_img_path=self.contours_path)

            log.info("Icon converted into {}".format(self.path))

            # Save PNG image.
            cv2.imwrite(self.png_path, image)

        except Exception as e:
            log.exception(e)

    @json_out
    def put_convert(self, image=None):
        """
        Convert given image to icon model.
        Can also re-convert existing PNG image to update the icon model.
        :param image: PNG image as base64 encoded string or bytes object. If None, then existing PNG is converted.

        Example:

        with open("icon_image.png", "rb") as file:
            data = file.read()

        icon_client.convert(data)
        """
        if image is None:
            with open(self.png_path, 'rb') as file:
                image = file.read()
        else:
            # Decode string to bytes.
            image = base64.decodebytes(image.encode("ascii"))

        # Decode from bytes to numpy array.
        image_np = cv2.imdecode(np.asarray(bytearray(image), dtype=np.uint8), cv2.IMREAD_COLOR)

        self.convert(image_np)

    @json_out
    def put_rename(self, new_name):
        """
        Renames icon.
        param new_name: a string containing the new name of the icon.
        """
        if new_name == self.name:
            return

        try:
            # Rename icon and all files related to it.
            renamed_icon = NodeIcon(new_name)
            os.rename(self.png_path, os.path.join(self.icon_folder_path, '{}.png'.format(new_name)))
            os.rename(self.path, os.path.join(self.icon_folder_path, '{}.shm'.format(new_name)))
            os.rename(self.contours_path, os.path.join(self.icon_folder_path, '{}.png'.format(new_name + '_contours')))

            if os.path.exists(self.metadata_path):
                os.rename(self.metadata_path, os.path.join(self.icon_folder_path, '{}.json'.format(new_name)))

            self.parent.add_child(renamed_icon)
            self.parent.remove_child(self)
        except Exception as ex:
            log.exception(ex)

    @json_out
    def get_extract_colors(self, num_colors=1):
        """
        Extract colors from icon that can be used in icon detection to differentiate
        icons with the same shape but different color.
        The results can be saved as color metadata for the icon.
        :param num_colors: Number of colors to extract.
        :return: List of colors as RGB tuples.
        """
        image = cv2.imread(self.png_path, cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        unique, _ = unique_quantized_colors(image, int(num_colors))

        return unique.tolist()

    def load_metadata(self):
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path) as file:
                return json.load(file)
        else:
            return {}

    def save_metadata(self, metadata):
        with open(self.metadata_path, "w") as file:
            json.dump(metadata, file, sort_keys=True, indent=4, separators=(',', ': '))

    @json_out
    def get_load_metadata(self):
        """
        Load icon metadata.
        :return: Dictionary of metadata.
        """
        return self.load_metadata()

    @json_out
    def put_save_metadata(self, metadata):
        """
        Save given metadata for icon.
        Currently supported content:
            colors: List of RGB tuples to use with quantized color detection.
            color_threshold: Value in [0, 1] used as threshold when comparing icon colors to image colors.
        Example:
            metadata = {"colors": [(200, 0, 0)], "color_threshold": 0.1}
        :param metadata: Metadata as dictionary.
        """
        self.save_metadata(metadata)
