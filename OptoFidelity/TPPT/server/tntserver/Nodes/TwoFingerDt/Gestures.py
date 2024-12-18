import tntserver.Nodes.TnT.Gestures
from tntserver.Nodes.Node import json_out

import logging


log = logging.getLogger(__name__)


class Gestures(tntserver.Nodes.TnT.Gestures.Gestures):
    """
    Gestures for 2-finger-dt robot.
    """

    def __init__(self, name):
        super().__init__(name)

    def _init(self, **kwargs):
        super()._init(**kwargs)

    @json_out
    def put_tap(self, x: float, y: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                clearance: float = 0, duration: float = 0, separation=None, tool_name=None, kinematic_name=None):
        """
        Performs a tap with given parameters.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: (optional) distance from DUT surface during movement
        :param duration: How long to keep finger down in seconds (default: 0s).
        :param separation: Separation during tap. If None, then current separation is used.
        :param tool_name: Name of tool to perform tap with. Value is not used because 2-finger can only tap with both fingers simultaneously.
        :param kinematic_name: Name of kinematic to perform tap with.  Value is not used because 2-finger can only tap with both fingers simultaneously.
        :return: "ok" / error
        """
        log.info("put_tap x={} y={} z={} tilt={} azimuth={} clearance={} duration={} "
                 "separation={} tool_name={}".format(x, y, z, tilt, azimuth, clearance,
                                                      duration, separation, tool_name))

        if separation is not None:
            self.robot.put_finger_separation(separation)

        super().put_tap(x=x, y=y, z=z, tilt=tilt, azimuth=azimuth, clearance=clearance, duration=duration)

        return "ok"
