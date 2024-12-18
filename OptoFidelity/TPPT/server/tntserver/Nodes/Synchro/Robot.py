import numpy as np
import logging
import tntserver.Nodes.TnT.Robot
import tntserver.drivers.robots.sm_regs as SMRegs
from tntserver.drivers.robots.goldenmov import AxisParameterContext
from tntserver.drivers.robots.golden_program import LinePrimitive
from tntserver.Nodes.Node import json_out, skip_nones, private, NodeException, Node
from tntserver.Nodes.TnT.PhysicalButton import PhysicalButton
from tntserver.Nodes.NodeSurfaceProbe import RobotSurfaceProbe
from tntserver.Nodes.TnT.Workspace import get_node_workspace
from tntserver import robotmath
from .tip_changer import SynchroFingerTipChanger
from .Gestures import VoicecoilMaxContCurrent

# Hardcode logger name to get logging under same name as normal TnT.Robot node logs
log = logging.getLogger('tntserver.Nodes.TnT.Robot')


class Robot(tntserver.Nodes.TnT.Robot.Robot):
    def __init__(self, name):
        super().__init__(name)

    def _init(self, **kwargs):
        # If multifinger is attached according to config, ask user to remove it before homing can proceed.
        if self.has_multifinger():
            input("Please remove multifinger from robot. Then press Enter to continue homing.")

            mount = self.find_mount("tool1")
            mount.tool.tip.remove_object_from_parent()

            # TODO: Tip status is not updated to config. For some reason self.save() does not work if invoked here.

        # For compatibility use open loop force by default.
        if "force_driver" not in kwargs:
            kwargs["force_driver"] = "open_loop_force"

        # call the original _init from TnT.Robot
        super()._init(**kwargs)

        # Assign robot a tip changer.
        self._tip_changer = SynchroFingerTipChanger(self)

        self._tip_changer.max_tip_change_speed = kwargs.get("max_tip_change_speed", 100.0)
        self._tip_changer.max_tip_change_acceleration = kwargs.get("max_tip_change_acceleration", 300.0)

        # Get maximum voicecoil current from configuration. Default is 1360 mA
        self.max_voicecoil_current = kwargs.get('max_voicecoil_current', 1360)

        # Set the force limit for voice coils to configured values. Default value 500 mA corresponds to about 215g.
        default_voicecoil_current = kwargs.get('default_voicecoil_current', 500)
        self.set_torque_limit('voicecoil1', default_voicecoil_current)
        self.set_torque_limit('voicecoil2', default_voicecoil_current)

        # Define voicecoil current for multifinger pick/drop operation
        pick_drop_current = kwargs.get(
            'voicecoil_multifinger_pick_drop_current', self.max_voicecoil_current)  # [mA]
        if pick_drop_current > self.max_voicecoil_current:
            log.warning("voicecoil_multifinger_pick_drop_current: {}mA is higher than allowed maximum {}mA. \
            Using maximum allowed value.".format(pick_drop_current, self.max_voicecoil_current))
        self.voicecoil_multifinger_pick_drop_current = min(pick_drop_current, self.max_voicecoil_current)

        # Add automatic surface z-height probe
        self._surface_probe = SynchroSurfaceProbe(robot=self)

        # Store separation axis parameters for the duration of gripping.
        self._gripping_separation_parameters = None

        # Get the current that separation axis uses when gripping a grippable tip
        self._continuous_separation_gripping_current = kwargs.get('continuous_separation_gripping_current', 500.0)
        self._peak_separation_gripping_current = kwargs.get('peak_separation_gripping_current', 500.0)

        # Get gripping distance that is used to move separation axis when gripping to a grippable tip.
        self._separation_gripping_distance = kwargs.get('separation_gripping_distance', -5.0)

        # Get gripping mode. Can be 'position', or 'torque'.
        self._separation_gripping_mode = kwargs.get('separation_gripping_mode', 'position')

        if self._separation_gripping_mode not in ['position', 'torque']:
            raise Exception("Robot argument 'separation_gripping_mode' must be 'position' or 'torque'.")

        # Get gripping torque setpoint that is used if mode is 'torque'.
        # Value -3000 seems to be ok for synchro to grip inwards. Default value is 0 to be safe.
        self._separation_gripping_torque_setpoint = kwargs.get('separation_gripping_torque_setpoint', 0)

    @json_out
    def put_home(self):
        """
        Commands the robot to go into home position.
        """
        # Prevent homing via API if multifinger is attached.
        if self.has_multifinger():
            raise NodeException("Cannot home while multifinger is attached.")

        self.driver.home()
        self.program.reset()

    def read_torque_limit(self, axis_name):
        """
        Read current axis torque limit
        :param axis_name: The axis that torque limit should be read for
        :return: Torque limit in milliamperes
        """
        current_cont_limit = self.driver.read_axis_parameter(axis_name, SMRegs.SMP_TORQUELIMIT_CONT)

        return current_cont_limit

    def set_torque_limit(self, axis_name, torque_limit):
        """
        Set axis torque limit
        :param axis_name: The axis that torque limit should be set for
        :param torque_limit: Torque limit in milliamperes
        :return:
        """
        if torque_limit > self.max_voicecoil_current:
            log.warning('Force exceeds maximum torque limit for motor. Clipping torque to {} mA.'.format(
                int(self.max_voicecoil_current)))
            torque_limit = self.max_voicecoil_current

        self.driver.set_axis_parameter(axis_name, SMRegs.SMP_TORQUELIMIT_PEAK, torque_limit)
        self.driver.set_axis_parameter(axis_name, SMRegs.SMP_TORQUELIMIT_CONT, torque_limit)

    @json_out
    def put_axis_position(self, axis: str, value):
        """
        Moves only one axis
        :param axis: axis name
        :param value: target position value
        :return:
        """
        self.set_axis_position(axis, value)

    @json_out
    def get_axis_position(self, axis: str):
        """
        Get current position of one axis
        :param axis: axis name
        :return: axis current position value
        """
        return self.axis_position(axis)

    @json_out
    def get_axis_parameter(self, axis, parameter):
        """
        get SimpleMotion axis parameter value
        :param axis: axis name
        :param parameter: parameter name
        :return: value (integer)
        """
        value = self.read_axis_parameter(axis, parameter)
        return value

    def read_axis_parameter(self, axis_name, parameter):
        return self.driver.read_axis_parameter(axis_name, parameter)

    @json_out
    def put_axis_parameter(self, axis, parameter, value):
        """
        set SimpleMotion axis parameter value
        :param axis: axis name
        :param parameter: parameter name
        :param value: value (integer)
        :return:
        """
        self.set_axis_parameter(axis, parameter, value)

    def set_axis_parameter(self, axis_name, parameter, value):
        self.driver.set_axis_parameter(axis_name, parameter, value)

    @json_out
    def put_finger_separation(self, distance, kinematic_name=None):
        """
        Set separation of two fingers in mm. Separation distance is measured from finger axes.
        :param distance: Distance in mm.
        :param kinematic_name: Name of kinematic to use for the motion. If None then currently active kinematic is used.
        :return: Dictionary with "status" key.
        """
        if self.has_multifinger():
            raise NodeException("Can't change finger separation while multifinger is attached!")

        self.set_axis_position("separation", distance, kinematic_name=kinematic_name)

        return {"status": "ok"}

    @json_out
    def get_finger_separation(self):
        """
        Get separation of two fingers in mm.
        :return: Separation distance in mm.
        """
        return self.axis_position("separation")

    @json_out
    def get_finger_separation_limits(self):
        """
        Get minimum and maximum axis-to-axis separation values.
        :return: Minimum and maximum values as list [min_separation, max_separation].
        """
        return self.driver.get_finger_separation_limits()

    def move_voicecoils(self, target_position):
        """
        Move voicecoils from their current positions to given target position simultaneously.
        They will arrive at target at the same time. The voicecoil which has longer distance to target
        uses the current robot speed and acceleration. The other voicecoil will use smaller or equal speed.
        :param target_position: Voicecoil position in mm. Positive direction is along effector local z ("down").
        """
        log.debug("Moving voicecoils to position {}.".format(target_position))

        prg = self.program

        # Kinematic name does not matter as we are moving only voicecoils. Need to choose some so use tool1.
        kinematic_name = "tool1"
        toolframe = self.tool_frame(kinematic_name)

        prg.begin(ctx=self.object_parent, toolframe=toolframe, kinematic_name=kinematic_name)
        prg.set_speed(self.robot_velocity, self.robot_acceleration)

        current_position = self.driver.position(tool=toolframe, kinematic_name=kinematic_name)

        # Line where the frame is kept at current position but voicecoils go from their current positions
        # to target position.
        p = LinePrimitive(current_position.frame, current_position.frame,
                           axes={'voicecoil1': [current_position.voicecoil1, target_position],
                           'voicecoil2': [current_position.voicecoil2, target_position]})

        prg.move(p)
        prg.run()

    @json_out
    def put_move_voicecoils(self, target_position):
        """
        Move voicecoils from their current positions to given target position simultaneously.
        They will arrive at target at the same time. The voicecoil which has longer distance to target
        uses the current robot speed and acceleration. The other voicecoil will use smaller or equal speed.
        :param target_position: Voicecoil position in mm. Positive direction is along effector local z ("down").
        """
        self.move_voicecoils(target_position)

    @property
    @private
    def default_separation(self):
        """
        Default separation is finger separation that can be used if there is no
        strict requirement for separation.
        :return:
        """
        # Add some margin to home separation to avoid round-off error when computing separation joint value.
        return float(self.driver._kinematics.home_separation + 1.0)

    @json_out
    def get_default_separation(self):
        return self.default_separation

    def grip_with_separation_axis(self, separation):
        """
        Grip anything with the separation axis by moving the two fingers closer to each other.
        Increases the tracking and velocity error thresholds so the axis does not induce tracking errors while holding
        the grip.
        :param separation: Separation value in ungripped state.
        :return:
        """
        log.debug("Gripping with separation axis.")

        grip_separation = separation + self._separation_gripping_distance

        continuous_current_limit = self.driver.get_axis_parameter("separation", SMRegs.SMP_TORQUELIMIT_CONT)
        peak_current_limit = self.driver.get_axis_parameter("separation", SMRegs.SMP_TORQUELIMIT_PEAK)

        if self._continuous_separation_gripping_current <= continuous_current_limit:
            continuous_current_limit = self._continuous_separation_gripping_current
        else:
            log.warning("Continuous separation gripping current: {} mA is higher than currently set value {} mA. \
                    Using the current value.".format(self._continuous_separation_gripping_current, continuous_current_limit))

        if self._peak_separation_gripping_current <= peak_current_limit:
            peak_current_limit = self._peak_separation_gripping_current
        else:
            log.warning("Peak separation gripping current: {} mA is higher than currently set value {} mA. \
                    Using the current value.".format(self._peak_separation_gripping_current, peak_current_limit))

        # Set position tracking error which allows grip separation to be applied.
        scaling_factors = self.driver.get_axis_spec_by_alias('separation').scaling_factors
        position_tracking_error_threshold = abs(self.axis_position('separation') - grip_separation) * 2 * scaling_factors.posToDevice

        # For some reason velocity needs to be divided by DIV here to get correct values, even though it works elsewhere
        # 6000 mm/s is way beyond the axis capabilities, so it is practically infinite
        div = self.driver._comm.get_axis_parameter('separation', SMRegs.SMP_INPUT_DIVIDER)
        velocity_tracking_error_threshold = 6000.0 * (scaling_factors.velocity / div)

        control_mode = SMRegs.CM_TORQUE if self._separation_gripping_mode == "torque" else SMRegs.CM_POSITION

        self._gripping_separation_parameters = AxisParameterContext(self.driver, "separation", parameters={
            SMRegs.SMP_POSITION_TRACKING_ERROR_THRESHOLD: int(position_tracking_error_threshold),
            SMRegs.SMP_VELOCITY_TRACKING_ERROR_THRESHOLD: int(velocity_tracking_error_threshold),
            SMRegs.SMP_TORQUELIMIT_CONT: int(continuous_current_limit),
            SMRegs.SMP_TORQUELIMIT_PEAK: int(peak_current_limit),
            SMRegs.SMP_CONTROL_MODE: int(control_mode)
        })

        self._gripping_separation_parameters.read_current_parameters()
        self._gripping_separation_parameters.apply_new_parameters()

        if self._separation_gripping_mode == "position":
            self.set_axis_position('separation', grip_separation)
        elif self._separation_gripping_mode == "torque":
            self.driver.set_axis_parameter('separation', SMRegs.SMP_ABSOLUTE_SETPOINT, int(self._separation_gripping_torque_setpoint))
        else:
            assert False

    def release_separation_axis_grip(self, release_separation):
        """
        Release the grip on the separation axis by returning to a separation value where the object is released.
        Sets the separation axis parameters to the original values.
        :param release_separation: Target separation when object is released.
        """
        log.debug("Releasing separation axis grip.")

        if self._gripping_separation_parameters is None:
            raise Exception("Gripping parameters have not been set when attempting to release grip.")

        # If mode is "torque", set position mode before moving to release separation.
        if self._separation_gripping_mode == "torque":
            self.driver.set_axis_parameter('separation', SMRegs.SMP_CONTROL_MODE, SMRegs.CM_POSITION)

        self.set_axis_position('separation', release_separation)

        self._gripping_separation_parameters.apply_original_parameters()
        self._gripping_separation_parameters = None

    @json_out
    def put_press_physical_button(self, button_name, duration: float = 0):
        """
        Performs a press gesture on the given button.

        :param button_name: The button to press.
        :param duration: How long to keep button pressed in seconds (default: 0s).
        :return: "ok" / error
        """
        return self.press_physical_button(button_name, duration)

    def press_physical_button(self, button_name, duration: float = 0):
        """
        Implementation for press gesture on a given button.

        :param button_name: The button to press.
        :param duration: How long to keep button pressed in seconds (default: 0s).
        :return: "ok" / error
        """
        ws = get_node_workspace(self)

        button = Node.find_from(ws, button_name)

        if button is None or type(button) != PhysicalButton:
            raise NodeException('No physical button found with name {}'.format(button_name))

        log.info("put_press_physical_button button_name={}, duration={}".format(button_name, duration))

        if button.approach_position is None or button.pressed_position is None or button.jump_height is None:
            raise Exception("Button's properties approach_position, pressed_position and jump_height"
                            " must be defined before call this press method")

        if self.has_multifinger():
            raise Exception("Press button gesture can't be performed with multifinger")

        # voicecoil tap if normal finger attached
        prg = self.program

        approach_position_pose = np.matrix(button.approach_position)
        pressed_position_pose = np.matrix(button.pressed_position)

        prg.begin(ctx=button.object_parent, toolframe=self.tool_frame(self.default_kinematic_name),
                  kinematic_name=self.default_kinematic_name)
        prg.set_speed(self.robot_velocity, self.robot_acceleration)

        current_robot_pose = self.effective_pose()
        initial_frame = robotmath.translate(current_robot_pose, self.object_parent, button.object_parent)

        current_rotation = initial_frame[0:3, 0:3]

        init_x, init_y, init_z = robotmath.frame_to_xyz(initial_frame)
        z_jump = max(initial_frame[2, 3], (approach_position_pose[2, 3] + button.jump_height))

        target_x, target_y, target_z = robotmath.frame_to_xyz(approach_position_pose)

        init_jump_pose = robotmath.xyz_rot_to_frame(init_x, init_y, z_jump, current_rotation)
        target_jump_pose = robotmath.xyz_rot_to_frame(target_x, target_y, z_jump, current_rotation)

        p1 = prg.line(init_jump_pose, target_jump_pose)
        p2 = prg.line(target_jump_pose, approach_position_pose)
        jump_primitives = [p1, p2]

        prg.move(jump_primitives)
        prg.run()

        with VoicecoilMaxContCurrent(self, self.max_voicecoil_current, ["voicecoil1", "voicecoil2"]):
            prg.clear()
            press_primitives = [prg.line(approach_position_pose, pressed_position_pose),
                                prg.pause(duration),
                                prg.line(pressed_position_pose, approach_position_pose)]
            prg.move(press_primitives)
            prg.run()

        return "ok"

    @property
    @private
    def surface_probe(self):
        return self._surface_probe

    def camera_capture_preparations(self, camera_name):
        """
        Perform preparation actions on the robot required for capturing camera images on an object.
        E.g., moving any robot parts away from the camera image.
        Rotates synchro tool so that it's not seen in the camera image. Azimuth is set to 0.
        :return:
        """
        position = self._position_info(self.object_parent)
        position = position["position"]

        # Set azimuth to zero, use slow speed to avoid overspeed / overcurrent issues
        self._move(x=position["x"], y=position["y"], z=position["z"], azimuth=0)

    def tool_frame(self, kinematic_name=None):
        """
        Calculate tool frame for given kinematic name.
        This is synchro robot specific implementation. See general description in super class.
        :param kinematic_name: Name of kinematic under which the tool frame is calculated. If None, then active kinematic is used.
        :return: Total tool frame.
        """
        if kinematic_name in ["mid", "synchro"]:
            # Make sure that the length of tool1 and tool2 are sufficiently close to prevent collision.
            tool_frame1 = super().tool_frame("tool1")
            tool_frame2 = super().tool_frame("tool2")

            _, _, z1 = robotmath.frame_to_xyz(tool_frame1)
            _, _, z2 = robotmath.frame_to_xyz(tool_frame2)

            # This threshold was chosen to be somewhat higher than typical variance in tip lengths.
            # This most importantly verifies that both tools have a tip attached,
            tool_z_threshold = 0.5

            if abs(z1 - z2) > tool_z_threshold:
                raise Exception("Lengths of tool1 and tool2 must be within {} mm.".format(tool_z_threshold))

            return tool_frame1
        else:
            # TODO: Should probably make sure that length of tool is bigger than other tools.
            return super().tool_frame(kinematic_name)

    def get_finger_press_depth(self, axis_name):
        """
        Calculates the finger press depth for voicecoil axis based on configured margin and max position given to the
        axis.
        :param axis_name: Name of the axis which value we want to know.
        :returns: Finger press depth in mm.
        """
        specs = self.driver._kinematics.specs()

        for axis in specs:
            if specs[axis]['alias'] == axis_name:
                finger_press_depth = specs[axis]['max_position'] - specs[axis]['press_margin']
                if finger_press_depth > 0:
                    return finger_press_depth
                else:
                    raise Exception("Finger press depth was too small. Check maximum position and press margin for {}"
                                    .format(axis_name))

        raise Exception("Axis with the name {}} not found. Check configurations.".format(axis_name))

    def get_voicecoil_name_from_kinematic_name(self, kinematic_name):
        """
        Gets the axis alias associated with given kinematic name.
        """
        if kinematic_name == 'tool1':
            return 'voicecoil1'
        elif kinematic_name == 'tool2':
            return 'voicecoil2'
        else:
            # For mid and synchro return the voicecoil with smaller press depth
            if self.get_finger_press_depth('voicecoil1') <= self.get_finger_press_depth('voicecoil2'):
                return 'voicecoil1'
            return 'voicecoil2'


