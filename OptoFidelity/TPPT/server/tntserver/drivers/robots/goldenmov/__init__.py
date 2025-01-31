import logging
import time
import numpy as np
from tntserver import robotmath
from tntserver.Nodes.Node import NodeException
from .kinematics import RobotKinematics
from tntserver.drivers.robots.goldenmov.goldenmov_optomotion import GoldenMovOptomotion
import tntserver.drivers.robots.sm_regs as SMRegs
from .trajectory import *
import copy

log = logging.getLogger(__name__)

try:
    from .simulator import RobotSimulator as RobotSimulator
except Exception as e:
    log.info('Could not import simulator', e)

# run 250 samples per second bufferedmotion with optomotion
SAMPLES_PER_SECOND = 250
TIME_STEP = 1 / SAMPLES_PER_SECOND

# TODO: use sm_regs.py instead if possible
API_OPTOMOTION = "optomotion"
from .simplemotion_defs import simplemotion_defs


class GoldenMovException(NodeException):
    pass


class AxisLimitError(Exception):
    pass


class GoldenMovRecorder:
    """
    Context manager class for recording buffered motion axes positions with GoldenMov.
    Usage pattern:
    with GoldenMovRecorder(goldenmov):
        # Perform gestures
        executed_axes = goldenmov.executed_axes

    """
    def __init__(self, goldenmov):
        self.goldenmov = goldenmov

    def __enter__(self):
        self.goldenmov.start_recording_axes()

    def __exit__(self, *args):
        self.goldenmov.stop_recording_axes()


