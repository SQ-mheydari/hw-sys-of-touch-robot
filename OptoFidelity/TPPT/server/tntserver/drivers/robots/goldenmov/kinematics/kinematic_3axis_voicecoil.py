import logging
from toolbox import robotmath
from tntserver.drivers.robots.goldenmov import RobotKinematics
from tntserver.drivers.robots.goldenmov.kinematics import append_post_homing_move
from .kinematic_3axis import filter_frame_3axis

log = logging.getLogger(__name__)


class RobotPosition(RobotKinematics.RobotPositionBase):
    __slots__ = ["frame", "d", "t", "voicecoil1"]
    pass


class Kinematic_3axis_voicecoil(RobotKinematics):
    """
    Kinematics implementation of standard 3-axis robot with voicecoil-based OptoStandard force actuator.
    """
    name = "3axis_voicecoil"
    voicecoil_joint_name = 'voicecoil1'

    def __init__(self, robot, axis_specs=None):

        if axis_specs is not None:
            self.axis_specs = axis_specs
        else:
            # default settings if no configuration is given
            self.axis_specs = {
                23: {'alias': 'x', 'homing_priority': 1, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.005},
                1: {'alias': 'y', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
                12: {'alias': 'z', 'homing_priority': 3, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
                11: {'alias': 'voicecoil1', 'homing_priority': 4, 'acceleration': 20000, 'velocity': 50,
                    'move_tolerance': 0.001, 'press_margin': 1},
            }

        super().__init__(robot, RobotPosition)

        # default tool orientation in relation to robot base
        self._tool_orientation = robotmath.xyz_euler_to_frame(0, 0, 0, 180, 0, 180)
        self._tool_orientation_i = self._tool_orientation.I

    def _joints_to_position(self, joints: dict, kinematic_name=None, tool=None, calibrated=False) -> RobotPosition:
        pos = self._robot_fk(joints, kinematic_name)

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
        position.frame = filter_frame_3axis(position.frame)

        if tool_inv is not None:
            position.frame = position.frame * tool_inv

        joints = self._robot_ik(position, axis_setpoints, kinematic_name)

        return joints

    def _robot_fk(self, joints: dict, kinematic_name=None) -> RobotPosition:
        """
        Forward kinematics.
        :param joints: Dictionary of joint values.
        :return: Robot position corresponding to given joint values.
        """
        y = joints['y']
        x = joints['x']
        z = joints['z']

        if kinematic_name == "force":
            # When voicecoil is in force mode the setpoint can't be used in z-kinematics.
            # Motion planning that uses force kinematics must assume that VC is at zero position.
            vc1_setpoint = 0
        else:
            vc1_setpoint = self.get_scaled_axis_setpoints()[self.voicecoil_joint_name]

        frame = robotmath.xyz_euler_to_frame(x, y, -(z + vc1_setpoint), 0, 0, 0) * self._tool_orientation

        position = self.create_robot_position(frame=frame)
        setattr(position, self.voicecoil_joint_name, vc1_setpoint)

        return position

    def _robot_ik(self, pos: RobotPosition, axis_setpoints: dict, kinematic_name=None):
        """
        use z-axis or voicecoil movement in z-axis direction depending on kinematic_name
        """
        x, y, z, = robotmath.frame_to_xyz(pos.frame * self._tool_orientation_i)
        driver_z_axis_setpoint = axis_setpoints['z']

        if kinematic_name == "voicecoil1":
            z_joint = driver_z_axis_setpoint
            vc_joint = -(z + driver_z_axis_setpoint)

            joints = {'y': y, 'x': x, 'z': z_joint, self.voicecoil_joint_name: vc_joint}
        elif kinematic_name == "force":
            # When voicecoil is in force mode the setpoint can't be used in z-kinematics.
            # Motion planning that uses force kinematics must assume that VC is at zero position.
            vc_joint = 0
            z_joint = -z

            # Don't pass VC joint to prevent optomotion setting it to position mode.
            joints = {'y': y, 'x': x, 'z': z_joint}
        else:
            vc_pos = getattr(pos, self.voicecoil_joint_name)
            if vc_pos is not None:
                vc_joint = vc_pos
            else:
                vc1_setpoint = axis_setpoints[self.voicecoil_joint_name]
                vc_joint = vc1_setpoint
            z_joint = -z - vc_joint

            joints = {'y': y, 'x': x, 'z': z_joint, self.voicecoil_joint_name: vc_joint}

        return joints

    def homing_sequence(self):
        # First home all axes (order should be chosen so that it is safe even if head is in e.g. tip rack).
        # Then move z down so that home switch opens.
        # Finally home z once again to get precise z home position.
        sequence = [
            ("home", ['z', 'x', 'y']),
            ("move", {'z': 10}),
            ("home", ['z', self.voicecoil_joint_name])
        ]

        append_post_homing_move(sequence, self.axis_specs)

        return sequence

    def specs(self):
        # These specs are not saved in drives, instead TnT level configuration
        # For x, y, z:
        # Acceleration mm/s^2, velocity mm/s
        return self.axis_specs

    def set_specs(self, axis_specs):
        """
        Sets axis_specs dict. Also sets press margin to voicecoil if one is not given.
        :param axis_specs: Value that is given to self.axis_specs.
        """
        # If voicecoils don't have press_margin given add press_margin 1mm for them as default value
        for axis in axis_specs:
            if axis_specs[axis]['alias'] == 'voicecoil1':
                if 'press_margin' not in axis_specs[axis]:
                    axis_specs[axis].update({'press_margin': 1})

        self.axis_specs = axis_specs

    def arc_r(self, toolframe=None, kinematic_name=None):
        return 0.0
