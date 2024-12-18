import numpy as np
import logging
import tntserver.robotmath as robotmath
from tntserver.drivers.robots import sm_regs
from tntserver.drivers.robots.goldenmov import RobotKinematics
from tntserver.drivers.robots.goldenmov.kinematics import append_post_homing_move
import math

log = logging.getLogger(__name__)


def filter_frame_xyza(frame):
    """
    Filter frame so that xyz-azimuth IK can be applied.
    Removes other rotations (in workspace coordinates) than rotation around workspace z axis (azimuth).
    :param frame: Frame to be filtered.
    :return: Filtered frame.
    """

    bx = robotmath.get_frame_x_basis_vector(frame)
    by = robotmath.get_frame_y_basis_vector(frame)

    # Force z-basis vector to point down in workspace.
    bz = np.array([0, 0, -1])

    # Normalize other basis vectors to represent direction on z = constant plane.
    bx[2] = 0.0
    bx = bx / np.linalg.norm(bx)

    by[2] = 0.0
    by = by / np.linalg.norm(by)

    # Set basis vectors.
    filtered = frame.copy()
    robotmath.set_frame_x_basis_vector(filtered, bx)
    robotmath.set_frame_y_basis_vector(filtered, by)
    robotmath.set_frame_z_basis_vector(filtered, bz)

    return filtered


def determine_robot_azimuth(target_rotation, current_azimuth):
    """
    Determine robot azimuth axis value corresponding to target frame.
    The axis value can be in range [-inf, inf] whereas the target frame can only describe angles
    within one revolution (e.g. [-180, 180]). Hence extra information is needed to determine the azimuth angle
    uniquely. This function utilizes known current robot azimuth angle to do that i.e. to map angle from
    [-180, 180] to [-180 + n*360, 180 + n*360] for integer n that is determined by current azimuth.
    :param target_rotation: 4x4 matrix that describes that target rotation of the robot. This is transform from ws to xyza.
    :param current_azimuth: Robot azimuth joint current value in degrees.
    :return: Azimuth angle in range [-inf, inf] in correct revolution specified by current_azimuth.
    """
    current_azimuth_rad = math.radians(current_azimuth)

    # The idea here is to first compute the signed angle difference between direction vectors that correspond
    # to target frame and to current azimuth angle. Then this difference is added to the current azimuth angle.
    # Hence the resulting angle will always be in the correct domain of revolution regardless if it crosses
    # angle pole values imposed by direct conversion from frame->angle.

    # Extract y-basis vector of frame.
    target_y_dir = target_rotation.A[0:2, 1]

    # Calculate y-basis corresponding current azimuth angle.
    current_y_dir = np.matrix([math.sin(current_azimuth_rad), math.cos(current_azimuth_rad)]).T

    target_y_dir_len = np.linalg.norm(target_y_dir)
    current_y_dir_len = np.linalg.norm(current_y_dir)

    d = np.dot(target_y_dir, current_y_dir) / (target_y_dir_len * current_y_dir_len)

    # Make sure d is in valid range for acos() in case of round-off errors.
    d = np.clip(d, -1.0, 1.0)

    # Compute the span angle of two vectors.
    # Note that this can be at most 180 degrees.
    angle_delta = math.degrees(math.acos(d))

    # Use cross-product to determine sign of rotation angle.
    if target_y_dir[0] * current_y_dir[1] - target_y_dir[1] * current_y_dir[0] < 0:
        angle_delta = -angle_delta

    return current_azimuth + angle_delta


