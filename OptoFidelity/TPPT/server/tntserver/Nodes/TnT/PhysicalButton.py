import logging
import numpy as np
from tntserver.Nodes.TnT import DeletableNode
from tntserver.Nodes.TnT import robotmath

log = logging.getLogger(__name__)


class PhysicalButton(DeletableNode):
    """
    TnT™ Compatible Button resource
    """
    def __init__(self, name):
        super().__init__(name)
        self._approach_position = None
        self._pressed_position = None
        self._jump_height = None

    @property
    def approach_position(self):
        """
        Robot position where button can be approached with linear movement.
        """
        return self._approach_position

    @approach_position.setter
    def approach_position(self, pose: list):
        """
        Set approach position in pose (4-by-4 matrix).
        """
        if pose is None:
            self._approach_position = None
            return

        x, y, z = robotmath.frame_to_xyz(np.matrix(pose))
        log.debug("approach_position x={} y={} z={}".format(x, y, z))

        self._approach_position = pose

    @property
    def pressed_position(self):
        """
        Robot position where the button is pressed down by the robot.
        """
        return self._pressed_position

    @pressed_position.setter
    def pressed_position(self, pose: list):
        """
        Set button pressed position in pose (4-by-4 matrix).
        """
        if pose is None:
            self._pressed_position = None
            return

        x, y, z = robotmath.frame_to_xyz(np.matrix(pose))
        log.debug("pressed_position x={} y={} z={}".format(x, y, z))

        self._pressed_position = pose

    @property
    def jump_height(self):
        """
        Height from approach position where robot can safely move over the approach position in the button's parent context.
        """
        return self._jump_height

    @jump_height.setter
    def jump_height(self, value):
        self._jump_height = value
