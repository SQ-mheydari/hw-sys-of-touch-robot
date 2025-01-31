import numpy as np
import logging
import time
from tntserver.Nodes.Node import json_out, skip_nones, Node, NodeException, private
from tntserver.Nodes.TnT.PhysicalButton import PhysicalButton
from tntserver.Nodes.TnT.Workspace import get_node_workspace
from tntserver import robotmath

from .Gestures import VoicecoilMaxContPeakCurrent
import tntserver.Nodes.TnT.Robot
from tntserver.Nodes.Synchro.Robot import SynchroSurfaceProbe
import tntserver.drivers.robots.sm_regs as SMRegs


# Hardcode logger name to get logging under same name as normal TnT.Robot node logs
log = logging.getLogger('tntserver.Nodes.TnT.Robot')


class Robot(tntserver.Nodes.TnT.Robot.Robot):
    """
    Robot node for one-finger voicecoil robot. Voicecoil can be operated in two different modes:
    - Closed loop force control if load cell is installed (Opto Standard Force).
    - Open loop force control if there is no load cell.
    """
    def __init__(self, name):
        super().__init__(name)

        # voicecoil kinematics to use voicecoil for movements in z-axis direction
        self.voicecoil_kinematic_name = "voicecoil1"

    def _init(self, **kwargs):
        # call the original _init from TnT.Robot
        super()._init(**kwargs)

        # Comfortable general settings, where the voice coil feels like a spring that compresses some
        self.voicecoil_nominal_cont_current = kwargs.get('voicecoil_nominal_cont_current', 250)    # [mA]
        self.voicecoil_nominal_peak_current = kwargs.get('voicecoil_nominal_peak_current', 300)    # [mA]
        # Take into account that drive card can have modified shunt resistor so values will be 10x higher
        self.voicecoil_cont_current = kwargs.get('voicecoil_cont_current', 800)    # [mA]
        self.voicecoil_peak_current = kwargs.get('voicecoil_peak_current', 900)    # [mA]

        self._voicecoil_name = kwargs.get('voicecoil_name', 'voicecoil1')

        # set current limits to nominal configured or default values
        self.set_current_limits(
            continuous_current=self.voicecoil_nominal_cont_current,
            peak_current=self.voicecoil_nominal_peak_current
        )

        log.info("Setting voice coil current limits to: {}mA continuous and {}mA peak.".format(
            self.voicecoil_nominal_cont_current,
            self.voicecoil_nominal_peak_current
        ))

        # Add automatic surface z-height probe.
        self._surface_probe = VoicecoilSurfaceProbe(robot=self)

    def samples(self):
        """
        Added to make simulator work
        :return: {"forces": []}
        """
        return {
            "forces": []
        }

    @property
    @private
    def surface_probe(self):
        return self._surface_probe

    @json_out
    def put_home(self):
        """
        Commands the robot to go into home position.
        """
        self.home()

    def home(self):
        """
        Execute homing sequence of voicecoil.
        :return: None
        """
        self.driver.home()
        self.program.reset()

    def set_current_limits(self, continuous_current, peak_current):
        """
        Set new values for max. continuous and peak current limits.
        :param continuous_current: Max. continuous current in mA.
        :param peak_current: Peak current limit in mA.
        :return:
        """
        if continuous_current is not None:
            self.driver.set_axis_parameter("voicecoil1", SMRegs.SMP_TORQUELIMIT_CONT, continuous_current)

        if peak_current is not None:
            self.driver.set_axis_parameter("voicecoil1", SMRegs.SMP_TORQUELIMIT_PEAK, peak_current)

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
        initial_jump_frame = robotmath.translate(current_robot_pose, self.object_parent, button.object_parent)

        init_x, init_y, init_z = robotmath.frame_to_xyz(initial_jump_frame)
        z_jump = max(initial_jump_frame[2, 3], (approach_position_pose[2, 3] + button.jump_height))

        target_x, target_y, target_z = robotmath.frame_to_xyz(approach_position_pose)

        init_jump_pose = robotmath.xyz_to_frame(init_x, init_y, z_jump)
        target_jump_pose = robotmath.xyz_to_frame(target_x, target_y, z_jump)

        p1 = prg.line(init_jump_pose, target_jump_pose)
        p2 = prg.line(target_jump_pose, approach_position_pose)
        jump_primitives = [p1, p2]

        prg.move(jump_primitives)
        prg.run()

        with VoicecoilMaxContPeakCurrent(robot=self, max_cont_current=self.voicecoil_cont_current,
                                         peak_current=self.voicecoil_peak_current):
            prg.clear()
            press_primitives = [prg.line(approach_position_pose, pressed_position_pose),
                                prg.pause(duration),
                                prg.line(pressed_position_pose, approach_position_pose)]
            prg.move(press_primitives)
            prg.run()

        return "ok"

    @json_out
    def put_press_physical_button(self, button_name, duration: float = 0):
        """
        Performs a press gesture on the given button.

        :param button_name: The button to press.
        :param duration: How long to keep button pressed in seconds (default: 0s).
        :return: "ok" / error
        """
        self.press_physical_button(button_name, duration)

    def get_finger_press_depth(self):
        """
        Calculates the finger press depth for voicecoil axis based on configured margin and max position given to the
        axis.
        :returns: Finger press depth in mm.
        """
        specs = self.driver._kinematics.specs()

        for axis in specs:
            if specs[axis]['alias'] == 'voicecoil1':
                finger_press_depth = specs[axis]['max_position'] - specs[axis]['press_margin']
                if finger_press_depth > 0:
                    return finger_press_depth
                else:
                    raise Exception("Finger press depth was too small. Check maximum position and press margin for {}"
                                    .format('voicecoil1'))

        raise Exception("Axis with the name voicecoil1 not found. Check configurations.")

    def enable_voicecoil(self):
        """
        Enable voicecoil and move to zero position.
        This can be used to make the end-effector loose and perform gestures in a more gentle way.
        """
        self.driver.enable_axes([self._voicecoil_name])

        self.move_joint_position({self._voicecoil_name: 0.0}, self.robot_velocity, self.robot_acceleration)

        self.driver.kinematics.voicecoil_position = None

    @json_out
    def put_enable_voicecoil(self):
        """
        Enable voicecoil and move to zero position.
        This can be used to make the end-effector loose and perform gestures in a more gentle way.
        """
        self.enable_voicecoil()

    def disable_voicecoil(self):
        """
        Disable voicecoil. The voicecoil position after stabilization time is stored and used
        by robot kinematics so that end-effector movements are still accurate.
        """
        specs = self.driver.kinematics.get_axis_spec_by_alias(self._voicecoil_name)

        rest_position = specs.get("rest_position", None)

        if rest_position is not None:
            log.debug("Moving {} to rest position {} mm.".format(self._voicecoil_name, rest_position))

            # Move to rest position before disabling the axis to prevent oscillation.
            self.move_joint_position({self._voicecoil_name: rest_position}, self.robot_velocity, self.robot_acceleration)

        self.driver.disable_axes([self._voicecoil_name])

        rest_time = specs.get("rest_time", 2.0)
        log.debug("Waiting for {} s for position to stabilize.".format(rest_time))
        time.sleep(rest_time)

        self.driver.kinematics.voicecoil_position = self.driver.get_joint_positions()[self._voicecoil_name]
        log.debug("VC position after disable is {} mm.".format(self.driver.kinematics.voicecoil_position))

    @json_out
    def put_disable_voicecoil(self):
        """
        Disable voicecoil. The voicecoil position after stabilization time is stored and used
        by robot kinematics so that end-effector movements are still accurate.
        """
        self.disable_voicecoil()


