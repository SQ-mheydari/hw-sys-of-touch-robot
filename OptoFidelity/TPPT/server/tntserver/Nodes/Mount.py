from tntserver.Nodes.Node import Node, private
from tntserver.Nodes.TnT.Tool import Tool
import tntserver.robotmath as robotmath

class Mount(Node):
    """
    Mounting point to named kinematic point
    """
    def __init__(self, name):
        super().__init__(name)

        self._mount_point = None

    def _init(self, **kwargs):
        """
        Initialize Mount node.
        """
        pass

    @property
    def mount_point(self):
        return self._mount_point

    @mount_point.setter
    def mount_point(self, value):
        self._mount_point = value

    @property
    @private
    def frame(self):
        """
        Mount frame as calculated by robot kinematics at the mount point.
        """
        robot = self.find_object_parent_by_class_name("Robot")
        driver = robot.driver

        # Use identity tool frame.
        f = driver.frame(robotmath.identity_frame(), kinematic_name=self.mount_point)
        return f

    @frame.setter
    def frame(self, f):
        robot = self.find_object_parent_by_class_name("Robot")
        robot.move_frame(f, Node.find("ws"), kinematic_name=self.mount_point, tool_frame=robotmath.identity_frame())

    @property
    @private
    def tool(self):
        """
        Tool node that is the child of Mount node.
        """
        if len(self.object_children) == 0:
            return None

        # Assume that mount has exactly one child that must be a Tool node.
        # TODO: Perhaps this should traverse until it finds a Tool node in case there is e.g. another Robot attached.
        first_child = list(self.object_children.values())[0]

        if type(first_child) is not Tool:
            return None

        return first_child


