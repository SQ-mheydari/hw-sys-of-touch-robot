import logging
import numpy as np
import time

from toolbox import robotmath
from tntserver.drivers.robots.goldenmov import RobotKinematics
import tntserver.drivers.robots.sm_regs as sm_regs
from tntserver.drivers.robots.goldenmov.kinematics import append_post_homing_move
from .kinematic_3axis import filter_frame_3axis

log = logging.getLogger(__name__)


# Set this to True to test Hbot kinematics (homing) with standard 3-axis robot.
TEST_AS_STANDARD_3AXIS = False


class OverrideAxisSettings:
    """
    Temporarily override axis settings.
    """
    def __init__(self, comm, axis_settings):
        self.comm = comm

        # Settings to be used to override original settings on enter.
        self.new_axis_settings = axis_settings

        # Store original settings that are reverted on exit.
        self.orig_axis_settings = {axis: {} for axis in axis_settings}

        for axis, settings in axis_settings.items():
            self.orig_axis_settings[axis] = {key: {} for key in settings}

    def __enter__(self):
        for axis, settings in self.orig_axis_settings.items():
            for reg in settings:
                settings[reg] = self.comm.get_axis_parameter(axis, reg)

        for axis, settings in self.new_axis_settings.items():
            for reg in settings:
                log.debug("Setting axis {} parameter {} to {}".format(axis, reg, settings[reg]))
                self.comm.set_axis_parameter(axis, reg, settings[reg])

                # Make sure the parameter was set. This is critical.
                if self.comm.get_axis_parameter(axis, reg) != settings[reg]:
                    raise Exception("Could not set parameter!")

    def __exit__(self, *args, **kwargs):
        for axis, settings in self.orig_axis_settings.items():
            for reg in settings:
                self.comm.set_axis_parameter(axis, reg, settings[reg])


def software_hardstop(sm, axis_increments, axis_tracking_error_limits):
    """
    Move axes in given directions until sufficient tracking error is determined.
    Note: This procedure is very sensitive to the various axis parameters and odds are it does not work reliably.
    :param sm: Communication object for setting Simplemotion parameters.
    :param axis_increments: Dict of axis motion values that determine stepping direction and length (e.g. {"x": -1}).
    :param axis_tracking_error_limits: Axis tracking error limits to determine hard stop (e.g. {"x": 100}).
    """

    axis_position = {}
    axis_setpoint = {}

    # Set axis setpoint book-keeping match the current axis positions.
    for axis in axis_increments.keys():
        axis_setpoint[axis] = sm.get_axis_parameter(axis, param=sm_regs.SMP_ACTUAL_POSITION_FB)

    WAIT_FOR_MOVEMENT = 4.0
    log.debug("Waiting for movement {} seconds".format(WAIT_FOR_MOVEMENT))
    tracking_error = {}

    while True:
        # Compute tracking errors.
        for axis in axis_increments.keys():
            axis_position[axis] = sm.get_axis_parameter(axis, param=sm_regs.SMP_ACTUAL_POSITION_FB)
            tracking_error[axis] = abs(axis_position[axis] - axis_setpoint[axis])
            log.debug("{} - tracking error: {}".format(
                axis, tracking_error[axis]))

        # If tracking error exceeds threshold then we have reached hard stop.
        if any(te > axis_tracking_error_limits[axis] for axis, te in tracking_error.items()):
            for axis in axis_increments.keys():
                log.debug("{} - Seems that we have hardstop. Setpoint = {}, current position = {}".format(
                    axis, axis_setpoint[axis], axis_position[axis]))
            break

        # Move axes by homing increment.
        for axis, increment, in axis_increments.items():
            axis_setpoint[axis] += increment
            log.debug("{} - Setting new setpoint to: {}".format(axis, axis_setpoint[axis]))
            sm.set_axis_parameter(axis, sm_regs.SMP_ABSOLUTE_SETPOINT, axis_setpoint[axis])

        # Wait for movement to complete.
        # TODO: Read some axis state rather than sleep.
        log.debug("Waiting for movement {} seconds".format(WAIT_FOR_MOVEMENT))
        time.sleep(WAIT_FOR_MOVEMENT)

    # ----------- set current position as the setpoint
    # p_y = sm.get_axis_parameter(axis, param=SMP_ACTUAL_POSITION_FB)
    for axis in axis_increments.keys():
        axis_position[axis] = sm.get_axis_parameter(axis, param=sm_regs.SMP_ACTUAL_POSITION_FB)

    # Move back from hard stop to relax controller.
    log.debug("Home position is: {}".format(axis_position))
    for axis, increment, in axis_increments.items():
        log.debug("Moving axis {} back {} units to relax from hard-stop".format(axis, 2 * increment))
        
        sm.set_axis_parameter(axis, sm_regs.SMP_ABSOLUTE_SETPOINT, axis_position[axis] - 2 * increment)

        # TODO: Read some axis state rather than sleep.
        time.sleep(4)
        # reset feedback and setpoint
        sm.set_axis_parameter(axis, sm_regs.SMP_SYSTEM_CONTROL, sm_regs.SMP_SYSTEM_CONTROL_RESET_FB_AND_SETPOINT)


