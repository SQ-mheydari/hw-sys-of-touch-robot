import logging

from tntserver import robotmath
from tntserver.Nodes.Node import json_out, Node

log = logging.getLogger(__name__)
import collections
import json

def tnt_pose_to_frame(x: float, y: float, z: float,
                      x_roll: float = None, y_roll: float = None, z_roll: float = None,
                      tilt: float = None, azimuth: float = None, spin: float = None):

    frame = None
    try:
        x_roll = float(x_roll)
        y_roll = float(y_roll)
        z_roll = float(z_roll)
        frame = robotmath.xyz_euler_to_frame(x, y, z, float(x_roll), float(y_roll), float(z_roll))
    except TypeError:
        pass  # x_roll, y_roll, z_roll not given

    try:
        a = float(azimuth)
        b = float(tilt)
        c = float(spin)
        frame = robotmath.xyz_euler_to_frame(x, y, z, -a, b, c, "rzyz")
    except TypeError:
        pass  # azimuth, tilt, spin not given

    if frame is None:
        frame = robotmath.identity_frame()

        frame.A1[3] = x
        frame.A1[7] = y
        frame.A1[11] = z

    return frame


def pose_to_tnt_roll_pose(frame):
    x, y, z, a, b, c = robotmath.frame_to_xyz_euler(frame)

    p = collections.OrderedDict((
        ("x", x),
        ("y", y),
        ("z", z),
        ("x_roll", a),
        ("y_roll", b),
        ("z_roll", c)))

    return p

def frame_to_tnt_tilt_azimuth_pose(frame):
    x, y, z, a, b, c = robotmath.frame_to_xyz_euler(frame)

    p = collections.OrderedDict((
        ("x", x),
        ("y", y),
        ("z", z),
        ("tilt", b),
        ("azimuth", -c)))

    return p

def flip(frame):
    """
    Modifies frame in place
    :param frame: Frame to flip x and z
    :return: None
    """
    frame.A[0:3, 0] *= -1
    frame.A[0:3, 2] *= -1


class ListingNode(Node):
    """
    TnT™ Compatible Resource Listing
    """
    def __init__(self, name, resources=None):
        super().__init__(name)
        self._resources = resources

    @json_out
    def post_self(self, name, type, **kwargs):
        return self.add(name, type, **kwargs)

    def add(self, name, type, **kwargs):
        """
        Create new child resource.
        :param name:
        :param type:
        :param kwargs:
        :return:
        """

        cls = self._resources[type]
        child = cls(name=name)

        self.add_child(child)

        child._init_arguments = kwargs
        child.init()

        self.save()

        if hasattr(child, "get_self"):
            result = child.get_self()

            return json.loads(result[1].decode('utf-8'))

        return {}


class DeletableNode(Node):

    @json_out
    def delete_self(self):
        return self.remove()

    def remove(self):
        """
        Deletes resource
        :return:
        """
        log.info("Deleted %s %s", type(self).__name__, self.name)
        parent = self.parent
        parent.remove_child(self)
        
        parent.save()

        return {"status": "ok"}

