import logging
from tntserver.Nodes.Node import json_out
from tntserver.Nodes.TnT.PhysicalButton import PhysicalButton
import tntserver.Nodes.TnT.Robot
import tntserver.robotmath as robotmath
from tntserver.Nodes.Node import Node
import numpy as np

# Hardcode logger name to get logging under same name as normal TnT.Robot node logs
log = logging.getLogger('tntserver.Nodes.TnT.Robot')


class Robot(tntserver.Nodes.TnT.Robot.Robot):
    """
    Robot node for 6-DOF
    """
    def __init__(self, name):
        super().__init__(name)
        self.arc_length = 100

    def _init(self, **kwargs):
        # call the original _init from TnT.Robot
        super()._init(**kwargs)

    @json_out
    def get_effective_pose(self, context: str, kinematic_name=None):
        """
        Current robot effective Pose in given context
        :param context: context node name as string
        :return: pose as 4x4 matrix
        """
        if context is not None:
            target_context = Node.find(context)
        else:
            target_context = self.parent

        if kinematic_name is None:
            kinematic_name = self.kinematic_name

        effective_frame = self.driver.frame(tool=self.tool_frame(kinematic_name), kinematic_name=kinematic_name)

        # The base class method does here an additional frame_to_pose() flip, which should not be done for this robot.
        frame = robotmath.translate(effective_frame, self.object_parent, target_context)

        return frame.tolist()

    def set_effective_pose(self, context: Node, pose, kinematic_name=None):
        """
        Moves robot effector to given Pose
        Pose is a 4x4 matrix where rotation part is identity matrix if Effector rotation is zero
            ( if user selects zero Tilt & Azimuth from UI )
        :param context: context as Node
        :param pose: target pose as 4x4 matrix
        :return:
        """
        pose = np.matrix(pose)
        assert pose.shape == (4, 4)
        # The base class method does here an additional pose_to_frame() flip, which should not be done for this robot.
        frame = pose
        self.move_frame(frame, context, kinematic_name=kinematic_name)

