from . import ListingNode, json_out
from .Image import Image
import os.path
import logging
import os
import time
log = logging.getLogger(__name__)


class Images(ListingNode):
    """
    TnT™ Compatible Images resource
    Should work together with
    - TnT Sequencer
    - TnT Positioning Tool

    This node is a container for Image resources
    """

    def __init__(self, name):
        super().__init__(name, resources={"Image": Image})

        self.image_folder_path = os.path.join('data', 'images')

        # Maximum number of images to store at once.
        # In case the limit is exceeded, oldest image is removed.
        self.max_images = 10

    def _init(self, **kwargs):

        os.makedirs(self.image_folder_path, exist_ok=True)
        existing_images = []

        for filename in os.listdir(self.image_folder_path):
            if filename.endswith('.png'):
                name = filename.split('.')[0]
                existing_images.append(name)
                self._create_image_instance(name)

        # To support older systems we need to check if there are images
        # that only exist in numpy array format.
        for filename in os.listdir(self.image_folder_path):
            name = filename.split('.')[0]
            if filename.endswith('.npy') and name not in existing_images:
                self._create_image_instance(name)

    def add(self, name, type="Image", **kwargs):
        """
        Create new image resource. Only limited number of images are stored at a time.
        :param name: Name of the image. If None, then name is generated from current time.
        :param type: Not used.
        :param kwargs: Not used.
        :return: Name of the created image.
        """
        image = self._create_image_instance(name)

        return image.name

    def _get_image_time_stamps(self):
        """
        Get list of time stamps of images whose name is time stamp.
        :return: List of integers.
        """
        names = []

        for child_name in self.children:
            try:
                names.append(int(child_name))
            except ValueError:
                pass  # If name can't be cast to int then we ignore that name.

        return names

    def _create_image_instance(self, name):
        # If name is not given, generate name from current time.
        if name is None:
            time_stamps = self._get_image_time_stamps()

            # Delete oldest image if number of images exceeds maximum and the new image is named as current time.
            if len(time_stamps) >= self.max_images:
                oldest_name = min(time_stamps)
                oldest = self.children[str(oldest_name)]

                oldest.remove()

            name = str(round(time.time(), 1)).replace('.', '')

        image = Image(name)

        self.add_child(image)

        image._init_arguments = {}
        image.init()

        # self.save()
        return image
