import numpy as np
import logging
import tntserver.robotmath as robotmath
from tntserver.drivers.robots.goldenmov import RobotKinematics
from tntserver.drivers.robots.goldenmov.kinematics import append_post_homing_move
from.kinematic_synchro import filter_frame_xyza, determine_robot_azimuth
import math

log = logging.getLogger(__name__)


class RobotPosition(RobotKinematics.RobotPositionBase):
    __slots__ = ["frame", "voicecoil1", "d", "t"]
    pass


class Kinematic_xyza_voicecoil(RobotKinematics):
    """
    Kinematics implementation xyz+azimuth+voicecoil robot.

    """
    name = "xyza-voicecoil"

    def __init__(self, robot, axis_specs=None):
        self.axis_specs = axis_specs

        super().__init__(robot, RobotPosition)

        # Default tool orientation in relation to robot base.
        # This is the final transformation in the forward kinematics chain to make the robot local z-axis point
        # "down" i.e. along negative robot base z-axis.
        self._tool_orientation = robotmath.xyz_euler_to_frame(0, 0, 0, 180, 0, 180)
        self._tool_orientation_i = self._tool_orientation.I

    def _joints_to_position(self, joints: dict, kinematic_name=None, tool=None, calibrated=False) -> RobotPosition:
        if kinematic_name is not None and kinematic_name == 'camera':
            pos = self._camera_fk(joints)
        else:
            pos = self._robot_fk(joints)
        if tool is not None:
            pos.frame = pos.frame * tool
        return pos

    def positions_to_joints(self, positions: list, kinematic_name=None, tool_inv=None, calibrated=False) -> list:
        axis_setpoints = self.get_scaled_axis_setpoints()

        # Call base class method on position values
        return self._positions_to_joints(positions=positions, axis_setpoints=axis_setpoints,
                                         kinematic_name=kinematic_name, tool_inv=tool_inv)

    def _position_to_joints(self, pos: RobotPosition, axis_setpoints, kinematic_name=None, tool_inv=None) -> dict:
        position = pos.copy()
        if kinematic_name == 'camera':
            # First remove rotation as camera does not rotate with azimuth.
            x, y, z = robotmath.frame_to_xyz(position.frame)
            # Then compose a frame and take tool into account.
            position.frame = robotmath.xyz_to_frame(x, y, z)
            position.frame = robotmath.pose_to_frame(position.frame)

            if tool_inv is not None:
                position.frame = position.frame * tool_inv

            return self._camera_ik(position)
        else:
            position.frame = filter_frame_xyza(position.frame)

            if tool_inv is not None:
                position.frame = position.frame * tool_inv

            return self._robot_ik(position, axis_setpoints, kinematic_name)

    def _robot_fk(self, joints: dict) -> RobotPosition:
        """
        Calculate forward kinematics for given tool and joint positions.
        :param joints: joint values as a dict
        :param kinematic_name: kinematic name that defines how tool transformation is done
        :return: RobotPosition object for given joints positions
        """

        # read raw joint values
        y = joints['y']
        x = joints['x']
        z = joints['z']
        a = joints['azimuth']

        # Voicecoil is redundant with z-axis. The default mode of operations is that
        # voicecoil acts as a spring and is ignored in IK/FK calculations. The current setpoint of voicecoil
        # joint is used instead of joint position to enable spring-like behavior.
        vc1_setpoint = self.get_scaled_axis_setpoints()["voicecoil1"]

        # joints to xyz frame
        m_xyz = robotmath.xyz_to_frame(x, y, -(z + vc1_setpoint))

        # azimuth frame
        m_azi = robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, -a)

        # xyz + azimuth + tool orientation (down)
        m_f = m_xyz * m_azi * self._tool_orientation

        return self.create_robot_position(frame=m_f, voicecoil1=vc1_setpoint)

    def _robot_ik(self, pos: RobotPosition, axis_setpoints: dict, kinematic_name=None):

        # effective frame
        m_f = pos.frame * self._tool_orientation_i

        # write joints
        x, y, z, a, b, c = robotmath.frame_to_xyz_euler(m_f)

        azimuth = determine_robot_azimuth(m_f, axis_setpoints["azimuth"])

        # Update reference azimuth value to make next IK computation more accurate.
        # This is required for cases when the planned motion rotates azimuth >= 180 degrees.
        # Especially this handles case where azimuth is rotated 180 degrees + epsilon (due to e.g. round-off).
        # Such rotation can often happen when picking tip, moving to screenshot position etc.
        axis_setpoints["azimuth"] = azimuth

        if kinematic_name == "voicecoil1":
            driver_z_axis_setpoint = axis_setpoints["z"]
            z_joint = driver_z_axis_setpoint
            vc_joint = -(z + driver_z_axis_setpoint)
        else:
            vc_pos = pos.voicecoil1

            if vc_pos is not None:
                vc_joint = vc_pos
            else:
                vc_joint = axis_setpoints["voicecoil1"]

            z_joint = -z - vc_joint

        joints = {'y': y, 'x': x, 'z': z_joint, 'azimuth': azimuth, 'voicecoil1': vc_joint}

        return joints

    def _camera_fk(self, joints):
        x = joints['x']
        y = joints['y']
        z = joints['z']
        vc1 = self.get_scaled_axis_setpoints()["voicecoil1"]

        frame = robotmath.xyz_euler_to_frame(x, y, -z, 180, 0, 180)

        return self.create_robot_position(frame=frame, voicecoil1=vc1)

    def _camera_ik(self, pos: RobotPosition):
        x, y, z = robotmath.frame_to_xyz(pos.frame)

        joints = {'y': y, 'x': x, 'z': -z}

        if pos.voicecoil1 is not None:
            joints["voicecoil1"] = pos.voicecoil1

        return joints

    def homing_sequence(self):
        # home axes
        # Voicecoils are homed twice just in case, because after recovering from emergency stop they can end up in the
        # wrong home position (too low).
        # z and azimuth are homed twice with move in-between to overcome issue with homing from home-switch.
        sequence = [
            ("home", ['z', 'x', 'azimuth', 'y', 'voicecoil1', 'voicecoil1']),
            ("move", {'z': 10}),
            ("home", ['z']),
            ("move", {'azimuth': 45}),
            ("home", ['azimuth'])
        ]

        if self.axis_specs is not None:
            append_post_homing_move(sequence, self.axis_specs)

        return sequence

    def specs(self):
        # These specs are not saved in drives, instead TnT level configuration
        # For x, y, z:
        # Acceleration mm/s^2, velocity mm/s
        # For azimuth, tilt:
        # Acceleration degree/s^2, velocity degrees/s

        if self.axis_specs is not None:
            return self.axis_specs
        else:
            # default settings if no configuration is given
            p = {
                1: {'alias': 'y', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
                32: {'alias': 'x', 'homing_priority': 1, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.005},
                31: {'alias': 'z', 'homing_priority': 3, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
                22: {'alias': 'azimuth', 'homing_priority': 1, 'acceleration': 500, 'velocity': 500,
                    'move_tolerance': 0.005},
                11: {'alias': 'voicecoil1', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500,
                    'move_tolerance': 0.001},
            }
            return p

    def arc_r(self, toolframe=None, kinematic_name=None):
        # TODO: This determines azimuth rotation speed when xyz is stationary. Should this be configurable?
        return 50