class GoldenMov:
    """
    GoldenMov based robot.
    """

    def __init__(self, robot, host: str, port: int, model: str,
                 use_simulator: bool, visualize,
                 log_level: int=2, axis_specs=None, api_name=API_OPTOMOTION,
                 position_limits=None, restore_axis_configs=True, home_axes=True,
                 kinematic_parameters=None):
        """
        Initialize GoldenMov robot control object.
        :param host: Host IP address string.
        :param port: Host port number.
        :param model: Model name that is used to select robot kinematics.
        :param use_simulator: Is simulator instead of optomotion controller?
        :param visualize: If simulator, are the results visualized in Web browser?
        :param log_level: Log level that affects loggig of Simplemotion commands.
        :param axis_specs: Axis spec dictionary (optional).
        :param api_name: Which robot control API to use.
        :param position_limits: Position limits (in workspace). Can be used on case the limits can't be deduced from axis limits.
        :param restore_axis_configs: Restore axis configs before homing.
        :param home_axes: Home axes on initialization.
        """

        self._comm = None
        self._supported_axis = []
        self._kinematics = None
        self._restore_axis_configs = restore_axis_configs

        self.position_limits = position_limits

        kinematic_model = RobotKinematics.get_model(model.lower())
        kinematic = kinematic_model(robot, axis_specs)
        kinematic.driver = self

        if kinematic_parameters is not None:
            kinematic.parameters.update(kinematic_parameters)

        self._kinematics = kinematic
        axis_specs = self._kinematics.specs()

        if use_simulator:
            simu = RobotSimulator(model, kinematic, host, port, visualize)
            self._comm = simu.connection
            self._waiter = self._comm.waiter()

            self.__is_simulator = True
        else:
            if api_name == API_OPTOMOTION:
                log.debug("Using Optomotion API")

                self._comm = GoldenMovOptomotion("{}:{}".format(host, port), axis_specs=axis_specs)

                for address, data in kinematic.specs().items():
                    self._comm.discover_axis(address, data['alias'])
            else:
                raise Exception("Unknown API name {}!".format(api_name))

            self._waiter = self._comm.waiter

            self.__is_simulator = False

        # Get maximum position for voicecoil(s) if relevant for the robot type.
        unknown = []

        self._frame = None

        specs = self._comm.get_axis_specs()

        log.debug(specs)
        for axis in specs:
            specs = axis_specs.get(axis.address, None)
            if specs:

                # Update limits to axis_spec
                axis_specs[axis.address].update({'max_position': axis.position_limits.max,
                                                 'min_position': axis.position_limits.min})

                axis.alias = specs['alias']
                axis.homing_priority = specs['homing_priority']
                axis.inverted = specs['inverted'] if 'inverted' in specs else False
                if 'drive_acceleration' in specs:
                    axis.max_acceleration = specs['drive_acceleration']
                else:
                    axis.max_acceleration = specs['acceleration']
                if 'drive_velocity' in specs:
                    axis.max_velocity = specs['drive_velocity']
                else:
                    axis.max_velocity = specs['velocity']
                self._supported_axis.append(axis.alias)
                log.info('Found axis %s at address %s', axis.alias, axis.address)
            else:
                log.warning('Unknown axis at address %s', axis.address)
                unknown.append(axis.alias)

        for unknown_axis in unknown:
            self._comm.remove_axis(unknown_axis)

        # Set update axis_specs for kinematic so it contains the axis limits.
        kinematic.set_specs(axis_specs)

        axis_specs_alias = [a["alias"] for a in axis_specs.values()]
        if set(self._supported_axis) != set(axis_specs_alias):
            log.error("Robot should have {} axis but found {}".format(len(axis_specs_alias), len(self._supported_axis)))
            exit(0)

        for error in self.error:
            log.warning("Robot has error: %s", error)

        if home_axes:
            self._do_homing()

        log.debug("Waiting for robot initialization")
        while self._comm.is_busy():
            time.sleep(0.1)

        # Store copy of executed axis position buffers for inspection.
        # This is a list of axis dicts. Each buffered motion is appended to the list if executed_axes is not None.
        self.executed_axes = None

        log.info("GoldenMov %s initialized", model)

    @property
    def kinematics(self):
        return self._kinematics

    def start_recording_axes(self):
        # Empty list starts new recording.
        self.executed_axes = []

    def stop_recording_axes(self):
        # None means that axes values are not recorded.
        self.executed_axes = None

    def restore_axis_configs(self):
        """
        Restores configurations of axes listed in kinematics specs from non-volatile drive memory.
        This should be called during initialization before homing to ensure that the drive settings are not
        modified from previous use of TnT Server or some other program.
        """
        log.info("Restoring axis configurations.")

        for _, specs in self._kinematics.specs().items():
            self._comm.restore_axis_configuration(specs["alias"])

    def _do_homing(self):
        """
        Executes all commands defined in a robot's homing sequence.
        :return: None
        """
        if self._restore_axis_configs:
            self.restore_axis_configs()

        self._comm.clear_errors()
        cmd_id = None

        log.debug("homing will follow as:")
        for command, params in self._kinematics.homing_sequence():
            log.debug("  {} : {}".format(command, params))

        for command, params in self._kinematics.homing_sequence():
            log.debug("homing: {} : {}".format(command, params))
            if command == "homeall":
                log.info("Home all axes")
                cmd_id = self._comm.home()
            elif command == "home":
                log.info("Home axes: %s", params)
                cmd_id = self._home_axes(params)
            elif command == "home_simultaneously":
                log.info("Home axes simultaneously: %s", params)
                cmd_id = self._home_axes_simultaneously(params)
            elif command == "move":
                log.info("Move axes: %s", params)
                cmd_id = self._comm.move_absolute(params)
            elif command == "move_axis":
                alias = params["alias"]
                position = params["position"]
                speed = params["speed"]
                acceleration = params["acceleration"]

                with AxisMaximumSpeedAndAcceleration(self._comm, alias, speed, acceleration):
                    cmd_id = self._comm.move_absolute({alias: position})
            elif command == "tare":
                log.info("Tare force axes")
                cmd_id = self._comm.tare()
            elif command == "enable":
                log.info("Enable axes: %s", params)
                cmd_id = self.enable_axes(params)
            elif command == "disable":
                log.info("Disable axes: %s", params)
                cmd_id = self._comm.disable_axes(params)
            elif command == "set_axis_parameter":
                log.info("Setting axis {} parameter {} value to {}".format(params["axis"], params["param"], params["value"]))
                self._comm.set_axis_parameter(params["axis"], params["param"], params["value"])
            elif command == "home_switch_polarity":
                parameter = self._comm.get_axis_parameter(params["axis"], SMRegs.SMP_TRAJ_PLANNER_HOMING_BITS)

                # 0 bit is negative polarity and 1 bit is positive polarity.
                if params["value"] == "positive":
                    parameter = parameter | SMRegs.HOMING_POS_HOME_SWITCH_POLARITY

                    log.info("Changing axis {} home switch polarity to positive.".format(params["axis"]))

                    self._comm.set_axis_parameter(params["axis"], SMRegs.SMP_TRAJ_PLANNER_HOMING_BITS, parameter)
                elif params["value"] == "negative":
                    parameter = parameter & (~SMRegs.HOMING_POS_HOME_SWITCH_POLARITY)

                    log.info("Changing axis {} home switch polarity to negative.".format(params["axis"]))

                    self._comm.set_axis_parameter(params["axis"], SMRegs.SMP_TRAJ_PLANNER_HOMING_BITS, parameter)
                elif params["value"] == "keep":
                    pass  # Keep original value.
                else:
                    raise Exception("Home switch polarity must be 'positive', 'negative' or 'keep'.")

            elif command == "control_mode":
                for axis, control_mode in params.items():
                    log.info("Setting axis {} control mode to {}".format(axis, control_mode))

                    if control_mode == "torque":
                        self._comm.set_axis_parameter(axis, SMRegs.SMP_CONTROL_MODE, SMRegs.CM_TORQUE)
                    elif control_mode == "position":
                        self._comm.set_axis_parameter(axis, SMRegs.SMP_CONTROL_MODE, SMRegs.CM_POSITION)
                    else:
                        raise RuntimeError("Unknown control mode: {}".format(control_mode))
            elif command == "check_axis_position_limits":
                log.info('Checking axis position limits: %s', params)
                for axis, axis_test_spec in params.items():
                    retries = axis_test_spec['retry_limit']
                    while not self._test_axis_position_limits(axis, axis_test_spec):
                        if retries == 0:
                            raise Exception(
                                "Axis '{}' limit check maximum retry amount reached. "
                                "Try manually moving the axis to both ends of the axis's "
                                "movement range and then restarting TnT Server. "
                                "See troubleshooting section in the user manual for more details.".format(axis))
                        log.warning("Axis '%s' limit check failed. Retrying homing.", axis)
                        self._home_axes([axis])
                        retries -= 1
            elif command == "execute":
                # params is a function object with signature "def f()".
                params()
            # TODO: What is the purpose of update_position? Can we remove it?
            elif command == "update_position":
                if cmd_id is not None:
                    self._waiter.wait(cmd_id)
                position = self._comm.get_position()
                log.info("Initializing robot kinematics with homed position: %s", position)
                params(position)
            else:
                raise RuntimeError("Unknown command in homing_sequence(): {}".format(command))

            # Wait for homing command to complete.
            if cmd_id is not None:
                self._waiter.wait(cmd_id)

    def _home_axes_simultaneously(self, axes_list):
        """
        Homes all axes. Axes that have the same homing priority are homed simultaneously by Optomotion.
        :param axes_list: List of axes to home. Force axes are not supported. Use _home_axes() for force axes.
        :return: None.
        """

        cmd_id = self._comm.home_axes(axes_list)

        # Wait for homing command to complete.
        if cmd_id is not None:
            self._waiter.wait(cmd_id)

        log.debug("Finished homing axes {}".format(axes_list))

        return None

    def _home_axes(self, axes_list):
        """
        Homes all axes in the list and does special homing for force-enabled axes.
        :param axes_list: List of axes to home.
        :return: None.
        """
        for axis_name in axes_list:
            log.info("Homing axis {}".format(axis_name))
            if self.force_is_supported(axis_name):
                # TODO: Should there be some check to see if homing is complete?
                self._comm.set_axis_parameter(axis_name, SMRegs.SMP_FORCE_MODE, SMRegs.FORCE_MODE_FORCE_CTRL)
                self._comm.clear_errors()
                self._comm.set_axis_parameter(axis_name, SMRegs.SMP_FORCE_MODE, SMRegs.FORCE_MODE_POS_CTRL)
            cmd_id = self._comm.home_axes([axis_name, ])
            # Wait for homing command to complete.
            if cmd_id is not None:
                self._waiter.wait(cmd_id)

            log.debug("Finished homing axis {}".format(axis_name))

        return None

    def force_is_supported(self, axis_name):
        """
        Checks if axis has force support enabled.
        :param axis_name: Name of axis.
        :return: True if force control is supported for this axis.
        """

        # Check force support from axis specs (from configuration file)
        for _, specs in self._kinematics.specs().items():
            if axis_name == specs['alias']:
                return specs.get('force_support', False)
        return False

    def _test_axis_position_limits(self, axis, axis_test_spec):
        """
        Checks that the axis can move to set position limits with given tolerance. Used to verify voice coil homing.
        :param axis: Name of axis to test.
        :param axis_test_spec: Dictionary containing axis test parameters.
        :return: True if the axis can reach both min and max position limits within given tolerance, False otherwise.
        """
        axis_spec = self._comm.get_axis_spec(axis)

        with AxisMaximumSpeedAndAcceleration(self._comm, axis, axis_test_spec['speed'], axis_test_spec['acceleration']):
            move_to_min_successful = self.test_move_to_position(axis, axis_spec.position_limits.min,
                                                                axis_test_spec['settling_timeout'],
                                                                axis_test_spec['limit_check_tolerance'])
            move_to_max_successful = self.test_move_to_position(axis, axis_spec.position_limits.max,
                                                                axis_test_spec['settling_timeout'],
                                                                axis_test_spec['limit_check_tolerance'])

            # Return the axis back to home position
            cmd_id = self._comm.move_absolute({axis: 0})
            # Wait for move command to complete
            self._waiter.wait(cmd_id)

        return move_to_min_successful and move_to_max_successful

    def test_move_to_position(self, axis, position, settling_timeout, tolerance):
        """
        Test that the given axis moves to the given position in the allocated time and with the given tolerance.
        :param axis: Name of the tested axis.
        :param position: Target position of the axis.
        :param settling_timeout: How long to wait for axis to settle to stable position before giving up.
        :param tolerance: Tolerance in millimeters for difference between given position and read axis position.
        :return: True if final axis position is within tolerance of the given position, False otherwise.
        """
        close_to_position = False

        cmd_id = self._comm.move_absolute({axis: position})
        # Wait for move command to complete
        self._waiter.wait(cmd_id)
        # Depending on robot tuning the position may be reached a while after the command has finished.
        # This should not take long, but we set a timeout just in case there is something wrong and the position
        # does not stabilize.
        start_time = time.time()
        while time.time() - start_time < settling_timeout:
            close_to_position = np.isclose(self._comm.get_position()[axis], position, atol=tolerance)
            if close_to_position:
                break

        return close_to_position

    @property
    def error(self):
        if self._comm is not None:
            return self._comm.get_errors()
        return ["Can not connect to robot"]

    def enable_axes(self, axes):
        for axis in axes:
            log.debug("Enabling axis {}.".format(axis))

            value = self.get_axis_parameter(axis, SMRegs.SMP_CONTROL_BITS1)

            value |= SMRegs.SMP_CB1_ENABLE

            self.set_axis_parameter(axis, SMRegs.SMP_CONTROL_BITS1, value)

    def is_axis_enabled(self, axis):
        status = self._comm.get_axis_parameter(axis, SMRegs.SMP_STATUS)

        return status & SMRegs.SMP_STAT_ENABLED

    def disable_axes(self, axes):
        self._comm.disable_axes(axes)

    def reset_error(self):
        self._comm.clear_errors()

    def home(self):
        self._do_homing()

    def get_joint_positions(self):
        p = self._comm.get_position()
        return p

    def get_joint_setpoints(self):
        setpoints = {}

        for value in self._kinematics.specs().values():
            alias = value["alias"]
            setpoints[alias] = self.get_scaled_axis_setpoint(alias)

        return setpoints

    def move_absolute(self, axes, with_speed=False):
        return self._comm.move_absolute(axes, with_speed=with_speed)

    def move_joint_position(self, joint_position, speed, acceleration):
        """
        Move joints to given positions from current positions in joint space.
        Note that speed and acceleration units make sense only if all axes have the same units.
        Blocks until movement is complete.
        :param joint_position: Dict {"x": 200, "y": 400} where positions are in workspace units e.g. mm.
        :param speed: Speed in axis units per seconds e.g. mm/s.
        :param acceleration: Acceleration in axis units per seconds squared e.g. mm/s^2.
        """
        buffer = plan_joint_motion(self.get_joint_setpoints(), joint_position, speed, acceleration)

        if buffer:
            self.move_buffered(buffer)

    def move_buffered(self, axes):
        self.check_buffered_position_limits(axes)

        # Store a copy of axes for possible inspection.
        if self.executed_axes is not None:
            self.executed_axes.append(copy.copy(axes))

        v = self._comm.move_buffered(axes)

        while self._comm.is_busy():
            pass

        return v

    def frame(self, tool=None, kinematic_name=None, calibrated=True):
        """
        Return current robot position as frame only
        :param tool: toolframe as 4x4 matrix
        :param kinematic_name: kinematics name to use
        :param calibrated: calibrated or not position
        :return: current robot position as frame only
        """
        p = self.position(tool, kinematic_name, calibrated)
        return p.frame

    def position(self, tool, kinematic_name, calibrated=True, return_joint_positions=False):
        """
        Return current robot position.
        :param tool: toolframe as 4x4 matrix
        :param kinematic_name: kinematics name to use
        :param calibrated: calibrated or not position
        :param return_joint_positions: If True, return also joint positions.
        :return: Current robot position or (robot_pos, joint_pos) if return_joint_positions is True.
        """
        joints = self.get_joint_positions()

        if tool is None:
            raise(Exception("no tool provided goldenmov.position"))
        if kinematic_name is None:
            raise(Exception("no name provided goldenmov.position"))

        pos = self._kinematics.joints_to_position(joints, tool=tool, kinematic_name=kinematic_name, calibrated=calibrated)

        if return_joint_positions:
            return pos, joints
        else:
            return pos

    def create_robot_position(self, **kwargs):
        """
        Create robot position object according to kinematics.
        :param kwargs: Keyword arguments for robot position init.
        :return: RobotPosition object.
        """
        return self._kinematics.create_robot_position(**kwargs)

    def exec_positions(self, positions: list, toolframe, kinematic_name: str):
        if toolframe is None:
            toolframe = robotmath.identity_frame()

        self.check_position_limits(positions, toolframe)

        #
        # Fill buffered_positions from list of positions given to the function
        # the positions given may or may not have values for axis
        # if the values are not found, fill previous values (or values read from the robot)
        #
        buffered_positions = {a: [] for a in self._supported_axis}
        joint_setpoints = self.get_joint_setpoints()
        toolframe_inv = toolframe.I
        for joints in self._kinematics.positions_to_joints(positions, tool_inv=toolframe_inv, kinematic_name=kinematic_name):

            # If some joint is missing in joints, add it with value None.
            # These values are handled after all buffered positions have been collected.
            for joint_name in buffered_positions:
                if joint_name not in joints:
                    joints[joint_name] = None

            for joint_name in joints:
                joint_position = joints[joint_name]
                buffered_positions[joint_name].append(joint_position)

        # Handle None values in buffered_positions.
        for joint_name in self._supported_axis:
            if np.all(np.equal(np.array(buffered_positions[joint_name]), None)):
                # If all positions of a joint are None, remove the position buffer entirely.
                del buffered_positions[joint_name]

            # if there is at least one None value, but not all are None
            elif np.any(np.equal(np.array(buffered_positions[joint_name]), None)):
                # If a joint has some None values, replace them with current joint setpoint.
                positions = buffered_positions[joint_name]
                current_position = joint_setpoints[joint_name]

                # replace None values as a vectorized operation
                pos_array = np.array(positions)
                pos_array[np.isnan(pos_array.astype(float))] = current_position
                buffered_positions[joint_name] = pos_array.tolist()

        self._kinematics.check_dynamic_position_limits(buffered_positions)

        buffered_positions, _ = limit_trajectory_speed_and_acceleration(buffered_positions,
                                                                     self._kinematics.specs(), TIME_STEP)

        log_trajectory_stats(buffered_positions, TIME_STEP)

        self.move_buffered(buffered_positions)

    def get_axis_spec_by_alias(self, alias):
        specs = self._comm.get_axis_specs()

        for spec in specs:
            if spec.alias == alias:
                return spec

    def get_joint_limits(self):
        limits = {}

        specs = self._comm.get_axis_specs()

        for spec in specs:
            if spec.position_limits is not None:
                limits[spec.alias] = (spec.position_limits.min, spec.position_limits.max)

        return limits

    def get_joint_status(self):
        status = {}

        specs = self._comm.get_axis_specs()

        for spec in specs:
            enabled = self.is_axis_enabled(spec.alias)

            status[spec.alias] = {"enabled": enabled}

        return status

    def check_position_limits(self, positions, toolframe):
        """
        Check position limits in workspace coordinate system in case position_limits has been specified.
        Positions are effector positions in workspace (in contrast to joint positions).
        :param positions: List of robot positions in workspace coordinate system
        """
        if self.position_limits is None:
            return

        # Need to remove effect of tool on the position when imposing the limits.
        inv_tool = toolframe.I

        # Parse min and max position limits for x, y, z axes.
        # In case no limit is specified, use -inf as min limit and inf as max limit (position is unaffected by these).
        min_limits = {
            "x": self.position_limits.get("x_min", float("-inf")),
            "y": self.position_limits.get("y_min", float("-inf")),
            "z": self.position_limits.get("z_min", float("-inf"))
        }

        max_limits = {
            "x": self.position_limits.get("x_max", float("inf")),
            "y": self.position_limits.get("y_max", float("inf")),
            "z": self.position_limits.get("z_max", float("inf"))
        }

        for p in positions:
            x, y, z = robotmath.frame_to_xyz(p.frame * inv_tool)

            pos = {"x": x, "y": y, "z": z}

            for name in ["x", "y", "z"]:
                if pos[name] < min_limits[name]:
                    raise AxisLimitError(
                        "Position '{}' attempted to move below minimum limit {}".format(name, min_limits[name]))

                if pos[name] > max_limits[name]:
                    raise AxisLimitError(
                        "Position '{}' attempted to move above maximum limit {}".format(name, max_limits[name]))

    def check_buffered_position_limits(self, buffered_positions):
        """
        Check that buffered positions are within axis limits.
        Buffered positions are joint positions (in contrast to effector position).
        Raises exception in case of axis limit violation.
        :param buffered_positions: Dictionary of axis position lists.
        """

        # Don't check buffered positions if position_limits is defined.
        # They are defined in case axis limits can't be used to determine workspace limits.
        if self.position_limits is not None:
            return

        for alias, positions in buffered_positions.items():
            spec = self.get_axis_spec_by_alias(alias)

            p = np.array(positions)

            if np.any(p < spec.position_limits.min):
                raise AxisLimitError("Axis '{}' attempted to move below minimum limit {}"
                                     .format(alias, spec.position_limits.min))

            if np.any(p > spec.position_limits.max):
                raise AxisLimitError("Axis '{}' attempted to move above maximum limit {}"
                                     .format(alias, spec.position_limits.max))

    def get_finger_separation_limits(self):
        """
        Get minimum and maximum limits of finger separation if robot has such properties.
        These are not the limits of the axis but rather the limits of axis-to-axis finger distances.
        Usually at axis position 0 fingers are at certain non-zero axis-to-axis home separation.
        :return: Minimum and maximum limits.
        """
        spec = self.get_axis_spec_by_alias("separation")

        if spec is None or not hasattr(self._kinematics, "home_separation"):
            raise Exception("Robot does not define finger separation limits.")

        # Spec limits are joint limits. Add home separation to transform to finger axis-to-axis separation limits.
        min_limit = spec.position_limits.min + self._kinematics.home_separation
        max_limit = spec.position_limits.max + self._kinematics.home_separation

        # Decrease limit range by small margin to make sure robot can actually be commanded to given
        # values in case there is some round-off error.
        margin = 0.001
        min_limit += margin
        max_limit -= margin

        return [min_limit, max_limit]

    def bounds(self, tool, kinematic_name):
        """
        Calculates current working area bounds with
         - current possible tilt/azimuth/spin angles if any
         - current tool attached
        :return: (dict) x, y, z bounds
        """
        bounds = None

        if self.position_limits is None:
            specs = self._comm.get_axis_specs()
            axis = {}
            for a in specs:
                axis[a.alias] = a

            x_axis = axis.get('x', None)
            y_axis = axis.get('y', None)
            z_axis = axis.get('z', None)

            x_positions = [0, 0] if x_axis is None else [x_axis.position_limits.min, x_axis.position_limits.max]
            y_positions = [0, 0] if y_axis is None else [y_axis.position_limits.min, y_axis.position_limits.max]
            z_positions = [0, 0] if z_axis is None else [z_axis.position_limits.min, z_axis.position_limits.max]

            large_number = 1000000

            bounds = {
                'x': [large_number, -large_number],
                'y': [large_number, -large_number],
                'z': [large_number, -large_number]
            }

            current_joints = self.get_joint_positions()

            for x in x_positions:
                for y in y_positions:
                    for z in z_positions:
                        current_joints['x'] = x
                        current_joints['y'] = y
                        current_joints['z'] = z

                        m = self._kinematics.joints_to_position(current_joints, kinematic_name=kinematic_name, tool=tool).frame
                        px, py, pz = robotmath.frame_to_xyz(m)

                        if px < bounds['x'][0]:
                            bounds['x'][0] = px
                        if px > bounds['x'][1]:
                            bounds['x'][1] = px
                        if py < bounds['y'][0]:
                            bounds['y'][0] = py
                        if py > bounds['y'][1]:
                            bounds['y'][1] = py
                        if pz < bounds['z'][0]:
                            bounds['z'][0] = pz
                        if pz > bounds['z'][1]:
                            bounds['z'][1] = pz
        else:
            tool_x, tool_y, tool_z = robotmath.frame_to_xyz(tool)

            # Take the tool offset into account in workspace bounds that are imposed on the effector.
            # It is assumed here that the effector local z points down in workspace. This is typically the case.
            bounds = {
                'x': [self.position_limits['x_min'] - tool_x, self.position_limits['x_max'] - tool_x],
                'y': [self.position_limits['y_min'] + tool_y, self.position_limits['y_max'] + tool_y],
                'z': [self.position_limits['z_min'] - tool_z, self.position_limits['z_max'] - tool_z]
            }

        # Shrink bounds a little bit to avoid hitting controller limits due to e.g. numerical inaccuracy.

        def set_range_margin(rng, margin):
            rng[0] -= margin
            rng[1] += margin

        bounds_margin = -1.0
        set_range_margin(bounds['x'], bounds_margin)
        set_range_margin(bounds['y'], bounds_margin)
        set_range_margin(bounds['z'], bounds_margin)

        return bounds

    def get_axis_parameter(self, axis, parameter):
        """
        read SimpleMotion axis parameter
        :param axis: axis name as string, like 'x', 'azimuth', 'voicecoil1'
        :param parameter: either parameter enum value or parameter name; 410 or 'SMP_TORQUELIMIT_CONT'
                          see simplemotion_defs
        :return: integer value
        """
        if isinstance(parameter, str):
            parameter = simplemotion_defs[parameter]
        return self._comm.get_axis_parameter(axis, int(parameter))

    def set_axis_parameter(self, axis, parameter, value):
        """
        write SimpleMotion axis parameter
        :param axis: axis name as string, like 'x', 'azimuth', 'voicecoil1'
        :param parameter: either parameter enum value or parameter name; 410 or 'SMP_TORQUELIMIT_CONT'
                          see simplemotion_defs
        :param value: integer value
        """
        if isinstance(parameter, str):
            parameter = simplemotion_defs[parameter]
        self._comm.set_axis_parameter(axis, int(parameter), int(value))

    def read_axis_parameter(self, axis, parameter):
        """
        Read SimpleMotion axis parameter
        :param axis: Axis name as string, like 'x', 'azimuth', 'voicecoil1'
        :param parameter: Either parameter enum value or parameter name; 410 or 'SMP_TORQUELIMIT_CONT',
                          see simplemotion_defs.
        """
        if isinstance(parameter, str):
            parameter = simplemotion_defs[parameter]
        return self._comm.read_axis_parameter(axis, int(parameter))

    def get_axis_current(self, axis):
        """
        Get axis current limit (torque, force) as Amperes (A)
        :param axis: axis name, like 'x', 'azimuth' or 'voicecoil1'
        :return current (A)
        """
        ma = self.get_axis_parameter(axis, 'SMP_TORQUELIMIT_PEAK')
        return ma / 1000

    def set_axis_current(self, axis, amperes):
        """
        Set axis current limit (torque, force) as Amperes (A)
        :param axis: axis name, like 'x', 'azimuth' or 'voicecoil1'
        :param amperes: current (A)
        """
        ma = amperes * 1000
        self.set_axis_parameter(axis, 'SMP_TORQUELIMIT_PEAK', int(ma))

    def get_scaled_axis_setpoint(self, axis_alias):
        """
        Get axis setpoint from axis controller.
        The value is scaled to units used by TnT server i.e. linear axis value is in mm
        and rotational axis value is in degrees.
        :param axis_alias: Name of axis e.g. 'x'.
        :return: Scaled axis setpoint.
        """
        return self._comm.get_scaled_axis_setpoint(axis_alias)

    def set_axis_force_mode(self, axis, mode):
        """
        Set force mode of axis. This method should be preferred over setting the mode directly
        via set_axis_parameter because kinematics may need to react to force mode changes.
        :param axis: Axis name e.g. "x".
        :param mode: Force mode e.g. SMRegs.FORCE_MODE_FORCE_CTRL.
        """

        self.kinematics.pre_force_mode_change(axis, mode)

        self.set_axis_parameter(axis, SMRegs.SMP_FORCE_MODE, mode)


