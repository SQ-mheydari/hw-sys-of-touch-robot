import logging
import numpy as np

import fik
import tntserver.robotmath as robotmath
from tntserver.drivers.robots.goldenmov import RobotKinematics
from tntserver.drivers.robots.goldenmov.kinematics import append_post_homing_move
import tntserver.drivers.robots.sm_regs as sm_regs
log = logging.getLogger(__name__)


class RobotPosition(RobotKinematics.RobotPositionBase):
    __slots__ = ["frame", "d", "t"]
    pass


class Kinematic_hmdiq(RobotKinematics):
    """
    6 DOF HMD IQ robot. Cartesian XYZ-stage with three rotary joints on top. Rotations are in order yaw - > pitch ->
    roll. XY-movement uses a H-bot type mechanism, in which one joint creates diagonal 45 degree (pi/4) movement.
    Positive movement of first joint moves the H-stage to positive X/positive Y direction. Positive movement of second
    joint moves H-stage to negative X/positive Y direction.
    """
    name = "hmdiq"

    def __init__(self, robot, axis_specs=None):
        self.axis_specs = axis_specs
        self.kinematics = fik.HMD_IQ()
        super().__init__(robot, RobotPosition)
        self.position_limits = None

    def _joints_to_position(self, joints: dict, kinematic_name=None, tool=None, calibrated=False) -> RobotPosition:

        j = {'x': joints['x'],
             'y': joints['y'],
             'z': joints['z'],
             'yaw': np.radians(joints['yaw']),
             'pitch': np.radians(joints['pitch']),
             'roll': np.radians(joints['roll'])}

        # Call FK with current robot model (nominal or calibrated)
        frame = np.matrix(self.kinematics.robot_forward_kinematics(joints=j, model=self.robot_model))
        pos = self.create_robot_position(frame=frame)
        if tool is not None:
            pos.frame = pos.frame * tool
        return pos

    def positions_to_joints(self, positions: list, kinematic_name=None, tool_inv=None, calibrated=False) -> list:
        if tool_inv is None:
            tool_inv = np.eye(4)
        toolframe = np.array(np.linalg.inv(tool_inv))
        joint_sets = []
        model = self.robot_model

        # pass initial guess to IK solver to reduce number of iterations
        initial_joints = [0] * len(self.kinematics.joint_aliases)

        for position in positions:
            position.frame = np.array(position.frame * tool_inv)

            # Call IK solver with used robot model (nominal or calibrated). Frame filtering can be disabled to speed up
            # computation, since there are no unreachable orientations for this robot type.
            ik_solution = self.kinematics.robot_inverse_kinematics(target_flange_pose=position.frame, tool=toolframe,
                                                                   model=model, q_i=initial_joints, filter_frames=False)

            initial_joints = ik_solution['joint_values']  # new initial guess is the previous solution
            joints_set = ik_solution['joints']
            joints = {
                'x': joints_set['x'],
                'y': joints_set['y'],
                'z': joints_set['z'],
                'yaw': np.degrees(joints_set['yaw']),
                'pitch': np.degrees(joints_set['pitch']),
                'roll': np.degrees(joints_set['roll']),
            }
            joint_sets.append(joints)

        return joint_sets

    def homing_sequence(self):
        sequence = [
            ("home", ["z"]),
            ("disable", ["x"]),
            ("home", ["y"]),
            ("disable", ["y"]),
            ("home", ["x"]),
            # Reset x- and y-axes feedback and setpoint to "home" it. Axes must have been enabled beforehand.
            ("set_axis_parameter", {"axis": "x", "param": sm_regs.SMP_SYSTEM_CONTROL,
                                    "value": sm_regs.SMP_SYSTEM_CONTROL_RESET_FB_AND_SETPOINT}),
            ("set_axis_parameter", {"axis": "y", "param": sm_regs.SMP_SYSTEM_CONTROL,
                                    "value": sm_regs.SMP_SYSTEM_CONTROL_RESET_FB_AND_SETPOINT}),
            ("move", {"y": 0}),  # optomotion has no enable_axis, so use move_absolute instead to enable axis.
            ("home", {"yaw"}),
            ("home", {"pitch"}),
            ("home", {"roll"}),
        ]

        return sequence

    def specs(self):
        # These specs are not saved in drives, instead TnT level configuration
        # For x, y, z:
        # Acceleration mm/s^2, velocity mm/s
        # For azimuth, tilt, roll:
        # Acceleration degree/s^2, velocity degrees/s

        if self.axis_specs is not None:
            return self.axis_specs
        else:
            # default settings if no configuration is given
            # TODO: update this
            p = {
                1: {'alias': 'x', 'homing_priority': 3, 'acceleration': 50, 'velocity': 10, 'move_tolerance': 0.001},
                2: {'alias': 'y', 'homing_priority': 2, 'acceleration': 50, 'velocity': 10, 'move_tolerance': 0.005},
                3: {'alias': 'z', 'homing_priority': 1, 'acceleration': 50, 'velocity': 10, 'move_tolerance': 0.001},
                4: {'alias': 'yaw', 'homing_priority': 4, 'acceleration': 500, 'velocity': 500,
                    'move_tolerance': 0.005},
                5: {'alias': 'pitch', 'homing_priority': 5, 'acceleration': 500, 'velocity': 500,
                    'move_tolerance': 0.001},
                6: {'alias': 'roll', 'homing_priority': 6, 'acceleration': 500, 'velocity': 500,
                    'move_tolerance': 0.001},
            }
            return p

    @property
    def robot_model(self):
        # Apply calibration parameters to nominal model if they exist
        if self.robot.calibration_data is not None:
            return self.kinematics.apply_parameters_to_model(self.kinematics.nominal_model, self.robot.calibration_data)
        else:
            return self.kinematics.nominal_model

    def arc_r(self, toolframe=None, kinematic_name=None):
        return self.robot.arc_length