def calculate_synchro_tool_camera_offsets(measurements):
    """
    Compute synchro finger and camera x, y offsets from given measurement data.
    Measurement consists of robot position when finger is at sync point (e.g. Audit gauge) and robot
    position when camera center is at sync point. Such measurements are performed with multiple finger rotation
    angles around full circle. The angle is expected to behave so that rotation from zero to +90 deg
    rotates +x to -y.
    :param measurements: List of tuples (angle_radians, robot_finger_x, robot_finger_y, robot_camera_x, robot_camera_y).
    :return: Tuple (camera_offset, finger_offset, residual_error).
    """
    num_angles = len(measurements)

    # Declare least-squares elements for Ax = b form.
    A = np.zeros([2 * num_angles, 4])
    b = np.zeros([2 * num_angles])

    for i, measurement in enumerate(measurements):
        angle = measurement[0]
        robot_finger = np.array([measurement[1], measurement[2]])
        robot_camera = np.array([measurement[3], measurement[4]])

        c = math.cos(angle)
        s = math.sin(angle)

        # LSQ problem is obtained by requiring that finger and camera are at the same position (e.g. Audit gauge).
        # This leads to equation robot_camera + camera_offset = robot_finger + R(angle) * finger_offset
        # where R(angle) = [cos(angle)  sin(angle)]
        #                  [-sin(angle) cos(angle)]
        # Note that R(+90 deg) rotates x-axis to -y-axis.
        # Two matrix rows for current angle (one for each position coordinate).
        A[2 * i, :] = [1, 0, -c, -s]
        A[2 * i + 1, :] = [0, 1, s, -c]

        # Two corresponding RHS vector rows.
        b[(2 * i):(2 * i + 2)] = robot_finger - robot_camera

    # Solve the over-determined problem in the least-squares sense.
    result = np.linalg.lstsq(A, b, rcond=None)

    camera_offset = result[0][0:2]
    finger_offset = result[0][2:4]
    residual_error = result[1][0]

    return camera_offset, finger_offset, residual_error


class RobotPosition(RobotKinematics.RobotPositionBase):
    __slots__ = ["frame", "separation", "voicecoil1", "voicecoil2", "d", "t"]
    pass