class AxisMaximumSpeedAndAcceleration:
    """
    State class to temporarily set axis speed to maximum values allowed in kinematics for position limit test.
    """
    def __init__(self, comm, axis, speed, acceleration):
        self.comm = comm
        self.axis = axis
        self.speed = speed
        self.acceleration = acceleration

    def __enter__(self):
        self.comm.limit_axis_speeds({self.axis: self.speed})
        self.comm.limit_axis_accelerations({self.axis: self.acceleration})

    def __exit__(self, *args, **kwargs):
        self.comm.clear_axis_limits()


class AxisParameterContext:
    """
    Class for changing axis parameter values temporarily to some specific values and then
    reverting to original values.
    Context can be managed manually as:
        context.read_current_parameters()
        context.apply_new_parameters()
        # Do something.
        context.apply_original_parameters()
    or automatically if the scope of the context is well-defined:
        with context:
            # Do something.
    """
    def __init__(self, driver, axis_name, parameters):
        self.driver = driver
        self.axis_name = axis_name
        self.original_parameters = {}
        self.parameters = parameters

    def read_current_parameters(self):
        self.original_parameters = {register: self.driver.get_axis_parameter(self.axis_name, register) for register in self.parameters.keys()}

    def apply_new_parameters(self):
        for register in self.parameters.keys():
            if register not in self.original_parameters:
                raise Exception("Original parameters must be read before applying new parameters when using AxisParameterStore.")

        for register, value in self.parameters.items():
            self.driver.set_axis_parameter(self.axis_name, register, value)

    def apply_original_parameters(self):
        for register, value in self.original_parameters.items():
            self.driver.set_axis_parameter(self.axis_name, register, value)

    def __enter__(self):
        self.read_current_parameters()
        self.apply_new_parameters()

    def __exit__(self, *args, **kwargs):
        self.apply_original_parameters()


