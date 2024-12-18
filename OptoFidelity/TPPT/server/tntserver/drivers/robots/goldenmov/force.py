

class Force:
    """
    Base class for robot force drivers.
    Force drivers must implement the methods defined by this base class in order to be
    usable by robots.
    """
    def __init__(self, robot):
        self.robot = robot

    def set_force_calibration_table(self, table):
        raise NotImplemented

    def press(self, context, x: float, y: float, force: float, z: float = None, tilt: float = 0, azimuth: float = 0,
              duration: float = 0, press_depth: float = -1, tool_name=None):
        raise NotImplemented

    def drag_force(self, context, x1: float, y1: float, x2: float, y2: float, force: float, z: float = None,
                   tilt1: float = 0, tilt2: float = 0, azimuth1: float = 0, azimuth2: float = 0,
                   tool_name=None):
        raise NotImplemented