class VoicecoilSurfaceProbe(SynchroSurfaceProbe):
    """
    Voicecoil robot specific surface probing.
    The probing procedure is essentially the same as with synchro robot except that
    the calculation of surface pose during triggering is different. The difference comes
    from the way those two kinematics handle voicecoil in FW kinematics.
    """
    def __init__(self, robot):
        super().__init__(robot=robot)
        self._voicecoil_probing_current = None

    def set_probing_parameters(self, probing_settings: dict):
        super().set_probing_parameters(probing_settings)
        self._voicecoil_probing_current = probing_settings.get('voicecoil_probing_current', None)

    def __enter__(self):
        """
        Setup the robot configuration for surface probing by extending the voice coil to its probing position.
        :return: None
        """
        # Initialize probing position
        super().__enter__()

        # Set current during probing, if given
        if self._voicecoil_probing_current is not None:
            self._robot.set_current_limits(continuous_current=self._voicecoil_probing_current,
                                           peak_current=self._voicecoil_probing_current)

    def __exit__(self, *args, **kwargs):
        """
        Reset robot configuration back to normal after surface probing. Voicecoil is retracted and robot is moved back
        to starting position or to detected surface position.
        """
        # Restore current limits to default values
        self._robot.set_current_limits(
            continuous_current=self._robot.voicecoil_nominal_cont_current,
            peak_current=self._robot.voicecoil_nominal_peak_current
        )

        # Do the rest of setup steps for surface probing
        super().__exit__(*args, **kwargs)

    def surface_pose(self):
        """
        Return the found surface as a robot pose.
        :return: Robot pose of DUT surface.
        """
        if not self.surface_probe_triggered:
            log.warning("Surface probe touch has not been triggered while reading surface pose.")

        # Calculate touch pose based on the offset of the voicecoil.
        current_pose = self._robot.effective_pose()
        vc_position = self._robot.joint_position(joint='voicecoil1')

        # Difference in VC setpoint and achieved position.
        vc_diff = self._voicecoil_probing_position - vc_position

        if vc_diff < 0:
            raise Exception("Voicecoil setpoint must be greater than achieved position in probe trigger position.")

        # VC robot tool1 kinematics (default) uses VC setpoint in FW kinematics.
        # Hence the achieved effector position during probe trigger is at offset vc_diff (>0) along pose z-direction.
        touch_offset_frame = robotmath.xyz_to_frame(x=0, y=0, z=vc_diff)

        surface_pose = current_pose * touch_offset_frame

        return surface_pose