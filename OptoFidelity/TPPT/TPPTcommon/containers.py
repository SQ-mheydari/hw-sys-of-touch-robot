import numpy
import math

class TestAction(object):
    """
    Base class for discrete test actions
    """

    def __init__(self):
        pass


class Point(TestAction):
    """
    Container class representing a single 3D point for tests
    """

    def __init__(self, x, y, z, fingers=1, finger_distance=0, angle=0.0, first_finger_offset=0.0):
        # These coordinates always refer to the active finger of one-finger or two-finger tool.
        self.x = x
        self.y = y
        self.z = z
        self.azimuth = 0.0
        self.tilt = 0.0

        if fingers > 1 and finger_distance > 0:
            self.multifinger = True
        else:
            self.multifinger = False

        self.fingers = fingers
        self.finger_distance = finger_distance
        self.angle = angle
        self.first_finger_offset = first_finger_offset

    def __repr__(self):
        return "%s(%s) [x:%s; y:%s; z%s]" % (self.__class__.__name__, hex(id(self)), self.x, self.y, self.z)

    def data_dict(self):
        """
        Creates a dictionary of the container data.
        :return: Dictionary of container data.
        """
        return {"name": self.__class__.__name__,
                "x": self.x,
                "y": self.y,
                "z": self.z,
                "azimuth": self.azimuth,
                "tilt": self.tilt,
                "fingers": self.fingers,
                "finger_distance": self.finger_distance,
                "angle": self.angle,
                "first_finger_offset": self.first_finger_offset}

class TouchAreaPoint(Point):
    """
    Container class representing a single 3D point with touch area information
    """

    def __init__(self, x, y, z, fingers=1, finger_distance=0, angle=0.0, first_finger_offset=0.0, touch_area=''):
        super().__init__(x, y, z, fingers, finger_distance, angle, first_finger_offset)
        self.touch_area = touch_area

    def __repr__(self):
        return super().__repr__() + ', region:{0}'.format(self.touch_area)


class Line(TestAction):
    """
    Container class representing a single 3D line between start and end points for tests
    """

    def __init__(self, start_x, start_y, start_z, end_x, end_y, end_z, fingers=1, finger_distance=0, angle=0.0,
                 first_finger_offset=0.0):
        # These coordinates always refer to the active finger of one-finger or two-finger tool.
        self.start_x = start_x
        self.start_y = start_y
        self.start_z = start_z
        self.end_x = end_x
        self.end_y = end_y
        self.end_z = end_z
        self.azimuth = 0.0
        self.tilt = 0.0

        if fingers > 1 and finger_distance > 0:
            self.multifinger = True
        else:
            self.multifinger = False
        self.fingers = fingers
        self.finger_distance = finger_distance
        self.angle = angle
        self.first_finger_offset = first_finger_offset

    def __repr__(self):
        return "%s(%s) [start_x:%s; start_y:%s; start_z%s / end_x:%s; end_y:%s; end_z%s]" % (
        self.__class__.__name__, hex(id(self)), self.start_x, self.start_y, self.start_z, self.end_x, self.end_y,
        self.end_z)

    def length(self):
        return math.sqrt((self.start_x - self.end_x)**2 + (self.start_y - self.end_y)**2)

    def data_dict(self):
        """
        Creates a dictionary of the container data.
        :return: Dictionary of container data.
        """
        return {"start_x": self.start_x,
                "start_y": self.start_y,
                "start_z": self.start_z,
                "end_x": self.end_x,
                "end_y": self.end_y,
                "end_z": self.end_z,
                "azimuth": self.azimuth,
                "tilt": self.tilt,
                "fingers": self.fingers,
                "finger_distance": self.finger_distance,
                "angle": self.angle,
                "first_finger_offset": self.first_finger_offset}

class Pinch(TestAction):
    """
    Container class representing a single pinch centered at a point for tests
    """
    def __init__(self, center_x, center_y, start_separation, end_separation, azimuth):
        self.center_x = center_x
        self.center_y = center_y
        self.start_separation = start_separation
        self.end_separation = end_separation
        self.azimuth = azimuth
    def __repr__(self):
        return "%s(%s) [center_x:%s; center_y:%s; start_separation:%s; end_separation:%s; azimuth:%s]" % (
            self.__class__.__name__, hex(id(self)), self.center_x, self.center_y, self.start_separation,
            self.end_separation, self.azimuth)


