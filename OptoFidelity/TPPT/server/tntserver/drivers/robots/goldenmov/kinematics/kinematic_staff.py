import logging
from tntserver import robotmath
from fik.models import Staff as staff_fik
import numpy as np
import math
import tntserver.drivers.robots.sm_regs as sm_regs
from fik.ge_model import GenericErrorModel

from . import RobotKinematics

log = logging.getLogger(__name__)


class RobotPosition(RobotKinematics.RobotPositionBase):
    __slots__ = ["frame", "voicecoil1", "d", "t"]
    pass


class Kinematic_staff(RobotKinematics):
    """
    Kinematics implementation of STAFF robot.
    Note: This is a simple model with no calibrations. Use fik library to implement model that can be calibrated.
    """
    name = "staff"

    def __init__(self, robot, axis_specs=None):
        if axis_specs is not None:
            self.axis_specs = axis_specs
        else:
            # Default settings if no configuration is given.
            # Voicecoil rest_position is where the axis will go when disabled.
            # Voicecoil rest_time means how many seconds it takes for position to stabilize after the axis is disabled.
            self.axis_specs = {
                1: {'alias': 'x', 'homing_priority': 1, 'acceleration': 500, 'velocity': 150},
                2: {'alias': 'y', 'homing_priority': 2, 'acceleration': 500, 'velocity': 150},
                3: {'alias': 'z', 'homing_priority': 3, 'acceleration': 500, 'velocity': 150, 'force_support': True},
                4: {'alias': 'azimuth', 'homing_priority': 1, 'acceleration': 500, 'velocity': 150},
                5: {'alias': 'tilt', 'homing_priority': 2, 'acceleration': 500, 'velocity': 150},
                6: {'alias': 'voicecoil1', 'homing_priority': 2, 'acceleration': 50, 'velocity': 10, 'press_margin': 1,
                    'rest_position': 1.6, 'rest_time': 2.0}
            }

        # self.fik is before super().__init() because it's required
        # for calibration setter to work which is used in super().__init()
        self.fik = staff_fik()  # instance of Staff model from fik library

        super().__init__(robot, RobotPosition)

        # Apply possible DH-model calibration to the kinematics instance self.model via the parameters setter. If
        # calibration is None, the values default to the nominal model.
        if self.model_calibration is None:
            log.info("Using nominal static STAFF kinematic model.")
        else:
            log.info("Using calibrated static STAFF kinematic model.")

            self.fik.parameters = self.model_calibration

        self.generic_error_model_coefficients = None

        if self.calibration_data:
            if self.calibration_data.get('generic_error_model', None) is not None:
                self.generic_error_model_coefficients = self.calibration_data['generic_error_model']['coefficients']

        if self.generic_error_model_coefficients is not None:
            log.info("Using additional generic variable 6-DOF error model calibration.")
            self.fik.generic_error_model = \
                GenericErrorModel.from_coefficient_dictionary(coefficients=self.generic_error_model_coefficients,
                                                              joint_mapping=self.fik.joint_mapping)

        # This is for storing VC position for the duration when VC is disabled.
        # When VC is enabled, value must be None and VC position or setpoint is used by kinematics.
        self.voicecoil_position = None

        # Position of z axis is stored for the duration where z is set to force mode.
        # This is required because kinematics needs to know z axis position when performing movements with
        # other axes. Should be None when not in force mode.
        self._z_position = None

    @property
    def model_calibration(self):
        return self.calibration_data.get("model", None)

    def _joints_to_position(self, joints: dict, kinematic_name=None, tool=None, calibrated=False) -> RobotPosition:
        pos = self._robot_fk(joints, kinematic_name)

        if tool is not None:
            pos.frame = pos.frame * tool

        return pos

    def positions_to_joints(self, positions: list, kinematic_name=None, tool_inv=None, calibrated=False) -> list:
        # Get setpoints.
        axis_setpoints = self.get_scaled_axis_setpoints()

        # Call base class method on position values
        return self._positions_to_joints(positions=positions, axis_setpoints=axis_setpoints,
                                         kinematic_name=kinematic_name, tool_inv=tool_inv)

    def _positions_to_joints(self, positions: list, axis_setpoints, kinematic_name=None,  tool_inv=None) -> list:
        # Compute IK for position and apply calibration to joint values, if available. Child class must implement
        # self._position_to_joints()

        if tool_inv is None:
            tool_inv = robotmath.identity_frame()

        tool = robotmath.inv_oht(tool_inv)

        joints_list = []

        q_i = None

        rotation_error_limit = self.parameters.get("rotation_error_limit", 0.0001)
        position_error_limit = self.parameters.get("position_error_limit", 0.0001)
        itol = self.parameters.get("itol", 1e-8)

        for pos in positions:
            joints, q_i = self._robot_ik(pos, axis_setpoints, kinematic_name, tool_inv, tool, q_i=q_i,
                                         rotation_error_limit=rotation_error_limit,
                                         position_error_limit=position_error_limit,
                                         itol=itol)

            joints_list.append(joints)

        if self.joint_calibration_model is not None:
            joints_list = self.joint_calibration_model.compensate_joint_values_list_ik(joints_list)

        return joints_list

    def _robot_fk(self, joints: dict, kinematic_name) -> RobotPosition:
        """
        Calculate forward kinematics for given tool and joint positions.
        :param joints: joint values as a dict
        :param kinematic_name: kinematic name that defines how tool transformation is done
        :return: RobotPosition object for given joints positions
        """

        if kinematic_name == "camera":
            # Camera has no tilt.
            joints["tilt"] = 0

        if kinematic_name == "force":
            # Force kinematics is used when z is in force mode. In this case z joint position
            # can't be queried from the drive.
            if self._z_position is None:
                raise Exception("Position of z axis has not been set when in force mode.")

            z_joint = self._z_position
        else:
            z_joint = joints["z"]

        # If calibration has been applied to the kinematic model, it is used automatically
        frame = self.fik.robot_forward_kinematics(joints={"x": joints["x"],
                                                          "y": joints["y"],
                                                          "z": z_joint,
                                                          "azimuth": math.radians(joints["azimuth"]),
                                                          "tilt": math.radians(joints["tilt"])
                                                          })

        # Take VC setpoint into account in effective z.
        if kinematic_name == "force":
            # When z is in force mode VC must have been disabled and self.voicecoil_position should have the actual position.
            if self.voicecoil_position is None:
                raise Exception("Voicecoil must be disabled when z axis is in force mode.")

            vc = self.voicecoil_position
        elif self.voicecoil_position is None:
            # Voicecoil is redundant with z-axis. The default mode of operations is that
            # voicecoil acts as a spring and is ignored in IK/FK calculations. The current setpoint of voicecoil
            # joint is used instead of joint position to enable spring-like behavior.
            vc = self.get_scaled_axis_setpoints()["voicecoil1"]
        else:
            vc = self.voicecoil_position

        frame[2, 3] -= vc

        return self.create_robot_position(frame=np.matrix(frame), voicecoil1=vc)

    def _robot_ik(self, pos: RobotPosition, axis_setpoints, kinematic_name, tool_inv, tool, q_i=None,
                  rotation_error_limit=0.0001, position_error_limit=0.0001, itol=1e-8):
        frame = pos.frame * tool_inv

        if kinematic_name == "camera":
            # Camera has no tilt.
            x, y, z, _, _, c = robotmath.frame_to_xyz(frame)
            frame = robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(x, y, z, 0, 0, c))

        # Compute IK solution. As of fik 0.2.2 the checking for solution validity is done inside the library
        # (parameter filter_frames)

        # If calibration has been applied to the kinematic model, it is used automatically
        ik_result = self.fik.robot_inverse_kinematics(
            target_flange_pose=np.array(frame),
            rotation_error_limit=rotation_error_limit,
            position_error_limit=position_error_limit,
            itol=itol,
            tool=np.array(tool),
            filter_frames=True,
            q_i=q_i
        )

        joints = ik_result['joints']

        # VC kinematics moves VC to get to target z in workspace and z axis uses the current setpoint.
        # Default kinematics uses z axis to get to terget z in workspace and VC uses current setpoint.
        if kinematic_name == "voicecoil1":
            if self.voicecoil_position is not None:
                raise Exception("Can't use voicecoil kinematics when voicecoil is disabled.")

            driver_z_axis_setpoint = axis_setpoints["z"]
            z_joint = driver_z_axis_setpoint
            vc_joint = (joints["z"] - driver_z_axis_setpoint)

            joints['z'] = z_joint
            joints['voicecoil1'] = vc_joint
        elif kinematic_name == "force":
            # When using force kinematics z axis is in force mode and VC is disabled.
            # Remove z joint and don't set VC joint to keep the axes in their current states.
            del joints['z']
            assert 'voicecoil1' not in joints
        else:
            # If voicecoil_position is None, it means that VC is enabled and VC setpoint can be used.
            # If voicecoil_position is not None, it means that VC is disabled and
            # voicecoil_position should be used as VC position.
            if self.voicecoil_position is None:
                vc_pos = pos.voicecoil1

                if vc_pos is not None:
                    vc_joint = vc_pos
                else:
                    vc_joint = axis_setpoints["voicecoil1"]

                joints['voicecoil1'] = vc_joint
            else:
                vc_joint = self.voicecoil_position

            z_joint = joints["z"] - vc_joint

            joints['z'] = z_joint

        joints['azimuth'] = math.degrees(joints['azimuth'])
        joints['tilt'] = math.degrees(joints['tilt'])

        return joints, q_i

    def homing_sequence(self):
        sequence = [
            # Set voicecoil continuous current limits to given values
            ("home", ['z', 'x', 'tilt', 'azimuth', 'y', 'voicecoil1']),
            ("move", {'z': 10}),
            ("home", ['z']),
            ("move", {'azimuth': 45}),
            ("home", ['azimuth']),
            ("move", {'tilt': 45}),
            ("home", ['tilt'])
        ]

        return sequence

    def specs(self):
        return self.axis_specs

    def arc_r(self, toolframe=None, kinematic_name=None):
        # TODO: Should use tool length here.
        return 50.0

    def pre_force_mode_change(self, axis, mode):
        if axis == "z":
            if mode == sm_regs.FORCE_MODE_FORCE_CTRL:
                # Set z position that is needed when axis is in force mode.
                self._z_position = self.driver.get_scaled_axis_setpoint(axis)
            else:
                self._z_position = None