class Kinematic_synchro(RobotKinematics):
    """
    Kinematics implementation synchrofinger+azimuth robot where both fingers have voicecoil actuator

    """
    name = "synchro"

    def __init__(self, robot, axis_specs=None):

        if axis_specs is not None:
            self.axis_specs = axis_specs
        else:
            # default settings if no configuration is given
            self.axis_specs = {
                1: {'alias': 'y', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001,
                    'post_homing_move': 15},
                32: {'alias': 'x', 'homing_priority': 1, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.005,
                     'post_homing_move': 15},
                31: {'alias': 'z', 'homing_priority': 3, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
                22: {'alias': 'azimuth', 'homing_priority': 1, 'acceleration': 500, 'velocity': 500,
                    'move_tolerance': 0.005},
                21: {'alias': 'separation', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500,
                    'move_tolerance': 0.001},
                11: {'alias': 'voicecoil1', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500,
                    'move_tolerance': 0.001, 'press_margin': 1},
                12: {'alias': 'voicecoil2', 'homing_priority': 2, 'acceleration': 500, 'velocity': 500,
                    'move_tolerance': 0.001, 'press_margin': 1}
            }

        super().__init__(robot, RobotPosition)

        # Keep track of separation value.
        # Note: this corresponds to separation joint setpoint when in position control model.
        # Note that this should normally be avoided but separation axis may be controlled in torque mode
        # when using e.g. "gripping".
        self._separation = None

        # Default tool orientation in relation to robot base.
        # This is the final transformation in the forward kinematics chain to make the robot local z-axis point
        # "down" i.e. along negative robot base z-axis.
        self._tool_orientation = robotmath.xyz_euler_to_frame(0, 0, 0, 180, 0, 180)
        self._tool_orientation_i = self._tool_orientation.I

    @property
    def tool1_offset(self):
        """
        Fixed affine transform after azimuth rotation to the home position of the first finger.
        This should mainly be a negative translation along local x-axis.
        """
        offset = self.calibration_data["tool1_offset"]

        # offset should be a list of lists that is interpreted as 4x4 matrix.
        assert type(offset) is list

        return np.matrix(offset)

    @property
    def tool2_offset(self):
        """
        Fixed affine transform after azimuth rotation to the home position of the second finger.
        This should mainly be a positive translation along local x-axis.
        """

        offset = self.calibration_data["tool2_offset"]

        # offset should be a list of lists that is interpreted as 4x4 matrix.
        assert type(offset) is list

        return np.matrix(offset)

    @property
    def home_separation(self):
        """
        Axis-to-axis finger separation distance at finger home position.
        """

        # Separation is assumed to be along local x-axis (after azimuth rotation).
        return self.tool2_offset.A1[3] - self.tool1_offset.A1[3]

    @property
    def separation(self):
        """
        Get separation set point previously set by kinematics.
        If no set point has been set, the home separation is returned.
        This property can be used when no separation value is provided for IK.
        """
        if self._separation is None:
            return self.home_separation

        return self._separation

    def check_dynamic_position_limits(self, positions):
        """
        Check that dynamically changing axis position limits are not violated. For example, minimum allowed separation
        joint position depends on the size (diameter) of currently attached tips. Exception is thrown if minimum limit
        is violated.
        :param positions: Dictionary of buffered move positions.
        :return: None.
        """
        if 'separation' in positions:

            # Test only the minimum commanded separation joint value.
            min_separation = np.min(positions['separation'])

            # Get all attached tips.
            attached_tips = [mount.tool.tip for mount in self.robot.children.values() if mount.tool is not None]

            # Calculate gap between finger axes.
            tool1_axis = self.tool1_offset * robotmath.xyz_to_frame(-min_separation / 2, 0, 0)
            tool2_axis = self.tool2_offset * robotmath.xyz_to_frame(min_separation / 2, 0, 0)
            finger_axis_gap = tool2_axis.A1[3] - tool1_axis.A1[3]

            # Get radii of tips.
            r = [tip.diameter / 2.0 for tip in attached_tips if tip is not None]
            if sum(r) > finger_axis_gap:
                raise Exception("Finger separation cannot reach {:.3f} mm due to the size of currently attached tips."
                                .format(finger_axis_gap))

    def _joints_to_position(self, joints: dict, kinematic_name=None, tool=None, calibrated=False) -> RobotPosition:
        if kinematic_name is not None and kinematic_name == 'camera':
            pos = self._camera_fk(joints)
        else:
            pos = self._robot_fk(joints, kinematic_name)
        if tool is not None:
            pos.frame = pos.frame * tool
        return pos

    def positions_to_joints(self, positions: list, kinematic_name=None, tool_inv=None, calibrated=False) -> list:
        axis_setpoints = self.get_scaled_axis_setpoints()

        # Call base class method on position values
        joints = self._positions_to_joints(positions=positions, axis_setpoints=axis_setpoints,
                                           kinematic_name=kinematic_name, tool_inv=tool_inv)

        # If separation axis is in torque mode, do not specify separation joint value.
        # Optomotion will set axis control mode to position control if values are provided for given axis.
        # Such behavior does not work with torque mode gripping for multifinger tools.
        if self.driver.get_axis_parameter("separation", sm_regs.SMP_CONTROL_MODE) == sm_regs.CM_TORQUE:
            for joint in joints:
                if "separation" in joint:
                    del joint["separation"]

        return joints

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

    def compute_tool_transform(self, kinematic_name, separation_joint):
        """
        Compute tool matrix that transforms a vector from separated finger position
        to a position after xyz-azimuth transform.
        :param kinematic_name: Name of kinematic to use.
        :param separation_joint: Separation axis joint value.
        :return: Transform as numpy matrix.
        """
        if kinematic_name == "tool1":
            return self.tool1_offset * robotmath.xyz_to_frame(-separation_joint / 2, 0, 0)
        elif kinematic_name == "tool2":
            return self.tool2_offset * robotmath.xyz_to_frame(separation_joint / 2, 0, 0)
        elif kinematic_name == "mid":
            # Middle position between the two tools.
            x1, y1, z1 = robotmath.frame_to_xyz(self.tool1_offset)
            x2, y2, z2 = robotmath.frame_to_xyz(self.tool2_offset)
            return robotmath.xyz_to_frame((x1 + x2) * 0.5, (y1 + y2) * 0.5, (z1 + z2) * 0.5)
        elif kinematic_name == "synchro":
            # This corresponds to synchro mount point i.e. position after x, y, z, azimuth.
            return robotmath.identity_frame()
        else:
            raise Exception("unknown kinematic name {} given for joints_to_position".format(kinematic_name))

    def _robot_fk(self, joints: dict, kinematic_name) -> RobotPosition:
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

        # If in torque mode, calculate separation joint position from separation book-keeping.
        if self.driver.get_axis_parameter("separation", sm_regs.SMP_CONTROL_MODE) == sm_regs.CM_TORQUE:
            separation_joint = self.separation - self.home_separation
        else:
            separation_joint = joints['separation']

        # Voicecoil is redundant with z-axis. The default mode of operations is that
        # voicecoil acts as a spring and is ignored in IK/FK calculations. The current setpoint of voicecoil
        # joint is used instead of joint position to enable spring-like behavior.
        axis_setpoints = self.get_scaled_axis_setpoints()
        vc1 = axis_setpoints["voicecoil1"]
        vc2 = axis_setpoints["voicecoil2"]

        # joints to xyz frame
        m_xyz = robotmath.xyz_to_frame(x, y, -z)

        # azimuth frame
        m_azi = robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, -a)

        # Compute tool matrix that transform after azimuth rotation to the separated finger position.
        m_tool = self.compute_tool_transform(kinematic_name, separation_joint)

        # xyz + azimuth + synchro separation + tool orientation (down)
        m_f = m_xyz * m_azi * m_tool * self._tool_orientation

        # Compute finger axis-to-axis separation.
        separation = self.home_separation + separation_joint

        self._separation = separation

        return self.create_robot_position(frame=m_f, separation=separation, voicecoil1=vc1, voicecoil2=vc2)

    def _robot_ik(self, pos: RobotPosition, axis_setpoints, kinematic_name):

        # Finger axis-to-axis separation
        separation = pos.separation if pos.separation is not None else self.separation

        # separation joint value from finger axis-to-axis separation
        separation_joint = separation - self.home_separation

        # Compute tool matrix that transform after azimuth rotation to the separated finger position.
        m_tool = self.compute_tool_transform(kinematic_name, separation_joint)

        # effective frame
        # TODO: Check if m_tool.I is too expensive to compute.
        m_f = pos.frame * self._tool_orientation_i * m_tool.I

        # write joints
        x, y, z, a, b, c = robotmath.frame_to_xyz_euler(m_f)

        azimuth = determine_robot_azimuth(m_f, axis_setpoints["azimuth"])

        # Update reference azimuth value to make next IK computation more accurate.
        # This is required for cases when the planned motion rotates azimuth >= 180 degrees.
        # Especially this handles case where azimuth is rotated 180 degrees + epsilon (due to e.g. round-off).
        # Such rotation can often happen when picking tip, moving to screenshot position etc.
        axis_setpoints["azimuth"] = azimuth

        joints = {'y': y, 'x': x, 'z': -z, 'azimuth': azimuth}
        if separation_joint is not None:
            joints['separation'] = separation_joint
        if pos.voicecoil1 is not None:
            joints["voicecoil1"] = pos.voicecoil1
        if pos.voicecoil2 is not None:
            joints["voicecoil2"] = pos.voicecoil2
        return joints

    def _camera_fk(self, joints):
        x = joints['x']
        y = joints['y']
        z = joints['z']

        # If in torque mode, calculate separation joint position from separation book-keeping.
        if self.driver.get_axis_parameter("separation", sm_regs.SMP_CONTROL_MODE) == sm_regs.CM_TORQUE:
            separation_joint = self.separation - self.home_separation
        else:
            separation_joint = joints['separation']

        axis_setpoints = self.get_scaled_axis_setpoints()
        vc1 = axis_setpoints["voicecoil1"]
        vc2 = axis_setpoints["voicecoil2"]

        # Compute finger axis-to-axis separation.
        separation = self.home_separation + separation_joint

        frame = robotmath.xyz_euler_to_frame(x, y, -z, 180, 0, 180)
        return self.create_robot_position(frame=frame, separation=separation, voicecoil1=vc1, voicecoil2=vc2)

    def _camera_ik(self, pos: RobotPosition):
        x, y, z = robotmath.frame_to_xyz(pos.frame)

        # Finger axis-to-axis separation
        separation = pos.separation if pos.separation is not None else self.separation

        # separation joint value from finger axis-to-axis separation
        separation_joint = separation - self.home_separation

        joints = {'y': y, 'x': x, 'z': -z}

        if separation_joint is not None:
            joints['separation'] = separation_joint
        if pos.voicecoil1 is not None:
            joints["voicecoil1"] = pos.voicecoil1
        if pos.voicecoil2 is not None:
            joints["voicecoil2"] = pos.voicecoil2

        return joints

    def calibrate(self, parameters):

        measurements = parameters["measurements"]
        camera_offset, tool_offset, residual_error = calculate_synchro_tool_camera_offsets(measurements)
        result = {
            "tool_offset": tool_offset.tolist(),
            "camera_offset": camera_offset.tolist(),
            "residual_error": residual_error
        }
        return result

    def homing_sequence(self):
        # Test specifications for after homing position limit check for voice coils.
        kinematic_specs = self.specs()
        axis_limit_test_specs = {'voicecoil1': {},
                                 'voicecoil2': {}}

        # voice_coil_homing_current is 1000 mA as default and peak current is 1000 mA as default
        voicecoil1_homing_current = 1000
        voicecoil2_homing_current = 1000
        voicecoil1_peak_homing_current = 1360
        voicecoil2_peak_homing_current = 1360

        for axis in axis_limit_test_specs.keys():
            for kinematic_spec in kinematic_specs.values():
                if kinematic_spec['alias'] == axis:
                    axis_limit_test_specs[axis]['retry_limit'] = kinematic_spec.get('retry_limit', 5)
                    axis_limit_test_specs[axis]['limit_check_tolerance'] = kinematic_spec.get('limit_check_tolerance',
                                                                                              0.05)
                    axis_limit_test_specs[axis]['speed'] = kinematic_spec.get('velocity', 100)
                    axis_limit_test_specs[axis]['acceleration'] = kinematic_spec.get('acceleration', 400)
                    axis_limit_test_specs[axis]['settling_timeout'] = kinematic_spec.get('settling_timeout', 5)
                    if axis == 'voicecoil1':
                        voicecoil1_homing_current = kinematic_spec.get('voicecoil_homing_current', 1000)
                        voicecoil1_peak_homing_current = kinematic_spec.get('voicecoil_peak_homing_current', 1000)
                    elif axis == 'voicecoil2':
                        voicecoil2_homing_current = kinematic_spec.get('voicecoil_homing_current', 1000)
                        voicecoil2_peak_homing_current = kinematic_spec.get('voicecoil_peak_homing_current', 1000)
                    break

        # home axes
        # Voicecoils are homed twice just in case, because after recovering from emergency stop they can end up in the
        # wrong home position (too low).
        # z and azimuth are homed twice with move in-between to overcome issue with homing from home-switch.
        vc1_cont_current_limit = self.driver._comm.get_axis_parameter("voicecoil1", sm_regs.SMP_TORQUELIMIT_CONT)
        vc2_cont_current_limit = self.driver._comm.get_axis_parameter("voicecoil2", sm_regs.SMP_TORQUELIMIT_CONT)
        vc1_peak_current = self.driver._comm.get_axis_parameter("voicecoil1", sm_regs.SMP_TORQUELIMIT_PEAK)
        vc2_peak_current = self.driver._comm.get_axis_parameter("voicecoil2", sm_regs.SMP_TORQUELIMIT_PEAK)

        sequence = [
            # Set voicecoil continuous current limits to given values
            ("set_axis_parameter", {"axis": "voicecoil1", "param": sm_regs.SMP_TORQUELIMIT_CONT,
                                    "value": voicecoil1_homing_current}),
            ("set_axis_parameter", {"axis": "voicecoil2", "param": sm_regs.SMP_TORQUELIMIT_CONT,
                                    "value": voicecoil2_homing_current}),
            ("set_axis_parameter", {"axis": "voicecoil1", "param": sm_regs.SMP_TORQUELIMIT_PEAK,
                                    "value": voicecoil1_peak_homing_current}),
            ("set_axis_parameter", {"axis": "voicecoil2", "param": sm_regs.SMP_TORQUELIMIT_PEAK,
                                    "value": voicecoil2_peak_homing_current}),
            ("home", ['z', 'x', 'separation', 'azimuth', 'y', 'voicecoil1', 'voicecoil2', 'voicecoil1', 'voicecoil2']),
            ("check_axis_position_limits", axis_limit_test_specs),
            ("move", {'z': 10}),
            ("home", ['z']),
            ("move", {'azimuth': 45}),
            ("home", ['azimuth']),
            # Restore the original voicecoil values
            ("set_axis_parameter", {"axis": "voicecoil1", "param": sm_regs.SMP_TORQUELIMIT_CONT,
                                    "value": vc1_cont_current_limit}),
            ("set_axis_parameter", {"axis": "voicecoil2", "param": sm_regs.SMP_TORQUELIMIT_CONT,
                                    "value": vc2_cont_current_limit}),
            ("set_axis_parameter", {"axis": "voicecoil1", "param": sm_regs.SMP_TORQUELIMIT_PEAK,
                                    "value": vc1_peak_current}),
            ("set_axis_parameter", {"axis": "voicecoil2", "param": sm_regs.SMP_TORQUELIMIT_PEAK,
                                    "value": vc2_peak_current})
        ]

        # Default move in case axis spec is not defined is for compatibility with previous deliveries.
        if self.axis_specs is None:
            # Move x and y axes away from zero position to allow for movements with possible azimuth rotation.
            sequence.append(("move", {'x': 15, 'y': 15}))
        else:
            append_post_homing_move(sequence, self.axis_specs)

        return sequence

    def specs(self):
        # These specs are not saved in drives, instead TnT level configuration
        # For x, y, z:
        # Acceleration mm/s^2, velocity mm/s
        # For azimuth, tilt:
        # Acceleration degree/s^2, velocity degrees/s
        return self.axis_specs

    def set_specs(self, axis_specs):
        """
        Sets axis_specs dict. Also adds press_margin to voicecoils if it is not given.
        :param axis_specs: Value that is given to self.axis_specs.
        """
        # If voicecoils don't have press_margin given add press_margin 1mm for them as default value
        for axis in axis_specs:
            if axis_specs[axis]['alias'] == 'voicecoil1' or axis_specs[axis]['alias'] == 'voicecoil2':
                if 'press_margin' not in axis_specs[axis]:
                    axis_specs[axis].update({'press_margin': 1})

        self.axis_specs = axis_specs

    def arc_r(self, toolframe=None, kinematic_name=None):
        if toolframe is None or kinematic_name is None:
            raise Exception("Synchro kinematics requires toolframe and kinematic name for arc_r().")

        position = self.driver.position(tool=toolframe, kinematic_name=kinematic_name)

        arc_r = position.separation / 2 if position.separation is not None else 50   # safe rotational speed

        return arc_r


