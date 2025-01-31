import logging
from tntserver.Nodes.Node import *
from . import DeletableNode
from . import robotmath
from tntserver.Nodes.TnT import Tool

log = logging.getLogger(__name__)


class Tip(DeletableNode):
    """
    TnT™ Compatible tip resource
    Tip can be parented to a Tool node.
    """

    def __init__(self, name, type="Tip", diameter=9, length=16):
        super().__init__(name)
        self._kind = "tip"
        self._type = "Tip"
        self._model = "Standard"
        self._diameter = diameter
        self._length = length
        self._offset_x = 0.0
        self._offset_y = 0.0

        # Position of voice coils when picking and dropping the tip.
        self._voice_coil_position = None

        # Separation of two-finger to pick multifinger.
        self._separation = None

        # Is grippable by moving the two fingers toward each other with the separation axis.
        self._grippable = False

        # Number of tips in multifinger.
        self._num_tips = None

        # Distance of adjacent tip axes in multifinger.
        self._tip_distance = None

        # Distance from middle of multifinger tool to the first finger.
        self._first_finger_offset = None

        # slot_in = pose in tip rack
        # slot_out = pose when moving out of the tip rack
        self._slot_in = None
        self._slot_out = None

        # Smart tip properties are validated against data stored in PCB memory.
        self._smart = False

    def _init(self, **kwargs):
        # Simulator needs to know tip slot-in position to make tip initially appear in correct location.
        if self._slot_in:
            x, y, z = robotmath.frame_to_xyz(np.matrix(self._slot_in))
            msg = "set_tip_slot_in {} {} {} {}".format(self.name, x, y, z)
            self.send_message(channel="tips", message=msg)

        # Check if tip is attached to tool and robot and send message for simulator to visualize correct tip.
        if type(self.object_parent) is Tool.Tool:
            robot = self.find_object_parent_by_class_name("Robot")
            self.send_message(channel="tips", message="attach_tip {} {}".format(self.name, self.object_parent.name))

    def update_frame(self):
        """
        Update tip node frame to reflect current tip properties.
        """
        x = self.offset_x
        y = self.offset_y

        if self.is_multifinger and self.separation is not None and self.first_finger_offset is not None:
            # x is the x-coordinate of tip frame and corresponds to the first effector in multifinger tip.
            x = -self.separation / 2 + self.first_finger_offset

        self.frame = robotmath.xyz_to_frame(x, y, self.length)

    @property
    @private
    def dimension(self):
        """
        TnT client support.
        TODO: Remove if removed from client.
        """
        x, y, z = robotmath.frame_to_xyz(self.frame)
        return {"x": x, "y": y, "z": z}

    @property
    @private
    def is_multifinger(self):
        """
        Is tip multifinger.
        """
        return self.model == "Multifinger"

    @property
    def grippable(self):
        """
        Is tip grippable with separation axis.
        """
        return self._grippable

    @grippable.setter
    def grippable(self, value):
        # Value may come in as a JSON serialized string because put_properties doesn't serialize strings to objects
        if isinstance(value, str):
           value = value == 'true'

        self._grippable = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def model(self):
        """
        Tip model ("Standard", "Multifinger").
        """
        return self._model

    @model.setter
    def model(self, value):
        self._model = value
        self.update_frame()

    @property
    def length(self):
        """
        Length of the tip.
        """
        return self._length

    @length.setter
    def length(self, value):
        self._length = value
        self.update_frame()

    @property
    def offset_x(self):
        """
        Offset x of the tip.
        """
        return self._offset_x

    @offset_x.setter
    def offset_x(self, value):
        self._offset_x = value
        self.update_frame()

    @property
    def offset_y(self):
        """
        Offset y of the tip.
        """
        return self._offset_y

    @offset_y.setter
    def offset_y(self, value):
        self._offset_y = value
        self.update_frame()

    @property
    def voice_coil_position(self):
        return self._voice_coil_position

    @voice_coil_position.setter
    def voice_coil_position(self, value):
        self._voice_coil_position = value

    @property
    def diameter(self):
        """
        Diameter of the tip.
        """
        return self._diameter

    @diameter.setter
    def diameter(self, value):
        self._diameter = value

    @property
    def separation(self):
        """
        Separation of two-finger tool required to pick multifinger.
        """
        return self._separation

    @separation.setter
    def separation(self, value):
        self._separation = value
        self.update_frame()

    @property
    def num_tips(self):
        """
        Number of tips in multifinger.
        """
        return self._num_tips

    @num_tips.setter
    def num_tips(self, value):
        self._num_tips = value

    @property
    def tip_distance(self):
        """
        Axial distance of adjacent tips in multifinger.
        """
        return self._tip_distance

    @tip_distance.setter
    def tip_distance(self, value):
        self._tip_distance = value

    @property
    def first_finger_offset(self):
        """
        Distance from the middle of multifinger tip to the first finger.
        """
        return self._first_finger_offset

    @first_finger_offset.setter
    def first_finger_offset(self, value):
        self._first_finger_offset = value
        self.update_frame()

    @property
    def slot_in(self):
        """
        Tip's slot-in position in workspace context. In this position tip is fixed to a rack.
        """
        return self._slot_in

    @slot_in.setter
    def slot_in(self, pose:list):
        """
        Set slot in pose (4-by-4 matrix).
        """
        if pose is None:
            self._slot_in = None
            return

        x, y, z = robotmath.frame_to_xyz(np.matrix(pose))
        log.debug("slot_in x={} y={} z={}".format(x, y, z))

        self._slot_in = pose

    @property
    def slot_out(self):
        """
        Tip's slot-out position in workspace context. In this position tip is free from a rack.
        When robot attaches or detaches a tip, it will first move over slot-out position.
        """
        return self._slot_out

    @slot_out.setter
    def slot_out(self, pose: list):
        """
        Set slot out pose (4-by-4 matrix).
        """
        if pose is None:
            self._slot_out = None
            return

        x, y, z = robotmath.frame_to_xyz(np.matrix(pose))
        log.debug("slot_out x={} y={} z={}".format(x, y, z))

        self._slot_out = pose

    @property
    def smart(self):
        """
        Boolean value to indicate if tip is a "smart tip". Smart tip name, type, diameter and length
        can be saved to a PCB on the physical tip. This is used to make sure that correct tool size is used
        when robot motion is planned.
        """
        return self._smart

    @smart.setter
    def smart(self, value):
        """
        Boolean value to indicate if tip is a "smart tip". Smart tip name, type, diameter and length
        can be saved to a PCB on the physical tip. This is used to make sure that correct tool size is used
        when robot motion is planned.
        """
        self._smart = value

    def is_slot_defined(self):
        return self._slot_in is not None and self._slot_out is not None

    @property
    @private
    def is_attached(self):
        """
        Is tip attached to a robot's tool.
        Note: This is not guaranteed to return correct status in case of smart tip.
        Use Robot.get_attached_tips() instead to update smart tip status.
        """
        if self.object_parent is None:
            return False

        if self.find_object_parent_by_class_name("Robot") is None:
            return False

        return True
