from tntserver.Nodes.Node import *
from . import DeletableNode


class Tool(DeletableNode):
    """
    Tool can be parented to a Mount node. Other nodes such as Tool and Tip can be parented to Tool node.
    """

    def __init__(self, name):
        super().__init__(name)

        # Can tip be attached to this tool at runtime.
        self._can_attach_tip = True

        # Can multifinger tip be attached to this tool.
        self._can_attach_multifinger_tip = False

        # Can another tool be attached to this tool at runtime.
        self._can_attach_tool = True

        self._smart = False

    @property
    def can_attach_tip(self):
        """
        Boolean value that indicates whether a tip can be attached to the Tool node.
        """
        return self._can_attach_tip

    @can_attach_tip.setter
    def can_attach_tip(self, value):
        self._can_attach_tip = value

    @property
    def can_attach_multifinger_tip(self):
        """
        Boolean value that indicates whether a multifinger tip can be attached to the Tool node.
        """
        return self._can_attach_multifinger_tip

    @can_attach_multifinger_tip.setter
    def can_attach_multifinger_tip(self, value):
        self._can_attach_multifinger_tip = value

    @property
    def can_attach_tool(self):
        """
        Boolean value that indicates whether another Tool node can be attached to the Tool node at runtime.
        """
        return self._can_attach_tool

    @can_attach_tool.setter
    def can_attach_tool(self, value):
        self._can_attach_tool = value

    @property
    def smart(self):
        """
        Boolean value to indicate if tool is a "smart tool". Smart tool name
        can be saved to a PCB on the physical tool. This is used to make sure that correct tool is used
        when robot motion is planned.
        """
        return self._smart

    @smart.setter
    def smart(self, value):
        """
        Boolean value to indicate if tool is a "smart tool". Smart tool name
        can be saved to a PCB on the physical tool. This is used to make sure that correct tool is used
        when robot motion is planned.
        """
        self._smart = value

    @property
    @private
    def mount(self):
        """
        Mount node that is the parent (direct or grand) of Tool node.
        If Mount node can't be found, property evaluates to None.
        """
        node = self

        # Traverse tree up until a Mount node is found.
        while node.object_parent:
            node = node.object_parent

            if node.__class__.__name__ == "Mount":
                return node

        return None

    @property
    @private
    def is_attached(self):
        """
        Is tool attached to Mount mode.
        Note: This is not guaranteed to return correct status in case of smart tool.
        Use Robot.get_attached_tools() instead to update smart tool status.
        """
        return self.mount is not None

    @property
    @private
    def tip(self):
        """
        Tip attached to tool or None if no tip is attached.
        """
        if len(self.object_children) == 0:
            return None

        # Tool that can have a tip attached should only have one child or none.
        first_child = list(self.object_children.values())[0]

        if first_child.__class__.__name__ != "Tip":
            return None

        return first_child