def create_track(max_speed, acceleration, distance):
    if max_speed <= 0:
        raise Exception("Parameter max_speed must be positive.")
    if acceleration <= 0:
        raise Exception("Parameter acceleration must be positive.")
    if distance < 0:
        raise Exception("Parameter distance must be non-negative.")

    positions = []
    if distance == 0:
        positions.append((0, 0))
        return positions

    t1 = max_speed / acceleration
    s1 = 0.5 * acceleration * (t1 ** 2)

    if s1 > distance / 2:
        s1 = distance / 2
        t1 = math.sqrt(s1 / (0.5 * acceleration))

    v1 = acceleration * t1

    s2 = distance - s1
    t2 = t1 + (s2 - s1) / v1

    # acceleration until t1
    # deceleration from t2
    t3 = t1 + t2

    current_time = 0
    while current_time < t3:

        t = current_time
        current_time += TIME_STEP

        if t <= t1:
            # accelerate
            location = 0.5 * acceleration * (t ** 2)
            #speed = math.sqrt(2 * acceleration * location)
            #mode = "accelerate"
        elif t >= t2:  # s0 + v0*t + 0.5*a*(t**2)
            # decelerate
            t_ = t - t2
            location = s2 + v1 * t_ - 0.5 * acceleration * (t_ ** 2)
            #speed = v1 - math.sqrt(2 * acceleration * (location - s2))
            #mode = "decelerate"
        else:
            # travel
            location = s1 + (t - t1) * v1

        # could return time, speed, mode, etc. too
        positions.append((location, t))

    return positions


