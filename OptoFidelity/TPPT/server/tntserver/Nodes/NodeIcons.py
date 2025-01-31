import os

from tntserver.Nodes.TnT import ListingNode
from .NodeIcon import NodeIcon


class NodeIcons(ListingNode):
    """
    Icons managing: List and add icons to TnT server configuration
    """

    def __init__(self, name):
        super().__init__(name, resources={"Icon": NodeIcon})

        self.icon_folder_path = os.path.join('data', 'icons')

    def _init(self, **kwargs):
        os.makedirs(self.icon_folder_path, exist_ok=True)

        # Create icon nodes from PNG files.
        for filename in os.listdir(self.icon_folder_path):
            if not filename.endswith('_contours.png') and filename.endswith('.png'):
                self._create_icon_instance(filename.split('.')[0])

    def _create_icon_instance(self, name):
        icon = NodeIcon(name)

        self.add_child(icon)

        icon._init_arguments = {}
        icon.init()

        return icon

