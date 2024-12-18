from . import ListingNode
from .PhysicalButton import PhysicalButton
from tntserver.Nodes.Node import json_out


class PhysicalButtons(ListingNode):
    """
    TnT™ Compatible Buttons resource
    Buttons is a container for Button resources
    """
    resources = {
        'PhysicalButton': PhysicalButton
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, resources=PhysicalButtons.resources, **kwargs)

    @json_out
    def get_list_buttons(self, connection_name):
        buttons = []
        for child in self.children.values():
            if child.object_parent.name == connection_name:
                buttons.append(child.name)

        return buttons