def calculate_track_duration(max_speed, acceleration, distance):
    """
    Calculate the time duration of a track.
    :param max_speed: Max speed during the track.
    :param acceleration: Acceleration used in the track.
    :param distance: Travel distance.
    :return: Track duration in seconds.
    """
    return len(create_track(max_speed, acceleration, distance)) * TIME_STEP


def plan_joint_motion(joint_setpoints, joint_position, speed, acceleration):
    """
    Move joints to given positions from current positions in joint space.
    Note that speed and acceleration units make sense only if all axes have the same units.
    :param joint_setpoints: Dict of current joint setpoints.
    :param joint_position: Dict {"x": 200, "y": 400} where positions are in workspace units e.g. mm.
    :param speed: Speed in axis units per seconds e.g. mm/s.
    :param acceleration: Acceleration in axis units per seconds squared e.g. mm/s^2.
    """
    buffer = {}

    # Determine which axis travels longest distance.
    max_distance = 0

    for axis, target_position in joint_position.items():
        # Use setpoint as starting position. Works usually better if axis has been moved against obstacle.
        current_position = joint_setpoints[axis]

        distance = abs(target_position - current_position)

        max_distance = max(max_distance, distance)

    # Compute track according to longest distance to make the axis buffers have the same length.
    # This means that given speed and acceleration are realized for the axis which travels longest
    # distance. Other axes move more slowly.
    track = create_track(speed, acceleration, max_distance)

    for axis, target_position in joint_position.items():
        # Use setpoint as starting position. Works usually better if axis has been moved against obstacle.
        current_position = joint_setpoints[axis]

        distance = abs(target_position - current_position)

        if distance == 0:
            continue

        if axis not in buffer:
            buffer[axis] = []

        for d, _ in track:
            # Interpolation coordinate in [0, 1]. Compute according to maximum distance.
            interp = d / max_distance

            buffer[axis].append(current_position + interp * (target_position - current_position))

    return buffer