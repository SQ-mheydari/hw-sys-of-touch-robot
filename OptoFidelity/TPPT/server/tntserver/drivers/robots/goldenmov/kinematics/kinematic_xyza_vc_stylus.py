import numpy as np
import logging
import tntserver.robotmath as robotmath
from tntserver.drivers.robots.goldenmov import RobotKinematics
from tntserver.drivers.robots.goldenmov.kinematics import append_post_homing_move
from tntserver.drivers.robots.goldenmov.kinematics.kinematic_synchro import determine_robot_azimuth,\
    calculate_synchro_tool_camera_offsets, filter_frame_xyza

log = logging.getLogger(__name__)


class RobotPosition(RobotKinematics.RobotPositionBase):
    __slots__ = ["frame", "voicecoil1", "tilt_slider", "d", "t"]
    pass


class Kinematic_xyza_vc_stylus(RobotKinematics):
    """
    Kinematics implementation for a stylus robot with azimuth rotation, stylus tilting and a voiceoil actuator.

    """
    name = "xyza-vc-stylus"

    def __init__(self, robot, axis_specs=None):

        if axis_specs is not None:
            self.axis_specs = axis_specs
        else:
            # default settings if no configuration is given
            self.axis_specs = {
                1: {'alias': 'y', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
                32: {'alias': 'x', 'homing_priority': 1, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.005},
                31: {'alias': 'z', 'homing_priority': 3, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
                22: {'alias': 'azimuth', 'homing_priority': 1, 'acceleration': 500, 'velocity': 500,
                     'move_tolerance': 0.005},
                11: {'alias': 'voicecoil1', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500,
                     'move_tolerance': 0.001, 'press_margin': 1},
                12: {'alias': 'tilt_slider', 'homing_priority': 3, 'acceleration': 500, 'velocity': 500,
                     'move_tolerance': 0.001},
            }

        super().__init__(robot, RobotPosition)

        # Mounting offset for stylus angle (mechanically set to either -15.0 or 0 deg)
        self._rotation_offset = robotmath.xyz_euler_to_frame(0, 0, 0, 0, self.stylus_mount_angle, 0)

        # Default tool orientation in relation to robot base.
        # This is the final transformation in the forward kinematics chain to make the robot local z-axis point
        # "down" i.e. along negative robot base z-axis.
        self._tool_orientation = robotmath.xyz_euler_to_frame(0, 0, 0, 180, 0, 180)
        self._tool_orientation_i = self._tool_orientation.I
        self._rotation_offset_i = self._rotation_offset.I

    @property
    def sr_link_length(self):
        # Link length of Scott-Russell straight line mechanism
        return self.calibration_data.get("sr_link_length", 50.0)

    @property
    def stylus_mount_angle(self):
        # Mounting offset for stylus angle, by default at -15.0 deg
        return self.calibration_data.get("stylus_mount_angle", -15.0)

    @property
    def tool1_offset(self):
        """
        Fixed affine transform after azimuth rotation and tilt joint to the tip of the stylus.
        This should mainly have small x- and y-values and a positive z-value at around 100 mm.
        """
        offset = self.calibration_data["tool1_offset"]

        # offset should be a list of lists that is interpreted as 4x4 matrix.
        assert type(offset) is list

        return np.matrix(offset)

    @property
    def tilt_slider_zero_position(self):
        """
        Absolute value of tilt slider linear joint when stylus tilt angle is zero.
        :return: Joint value in mm. Defaults to approx 25.88 mm without calibration.
        """
        return self.calibration_data.get("tilt_slider_zero_position", np.sin(np.radians(15))*100)

    def _joints_to_position(self, joints: dict, kinematic_name=None, tool=None, calibrated=False) -> RobotPosition:
        if kinematic_name is not None and kinematic_name == 'camera':
            pos = self._camera_fk(joints)
        else:
            axis_setpoints = self.get_scaled_axis_setpoints()
            pos = self._robot_fk(joints, kinematic_name=kinematic_name, axis_setpoints=axis_setpoints)
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
            if kinematic_name == 'azimuth':
                position.frame = filter_frame_xyza(position.frame)  # Remove other rotations except azimuth
            else:
                # Leave only tilt and azimuth rotation
                position = self.filter_position(position, axis_setpoints, kinematic_name, tool_inv)

            if tool_inv is not None:
                position.frame = position.frame * tool_inv

            return self._robot_ik(position, axis_setpoints, kinematic_name)

    def filter_position(self, pos: RobotPosition, axis_setpoints, kinematic_name=None, tool_inv=None) \
            -> RobotPosition:

        target_pos = pos.copy()

        if tool_inv is not None:
            target_pos.frame = target_pos.frame * tool_inv  # target tool pose to target flange pose

        ik_result = self._robot_ik(target_pos, axis_setpoints, kinematic_name)

        # Calculate where the robot flange ends up with the given solution
        result_flange_pos = self._robot_fk(ik_result, kinematic_name, axis_setpoints)

        # Modify the target to use the orientation that was possible for the robot.
        pos.frame.A[0:3, 0:3] = result_flange_pos.frame.A[0:3, 0:3]

        return pos

    def compute_tool_transform(self, kinematic_name):
        """
        Return toolframe definition for specified kinematic (tool or mount point).
        :param kinematic_name: Name of kinematic to use.
        :return: Transform as numpy matrix.
        """
        if kinematic_name == "tool1" or kinematic_name == 'voicecoil1':
            return self.tool1_offset
        elif kinematic_name == "azimuth":
            # This corresponds to stylus mount point i.e. position after x, y, z and azimuth joint
            return robotmath.identity_frame()
        else:
            raise Exception("unknown kinematic name {} given for joints_to_position".format(kinematic_name))

    def _robot_fk(self, joints: dict, kinematic_name, axis_setpoints) -> RobotPosition:
        """
        Calculate forward kinematics for given tool and joint positions.
        :param joints: joint values as a dict
        :return: RobotPosition object for given joints positions
        """

        # read raw joint values
        y = joints['y']
        x = joints['x']
        z = joints['z']
        a = joints['azimuth']
        tilt_slider = joints['tilt_slider']

        # Voicecoil is redundant with z-axis. The default mode of operations is that
        # voicecoil acts as a spring and is ignored in IK/FK calculations. The current setpoint of voicecoil
        # joint is used instead of joint position to enable spring-like behavior.
        vc1_setpoint = axis_setpoints["voicecoil1"]

        # joints to xyz frame
        m_xyz = robotmath.xyz_to_frame(x, y, -(z + vc1_setpoint))

        # azimuth frame
        m_azi = robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, -a)

        # Total offset of slider from azimuth axis.
        tilt_slider_total = self.tilt_slider_zero_position + tilt_slider

        # Stylus holder straight line mechanism lateral movement
        m_slider = robotmath.xyz_to_frame(tilt_slider_total, 0, 0)

        # Positive direction of linear joint rotates tilting joint counter-clockwise
        tilt_joint = np.pi/2 - np.arccos(tilt_slider_total / (2*self.sr_link_length))  # result in radians

        # Tilting movement is around y-axis
        m_tilt = robotmath.xyz_euler_to_frame(0, 0, 0, 0, np.degrees(tilt_joint), 0)

        m_tool = self.compute_tool_transform(kinematic_name)

        if kinematic_name == "azimuth":
            m_f = m_xyz * m_azi * self._tool_orientation * m_tool
        else:
            # xyz + azimuth + slider + tilt + mounting flange orientation (down) + 15 deg rotation offset + tool offset
            m_f = m_xyz * m_azi * m_slider * m_tilt * self._tool_orientation * self._rotation_offset * m_tool

        return self.create_robot_position(frame=m_f, voicecoil1=vc1_setpoint)

    def _robot_ik(self, pos: RobotPosition, axis_setpoints: dict, kinematic_name=None):

        m_tool = self.compute_tool_transform(kinematic_name)
        m_tool_i = robotmath.inv_oht(m_tool)

        # effective frame to flange frame
        m_f = pos.frame * m_tool_i * self._rotation_offset_i * self._tool_orientation_i

        # Get tilt angle in degrees
        _, _, _, _, b, _ = robotmath.frame_to_xyz_euler(m_f)

        # Required tilt angle for stylus. Compute corresponding linear slider joint value
        tilt = np.pi/2 - np.radians(b)

        # Total offset of slider from azimuth axis.
        tilt_slider_total = np.cos(tilt) * 2 * self.sr_link_length

        # Tilt slider joint value.
        tilt_slider = tilt_slider_total - self.tilt_slider_zero_position

        azimuth = determine_robot_azimuth(m_f, axis_setpoints["azimuth"])

        # Tilting movement is around y-axis
        m_tilt = robotmath.xyz_euler_to_frame(0, 0, 0, 0, b, 0)

        # Stylus holder straight line mechanism lateral movement
        m_slider = robotmath.xyz_to_frame(tilt_slider_total, 0, 0)

        # azimuth frame
        m_azi = robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, -azimuth)

        x, y, z, _, _, _ = robotmath.frame_to_xyz_euler(m_f * robotmath.inv_oht(m_azi * m_slider * m_tilt))

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

            if kinematic_name == "azimuth":
                m_f = pos.frame * robotmath.inv_oht(m_tool) * self._tool_orientation_i  # effective frame to flange frame
                x, y, z, _, _, _ = robotmath.frame_to_xyz_euler(m_f * robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, azimuth))
                tilt_slider = axis_setpoints["tilt_slider"]

            z_joint = -z - vc_joint

        joints = {'y': y, 'x': x, 'z': z_joint, 'azimuth': azimuth, 'voicecoil1': vc_joint, 'tilt_slider': tilt_slider}

        return joints

    def _camera_fk(self, joints):
        x = joints['x']
        y = joints['y']
        z = joints['z']
        axis_setpoints = self.get_scaled_axis_setpoints()
        vc1 = axis_setpoints["voicecoil1"]
        tilt_slider = axis_setpoints["tilt_slider"]
        frame = robotmath.xyz_euler_to_frame(x, y, -z, 180, 0, 180)

        return self.create_robot_position(frame=frame, voicecoil1=vc1, tilt_slider=tilt_slider)

    def _camera_ik(self, pos: RobotPosition):
        x, y, z = robotmath.frame_to_xyz(pos.frame)

        joints = {'y': y, 'x': x, 'z': -z}

        if pos.voicecoil1 is not None:
            joints["voicecoil1"] = pos.voicecoil1
            joints["tilt_slider"] = pos.tilt_slider

        return joints

    def calibrate(self, parameters):

        measurements = parameters["measurements"]

        # Use the same computation algorithm as in Synchro robot, but take tilt slider offset into account in final
        # result
        camera_offset, tool_offset, residual_error = calculate_synchro_tool_camera_offsets(measurements=measurements)

        # The calibration algorithm gives the tool offset in robot base frame orientation and this has been implemented
        # for the synchro kinematics.
        # The calibration procedure for synchro uses FK transformation m_xyza * m_tool_synchro * m_tool_orientation
        # whereas stylus kinematics uses FK transformation m_xyza * m_tool_orientation * m_tool_stylus.
        # It could be argued that the synchro FK is not intuitively correct but changing it would break compatibility.
        # We can solve m_tool_stylus = m_tool_orientation^-1 * m_tool_synchro * m_tool_orientation.
        # Because tool frames have identity rotation part this amounts to changing the sign of x and z translation
        # components of the tool frame while y component remains unchanged. Only x and y components are
        # actually returned.
        tool_offset[0] = self.tilt_slider_zero_position - tool_offset[0]

        result = {
            "tool_offset": tool_offset.tolist(),
            "camera_offset": camera_offset.tolist(),
            "residual_error": residual_error
        }

        return result

    def homing_sequence(self):
        # home axes
        # Voicecoil is homed twice just in case, because after recovering from emergency stop it can end up in the
        # wrong home position (too low).
        # z and azimuth are homed twice with move in-between to overcome issue with homing from home-switch.
        sequence = [
            ("home", ['z', 'tilt_slider', 'x', 'azimuth', 'y', 'voicecoil1', 'voicecoil1']),
            ("move", {'z': 10}),
            ("home", ['z']),
            ("move", {'azimuth': 45}),
            ("home", ['azimuth']),

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

        return self.axis_specs

    def arc_r(self, toolframe=None, kinematic_name=None):
        # TODO: This determines azimuth rotation speed when xyz is stationary. Should this be configurable?
        return 50