def get_homing_parameters_from_spec(axis_specs, parameter_name):
    """
    Get specific homing parameter for each axis in spec that has homing parameters.
    :param axis_specs: Axis specifications dict.
    :param parameter_name: Name of homing parameter to get for each axis
    """
    return {spec["alias"]: spec["homing_parameters"][parameter_name] for spec in
                                  axis_specs.values() if "homing_parameters" in spec}


class RobotPosition(RobotKinematics.RobotPositionBase):
    __slots__ = ["frame", "d", "t"]
    pass


class Kinematic_hbot(RobotKinematics):
    """
    Kinematics implementation of H-bot 3-axis robot.
    Festo gantry stages for XY and voice coil for Z-axis.

    This kinematics requires special homing because x and y joints can't be homed independently due to
    the kinematics of the H-bot. The homing sequence is detailed in homing_sequence().

    How to configure x and y axes:
    - Stepper mode under open loop control.
    - x-axis homing should be against homing switch (e.g. light switch).
    - y-axis homing should be configured so that it does not move but only zeros the position.
      Basically this is normal hard-stop homing with very low hard-stop limit.
    """
    name = "hbot"

    def __init__(self, robot, axis_specs=None):
        self.axis_specs = axis_specs

        self.parameters = {
            # Possible values: "switch_torque", "switch_disable".
            "homing_method": "switch_torque"
        }



        super().__init__(robot, RobotPosition)

        # default tool orientation in relation to robot base
        self._tool_orientation = robotmath.xyz_euler_to_frame(0, 0, 0, 180, 0, 180)
        self._tool_orientation_i = self._tool_orientation.I

        # transformation matrix for kinematics
        # explanation: https://www.iwf.mavt.ethz.ch/ConfiguratorJM/publications/MODELING_A_132687166151936/3314_mod.pdf
        # MODELING AND MEASUREMENT OF H-BOT KINEMATIC SYSTEMS
        # Sascha Weikert, Roman Ratnaweera, Oliver Zirn and Konrad Wegener

        if TEST_AS_STANDARD_3AXIS:
            self.fk_trans = robotmath.identity_frame()
        else:
            self.fk_trans = np.matrix(
                [[-1.0,  1.0],
                 [-1.0, -1.0]])

        # IK transform is:
        # [-1/2, -1/2]
        # [ 1/2, -1/2]
        self.ik_trans = np.linalg.inv(self.fk_trans)

        """
        self.driver is an GoldenMov instance, that gets added in GoldenMov's __init__
        after kinematics creation. _comm from GoldenMov is: optomotion.OptoMotionComm,
        or RobotSimulator.connection.
        So, to use SimpleMotion with robot self.driver._comm is needed.
        """

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
        z = 0

        if self._has_z_axis():
            z = joints['z']

        xy_vector = self.fk_trans * np.matrix([x, y]).T
        x, y = xy_vector.item(0), xy_vector.item(1)

        frame = robotmath.xyz_euler_to_frame(x, y, -z, 0, 0, 0) * self._tool_orientation

        return self.create_robot_position(frame=frame)

    def _robot_ik(self, pos: RobotPosition):
        x, y, z, = robotmath.frame_to_xyz(pos.frame * self._tool_orientation_i)

        xy_vector = self.ik_trans * np.matrix([x, y]).T
        x, y = xy_vector.item(0), xy_vector.item(1)

        joints = {'y': y, 'x': x}

        if self._has_z_axis():
            joints['z'] = -z

        return joints

    def _has_z_axis(self):
        for spec in self.specs().values():
            if spec["alias"] == "z":
                return True

        return False

    def homing_sequence(self):
        """
        Homing sequence for H-bot. Multiple methods are defined.

        Alternative (worse ray):
        Use SW hard-stop homing (see function self.home()).
        """

        method = self.parameters["homing_method"]

        log.debug("Using homing method '{}'.".format(method))

        if TEST_AS_STANDARD_3AXIS:
            sequence = [
                ("home", ['x', 'y']), # Home to enable axes. Homing should not actually move the axes.
                ("execute", lambda: self.home_sw_hardstop({'x': -1})),  # Home workspace x
                ("execute", lambda: self.home_sw_hardstop({'y': -1})),  # Home workspace y
                ("home", ['x', 'y']), # Home axes again to reset encoder counter to zero.
                ("move", {'z': 10}),
                ("home", ['z'])
            ]
        elif method == "switch_disable":
            """
            Requirements:
            - x and y axes should be step motors under open loop control.
            - x-axis must define homing to a homing switch located at corner.
            - x-axis homing switch can be changed after first homing and offset move before second homing.
            - Axes can be freed by disabling them
            1) Home z-axis normally to hard stop or homing switch.
            2) Disable y-axis to allow homing stage to corner by homing x-axis.
            3) Set x-axis home switch to configured value switch_1.
            4) Home x-axis.
            5) Enable y-axis.
            6) Reset y-axis setpoint to 0. This allows moving y-axis to specific offset.
            7) Disable x-axis so that stage can be moved away from corner by moving y-axis.
            8) Move y-axis by configured distance offset using configured speed and acceleration.
            9) Disable y-axis to allow homing x-axis again.
            10) Set x-axis home switch to configured value switch_2.
            11) Home x-axis.
            12) Enable y-axis.
            13) Reset y-axis setpoint to 0.
            """
            spec_x = self.get_axis_spec_by_alias("x")
            spec_y = self.get_axis_spec_by_alias("y")
            homing_parameters_x = spec_x.get("homing_parameters", {})
            homing_parameters_y = spec_y.get("homing_parameters", {})

            offset_y = homing_parameters_y.get("offset", -20)
            speed_y = homing_parameters_y.get("speed", 10)
            acceleration_y = homing_parameters_y.get("acceleration", 20)

            # Use the same switch by default.
            # NOTE: The values should be sm_regs.SMP_DIG_IN1_GPI1 etc. but it seems that the values don't work
            # correctly. Instead they are off by one so that e.g. sm_regs.SMP_DIG_IN1_GPI1 should be zero.
            switch_x_1 = homing_parameters_x.get("switch_1", 0)
            switch_x_2 = homing_parameters_x.get("switch_2", 0)

            sequence = [
                ("disable", ["y"]),
                ("set_axis_parameter", {"axis": "x", "param": sm_regs.SMP_HOME_SWITCH_SOURCE_SELECT, "value": switch_x_1}),
                ("home", ['x']),
                ("enable", ['y']),
                ("set_axis_parameter", {"axis": "y", "param": sm_regs.SMP_SYSTEM_CONTROL,
                                        "value": sm_regs.SMP_SYSTEM_CONTROL_RESET_FB_AND_SETPOINT}),
                ("disable", ["x"]),
                ("move_axis", {'alias': 'y', 'position': offset_y, 'speed': speed_y, 'acceleration': acceleration_y}),
                ("disable", ["y"]),
                ("set_axis_parameter", {"axis": "x", "param": sm_regs.SMP_HOME_SWITCH_SOURCE_SELECT, "value": switch_x_2}),
                ("home", ['x']),
                ("enable", ['y']),
                # Reset y-axis feedback and setpoint to "home" it. Axis must have been enabled beforehand.
                ("set_axis_parameter", {"axis": "y", "param": sm_regs.SMP_SYSTEM_CONTROL,
                                        "value": sm_regs.SMP_SYSTEM_CONTROL_RESET_FB_AND_SETPOINT})
            ]
        elif method == "dual":
            """
            Requirements:
            - Homing switch 1 and 2 are both connected to x and y axes to GPI1 and GPI2 pins.
            - x and y axes must define homing to a homing switch (switch is changed during homing sequence).
            - Axis limits of x and y must be from large negative to large positive. Do not use zeros.
            - Movement limits must be set for TnT so that if homed, robot is able to perform the initial offset move.
            1) Home z-axis normally to hard stop or homing switch.
            2) Enable x and y axes to ensure that Optomotion homes both nearly simultaneously when commanded.
            3) Reset x and y setpoints and move them so that they are out of home switches in case homing starts from home.
            4) Set homing switches of x and y axes to switch_x_1 and switch_y_1.
            5) Set x and y axis home switch polarities so that stage moves to switch 1.
            6) Home x and y axes simultaneously to switch 1.
            7) Set homing switches of x and y axes to switch_x_2 and switch_y_2.
            8) Set x and y axis home switch polarities so that stage moves to switch 2.
            9) Home x and y axes simultaneously to switch 2.
            """
            spec_x = self.get_axis_spec_by_alias("x")
            spec_y = self.get_axis_spec_by_alias("y")

            if spec_x["homing_priority"] != spec_y["homing_priority"]:
                raise Exception("x and y axis homing priorities must match in dual homing.")

            homing_parameters_x = spec_x.get("homing_parameters", {})
            homing_parameters_y = spec_y.get("homing_parameters", {})

            # NOTE: The values should be sm_regs.SMP_DIG_IN1_GPI1 etc. but it seems that the values don't work
            # correctly. Instead they are off by one so that e.g. sm_regs.SMP_DIG_IN1_GPI1 should be zero.
            switch_x_1 = homing_parameters_x.get("switch_1", 0)
            switch_x_2 = homing_parameters_x.get("switch_2", 1)
            switch_y_1 = homing_parameters_y.get("switch_1", 0)
            switch_y_2 = homing_parameters_y.get("switch_2", 1)

            home_switch_polarity_x_1 = homing_parameters_x.get("home_switch_polarity_1", "keep")
            home_switch_polarity_x_2 = homing_parameters_x.get("home_switch_polarity_2", "keep")
            home_switch_polarity_y_1 = homing_parameters_y.get("home_switch_polarity_1", "keep")
            home_switch_polarity_y_2 = homing_parameters_y.get("home_switch_polarity_2", "keep")

            offset_x = homing_parameters_x.get("offset", 0)
            speed_x = homing_parameters_x.get("speed", 10)
            acceleration_x = homing_parameters_x.get("acceleration", 10)
            offset_y = homing_parameters_y.get("offset", 0)
            speed_y = homing_parameters_y.get("speed", 10)
            acceleration_y = homing_parameters_y.get("acceleration", 10)

            sequence = [
                ("enable", ['x', 'y']),
                ("set_axis_parameter", {"axis": "x", "param": sm_regs.SMP_SYSTEM_CONTROL, "value": sm_regs.SMP_SYSTEM_CONTROL_RESET_FB_AND_SETPOINT}),
                ("set_axis_parameter", {"axis": "y", "param": sm_regs.SMP_SYSTEM_CONTROL, "value": sm_regs.SMP_SYSTEM_CONTROL_RESET_FB_AND_SETPOINT}),
                ("move_axis", {'alias': 'x', 'position': offset_x, 'speed': speed_x, 'acceleration': acceleration_x}),
                ("move_axis", {'alias': 'y', 'position': offset_y, 'speed': speed_y, 'acceleration': acceleration_y}),
                ("set_axis_parameter", {"axis": "x", "param": sm_regs.SMP_HOME_SWITCH_SOURCE_SELECT, "value": switch_x_1}),
                ("set_axis_parameter", {"axis": "y", "param": sm_regs.SMP_HOME_SWITCH_SOURCE_SELECT, "value": switch_y_1}),
                ("home_switch_polarity", {"axis": "x", "value": home_switch_polarity_x_1}),
                ("home_switch_polarity", {"axis": "y", "value": home_switch_polarity_y_1}),
                ("home_simultaneously", ['x', 'y']),
                ("set_axis_parameter", {"axis": "x", "param": sm_regs.SMP_HOME_SWITCH_SOURCE_SELECT, "value": switch_x_2}),
                ("set_axis_parameter", {"axis": "y", "param": sm_regs.SMP_HOME_SWITCH_SOURCE_SELECT, "value": switch_y_2}),
                ("home_switch_polarity", {"axis": "x", "value": home_switch_polarity_x_2}),
                ("home_switch_polarity", {"axis": "y", "value": home_switch_polarity_y_2}),
                ("home_simultaneously", ['x', 'y'])
            ]
        elif method == "switch_torque":
            """
            Requirements:
            - x and y axes should be step motors under open loop control.
            - x-axis must define homing to a homing switch.
            - Axes can be freed by setting them to torque mode (axes may have breaks).
            1) Home z-axis normally to hard stop or homing switch.
            2) Set y-axis continuous current limit to near-zero value. It will then act as pulley.
            3) Home x-axis to a homing switch.
            4) Revert y-axis continuous current limit to normal operational value.
            5) Home y-axis to hard-stop assuming very low tracking error. Its position will then be zero but there is no motion.
            6) Move x and z axes slightly to avoid violating movement limits during first movement.
            """
            cont_current_limit = self.driver._comm.get_axis_parameter("y", sm_regs.SMP_TORQUELIMIT_CONT)

            sequence = [
                # Set y axis continuous current limit to near-zero value (zero not allowed). Axis then acts as pulley.
                ("set_axis_parameter", {"axis": "y", "param": sm_regs.SMP_TORQUELIMIT_CONT, "value": 1}),
                # Do hard-stop homing on x-axis. Because y-axis is free to roll, stage will home to corner.
                ("home", ['x']),
                # Revert continuous current limit.
                ("set_axis_parameter", {"axis": "y", "param": sm_regs.SMP_TORQUELIMIT_CONT, "value": cont_current_limit}),
                # Reset y-axis feedback and setpoint to "home" it. Axis must have been enabled beforehand.
                ("set_axis_parameter", {"axis": "y", "param": sm_regs.SMP_SYSTEM_CONTROL, "value": sm_regs.SMP_SYSTEM_CONTROL_RESET_FB_AND_SETPOINT})
            ]
        else:
            raise Exception("Unrecognized homing method '{}'.".format(method))

        # Home z-axis first if such axis is defined.
        if self._has_z_axis():
            z_cont_current = self.driver._comm.get_axis_parameter("z", sm_regs.SMP_TORQUELIMIT_CONT)
            z_peak_current = self.driver._comm.get_axis_parameter("z", sm_regs.SMP_TORQUELIMIT_PEAK)

            spec = self.get_axis_spec_by_alias("z")
            homing_parameters = spec.get("homing_parameters", {})
            z_cont_homing_current_limit = homing_parameters.get("cont_current_limit", z_cont_current)
            z_peak_homing_current_limit = homing_parameters.get("peak_current_limit", z_peak_current)

            # Home z-axis using specific current limits. Usually the limits are set so that axis applies only small
            # force or torque. In homing, larger current may be needed to detect hard-stop reliably.
            sequence = [
                           ("set_axis_parameter", {"axis": "z", "param": sm_regs.SMP_TORQUELIMIT_CONT,
                                                   "value": z_cont_homing_current_limit}),
                           ("set_axis_parameter", {"axis": "z", "param": sm_regs.SMP_TORQUELIMIT_PEAK,
                                                   "value": z_peak_homing_current_limit}),
                           ("home", ['z']),
                           ("set_axis_parameter", {"axis": "z", "param": sm_regs.SMP_TORQUELIMIT_CONT,
                                                   "value": z_cont_current}),
                           ("set_axis_parameter", {"axis": "z", "param": sm_regs.SMP_TORQUELIMIT_PEAK,
                                                   "value": z_peak_current}),
                       ] + sequence

        append_post_homing_move(sequence, self.axis_specs)

        return sequence

    def home_sw_hardstop(self, axis_factors):
        """
        Custom homing method for Festo H-bot stage (parallel kinematics)
        1. Move robot to home position
        2. Reset setpoint and feedback
        - rotate both motors to move gantry into X and then Y direction until it hits hard-stop, consider:
            - speed
            - acceleration
            - current limit
            - fault limits, especially tracking error
        Can be used in homing sequence as step ("execute", lambda: self.home({'y': -1, 'x': 1}))
        """
        sm = self.driver._comm  # sm like in SomethingMotion
        # xy1 - motor 1, xy2 - motor 2, that's how I imagine Festo stages configuration
        """
        1. set speed/acceleration
        2. change tracking error fault limit to ridiculously high
        3. move in one and then other direction
        4. revert speed/acceleration/fault limit changes
        5. reset position and feedback
        """

        # Get homing axis parameters from spec.
        # Notice that e.g. speed and acceleration values are in encoder counts.
        accelerations = get_homing_parameters_from_spec(self.axis_specs, "acceleration")
        velocities = get_homing_parameters_from_spec(self.axis_specs, "velocity")
        position_tracking_errors = get_homing_parameters_from_spec(self.axis_specs, "position_tracking_error")
        velocity_tracking_errors = get_homing_parameters_from_spec(self.axis_specs, "velocity_tracking_error")
        peak_current_limits = get_homing_parameters_from_spec(self.axis_specs, "peak_current_limit")
        continuous_current_limits = get_homing_parameters_from_spec(self.axis_specs, "continuous_current_limit")
        increments = get_homing_parameters_from_spec(self.axis_specs, "increment")

        # Map parameters to Simplemotion names.
        axis_settings = {}

        for axis in axis_factors.keys():
            settings = {
                sm_regs.SMP_TRAJ_PLANNER_ACCEL: accelerations[axis],
                sm_regs.SMP_TRAJ_PLANNER_VEL: velocities[axis],
                sm_regs.SMP_POSITION_TRACKING_ERROR_THRESHOLD: position_tracking_errors[axis],
                sm_regs.SMP_VELOCITY_TRACKING_ERROR_THRESHOLD: velocity_tracking_errors[axis],
                sm_regs.SMP_TORQUELIMIT_CONT: continuous_current_limits[axis],
                sm_regs.SMP_TORQUELIMIT_PEAK: peak_current_limits[axis],
                sm_regs.SMP_POSITION_SOFT_HIGH_LIMIT: 0,
                sm_regs.SMP_POSITION_SOFT_LOW_LIMIT: 0
            }

            axis_settings[axis] = settings

        axis_tracking_error_limits = get_homing_parameters_from_spec(self.axis_specs, "tracking_error_limit")

        for key in axis_factors.keys():
            increments[key] *= axis_factors[key]

        # Perform hardstop homing with specific axis settings.
        with OverrideAxisSettings(sm, axis_settings):
            software_hardstop(sm, increments, axis_tracking_error_limits)

        return None

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
                11: {'alias': 'z', 'homing_priority': 3, 'acceleration': 500, 'velocity': 500, 'move_tolerance': 0.001},
            }
            return p

    def arc_r(self, toolframe=None, kinematic_name=None):
        return 0.0