class SynchroSurfaceProbe(RobotSurfaceProbe):
    """
    Synchro robot specific implementation of RobotSurfaceProbe class.
    If multifinger tip is attached to robot, uses both voicecoils simultaneously to probe surface.
    """
    def __init__(self, robot):
        """
        Initializes robot specific implementation of RobotSurfaceProbe.
        :param robot: Robot node.
        """
        super().__init__(robot=robot)

        self._voicecoil_probing_position = None
        self._offset_frame = None
        self._initial_vc_position = None
        self._start_probe_axis_position = None
        self._detection_threshold = None
        self._incremental_step = None
        self._voicecoil_name = "voicecoil1"

    def set_tool(self, tool_name: str):
        if tool_name == "tool1":
            self._voicecoil_name = "voicecoil1"
        elif tool_name == "tool2":
            self._voicecoil_name = "voicecoil2"
        else:
            raise ValueError(f"Unrecognized tool {tool_name}.")

    def set_probing_parameters(self, probing_settings: dict):
        """
        Set probing parameters from settings dictionary.
        :param probing_settings: Dictionary containing settings for surface probing.
        :return: None
        """
        self._voicecoil_probing_position = probing_settings.get('voicecoil_probe_position', 10)
        self._incremental_step = probing_settings.get('robot_probing_step', 5)
        self._detection_threshold = probing_settings.get('surface_detection_threshold', 1)

        assert self._voicecoil_probing_position > self._detection_threshold, \
            "Voicecoil surface probing position must be larger than detection threshold of {} mm.".format(self._detection_threshold)

        assert self._voicecoil_probing_position * 0.9 > self._incremental_step, "Surface probing step is too large"

        # Movement during probing is towards the current robot tool Z-axis direction.
        self._offset_frame = robotmath.xyz_euler_to_frame(x=0, y=0, z=-self._incremental_step, a=0, b=0, c=0)

    def surface_pose(self):
        """
        Return the found surface as a robot pose.
        :return: Robot pose of DUT surface.
        """
        if not self.surface_probe_triggered:
            log.warning("Surface probe touch has not been triggered while reading surface pose.")

        # Calculate touch pose based on the offset of the voicecoil.
        current_pose = self._robot.effective_pose()

        if self._robot.has_multifinger():
            # If multifinger is attached, use the VC position that is smaller (compressed more).
            vc1_position = self._robot.joint_position(joint='voicecoil1')
            vc2_position = self._robot.joint_position(joint='voicecoil2')
            vc_position = min(vc1_position, vc2_position)

            log.debug("Voicecoil positions during multifinger probing: {}, {}".format(vc1_position, vc2_position))
        else:
            vc_position = self._robot.joint_position(joint=self._voicecoil_name)

        touch_offset_frame = robotmath.xyz_to_frame(x=0, y=0, z=-vc_position)
        surface_pose = current_pose * touch_offset_frame

        return surface_pose

    def __enter__(self):
        """
        Setup the robot configuration for surface probing by extending the voice coil to its probing position.
        :return: None
        """
        # Save voice coil starting position
        self._starting_robot_position = self._robot.effective_pose()
        self._initial_vc_position = self._robot.axis_position(axis=self._voicecoil_name)

        # Extend voice coil axis to probing position.
        if self._robot.has_multifinger():
            # If multifinger is attached, move both VCs simultaneously.
            self._robot.move_voicecoils(self._voicecoil_probing_position)
        else:
            self._robot.set_axis_position(axis=self._voicecoil_name, value=self._voicecoil_probing_position)

        self._start_probe_axis_position = self._robot.joint_position(joint=self._voicecoil_name)

        # Raise exception if voice coil cannot be extended to probing position.
        if not np.isclose(self._voicecoil_probing_position, self._start_probe_axis_position, atol=0.3):
            if self._robot.has_multifinger():
                # Move both VCs simultaneously to initial position.
                self._robot.move_voicecoils(self._initial_vc_position)
            else:
                self._robot.set_axis_position(axis=self._voicecoil_name, value=self._initial_vc_position)

            raise Exception("Failed to extend voicecoil to probing position. Check starting position of robot.")

    def __exit__(self, *args, **kwargs):
        """
        Reset robot configuration back to normal after surface probing. Voicecoil is retracted and robot is moved back
        to starting position or to detected surface position.
        """
        surface_pose = self.surface_pose()

        # Retract voicecoil back to its starting position.
        if self._robot.has_multifinger():
            self._robot.move_voicecoils(self._initial_vc_position)
        else:
            self._robot.set_axis_position(axis=self._voicecoil_name, value=self._initial_vc_position)

        # Move robot back to starting position or surface position.
        prg = self._robot.program
        prg.clear()
        prg.begin(ctx=self._robot.object_parent, toolframe=self._robot.tool_frame(),
                  kinematic_name=self._robot.kinematic_name)
        prg.set_speed(self._robot.robot_velocity, self._robot.robot_acceleration)

        if self.return_to_start:
            prg.move(prg.point(self._starting_robot_position))
        else:
            prg.move(prg.point(surface_pose))

        prg.run()

    def execute_probing_step(self):
        """
        Executes one incremental step in the surface probing sequence. Robot is moved one step in the direction defined
        by self._offset_frame.
        :return: None
        """
        # Advance robot one incremental step.
        prg = self._robot.program
        prg.clear()
        prg.begin(ctx=self._robot.object_parent, toolframe=self._robot.tool_frame(),
                  kinematic_name=self._robot.kinematic_name)
        prg.set_speed(self._robot.robot_velocity, self._robot.robot_acceleration)

        current_pose = self._robot.effective_pose()
        target_pose = current_pose * self._offset_frame
        prg.move(prg.line(current_pose, target_pose))
        prg.run()
        prg.clear()

    @property
    def surface_probe_triggered(self):
        """
        Return True if surface contact has been detected.
        :return: True if surface found, else False.
        """
        if self._robot.has_multifinger():
            diff1 = self._voicecoil_probing_position - self._robot.joint_position(joint='voicecoil1')
            diff2 = self._voicecoil_probing_position - self._robot.joint_position(joint='voicecoil2')

            # If either VC exceeds threshold, stop probing.
            return diff1 > self._detection_threshold or diff2 > self._detection_threshold
        else:
            return self._voicecoil_probing_position - self._robot.joint_position(joint=self._voicecoil_name) > self._detection_threshold
