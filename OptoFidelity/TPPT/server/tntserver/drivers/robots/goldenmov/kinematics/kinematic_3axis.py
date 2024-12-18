import logging
from toolbox import robotmath
from tntserver.drivers.robots.goldenmov import RobotKinematics
from tntserver.drivers.robots.goldenmov.kinematics import append_post_homing_move


log = logging.getLogger(__name__)


def filter_frame_3axis(frame):
    """
    Filter frame so that 3-axis kinematics can be applied to it.
    This means that rotation part is aligned with workspace.
    :param frame: Frame to be filtered.
    :return: Filtered frame.
    """
    return robotmath.pose_to_frame(robotmath.xyz_to_frame(*robotmath.frame_to_xyz(frame)))


class RobotPosition(RobotKinematics.RobotPositionBase):
    __slots__ = ["frame", "d", "t"]
    pass


class Kinematic_3axis(RobotKinematics):
    """
    Kinematics implementation of standard 3-axis robot.
    """
    name = "3axis"

    def __init__(self, robot, axis_specs=None):
        self.axis_specs = axis_specs

        super().__init__(robot, RobotPosition)

        # default tool orientation in relation to robot base
        self._tool_orientation = robotmath.xyz_euler_to_frame(0, 0, 0, 180, 0, 180)
        self._tool_orientation_i = self._tool_orientation.I

    def _joints_to_position(self, joints: dict, kinematic_name=None, tool=None, calibrated=False) -> RobotPosition:
        pos = self._robot_fk(joints)

        if tool is not None:
            pos.frame = pos.frame * tool

        return pos

    def positions_to_joints(self, positions: list, kinematic_name=None, tool_inv=None, calibrated=False) -> list:
        # Call base class method on position values
        return self._positions_to_joints(positions=positions, axis_setpoints=None, kinematic_name=kinematic_name,
                                         tool_inv=tool_inv)

    def _position_to_joints(self, pos: RobotPosition, axis_setpoints=None, kinematic_name=None, tool_inv=None) -> dict:
        position = pos.copy()
        position.frame = filter_frame_3axis(position.frame)

        if tool_inv is not None:
            position.frame = position.frame * tool_inv

        joints = self._robot_ik(position)

        return joints

    def _robot_fk(self, joints: dict) -> RobotPosition:
        """
        Forward kinematics.
        :param joints: Dictionary of joint values.
        :return: Robot position corresponding to given joint values.
        """
        y = joints['y']
        x = joints['x']
        z = joints['z']

        frame = robotmath.xyz_euler_to_frame(x, y, -z, 0, 0, 0) * self._tool_orientation

        return self.create_robot_position(frame=frame)

    def _robot_ik(self, pos: RobotPosition):
        x, y, z, = robotmath.frame_to_xyz(pos.frame * self._tool_orientation_i)

        joints = {'y': y, 'x': x, 'z': -z}

        return joints

    def homing_sequence(self):
        # First home all axes (order should be chosen so that it is safe even if head is in e.g. tip rack).
        # Then move z down so that home switch opens.
        # Finally home z once again to get precise z home position.
        sequence = [
            ("home", ['z', 'x', 'y']),
            ("move", {'z': 10}),
            ("home", ['z'])
        ]

        append_post_homing_move(sequence, self.axis_specs)

        return sequence

    def specs(self):
        # These specs are not saved in drives, instead TnT level configuration
        # For x, y, z:
        # Acceleration mm/s^2, velocity mm/s

        if self.axis_specs is not None:
            return self.axis_specs
        else:
            # default settings if no configuration is given
            p = {
                1: {'alias': 'x', 'homing_priority': 1, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.005},
                2: {'alias': 'y', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
                3: {'alias': 'z', 'homing_priority': 3, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
            }
            return p

    def arc_r(self, toolframe=None, kinematic_name=None):
        return 0.0

