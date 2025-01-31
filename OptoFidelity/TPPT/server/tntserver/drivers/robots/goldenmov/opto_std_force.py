import logging
import time
from scipy import interpolate

import tntserver.drivers.robots.sm_regs as SMRegs
from tntserver.drivers.robots.goldenmov.force import Force
from tntserver import robotmath

log = logging.getLogger(__name__)


def require_force_support(func):
    """
    Decorator to verify that drive supports force related functionality before trying to execute called function.
    """

    def f(self, *args, **kwargs):
        if self._force_supported:
            return func(self, *args, **kwargs)
        else:
            raise Exception("Failed to execute {}, force control is not supported.".format(func.__name__))

    return f


class OptoStdForce(Force):
    """
    Implements Opto Standard Force for robot that has voice coil and load cell feedback.
    Requires special force firmware for the voice coil axis.
    - Convert actual force values <-> setpoint force values
    - Implement press gesture
    - Implement drag force gesture
    """
    def __init__(self, robot, parameters):
        super().__init__(robot)

        self._comm = robot.driver._comm
        self._driver = robot.driver

        self._axis = parameters.get("axis_name", "voicecoil1")

        self._no_contact_force_threshold = parameters.get("no_contact_force_threshold", 20)  # [g]
        self._no_contact_force_stabilization_time = parameters.get("no_contact_force_stabilization_time", 5.0)
        self._voicecoil_speed = parameters.get('voicecoil_speed', 50)
        self._voicecoil_acceleration = parameters.get('voicecoil_acceleration', 30000)
        self._force_tare_threshold = parameters.get("force_tare_threshold", 0.5)  # [g]
        self._force_tare_stabilization_time = parameters.get("force_tare_stabilization_time", 2)  # [s]
        self._force_tare_timeout = parameters.get("force_tare_timeout", 10)
        self._press_start_height = parameters.get("press_start_height", 1)

        self._force_seek_surface = parameters.get("seek_surface", True)
        self._force_touch_probing_velocity = parameters.get("force_touch_probing_velocity", 1.0)  # velocity in mm/s
        self._force_touch_probing_acceleration = parameters.get("force_touch_probing_acceleration", 100)  # acceleration in mm/s^2
        self._force_touch_probing_threshold = parameters.get("force_touch_probing_threshold", 10)  # touch threshold in grams
        self._scope_force = parameters.get("scope_force", False)
        self._scope_capture_percents_before_trigger = parameters.get("score_capture_percents_before_trigger", 0)
        self._scope_sample_rate = parameters.get("scope_sample_rate", 500)

        self.min_force = parameters.get('min_force', 25)
        self.max_force = parameters.get('max_force', 800)
        self.force_calibration_window_size = parameters.get("force_calibration_window_size", 100)

        self._force_setpoint_multiplier = 1000

        # Optomotion Scope object.
        self._scope = None
        self._force_feedback_raw = None
        self._force_feedback_calibrated = None

        # Dicts for force conversion functions
        self._actual_to_setpoint = {}
        self._setpoint_to_actual = {}

        spec = self._comm.get_axis_spec(self._axis)

        self._acceleration_setpoint_multiplier = spec.scaling_factors.acceleration
        self._position_setpoint_multiplier = spec.scaling_factors.posToDevice
        self._setpoint_position_multiplier = spec.scaling_factors.posFromDevice
        self._velocity_setpoint_multiplier = spec.scaling_factors.velocity

        self._force_supported = self.robot.driver.force_is_supported(self._axis)

        if parameters.get("tare_on_init", True) and self.robot.driver.force_is_supported(self._axis):
            self.force_tare()

    @property
    def axis(self):
        """
        Name of axis used to apply force.
        """
        return self._axis

    def set_force_calibration_table(self, table):
        """
        Set interpolation table for force calibration data.
        :param table: Dict where key is axis name and value is of type {"force": [], "current": []}}.
        """
        for axis_name, data in table.items():
            self._force_functions_from_calibration_table(axis_name, data)

    def _force_functions_from_calibration_table(self, axis_name, data):
        """
        Generate force conversion function for the given axis from calibration table data
        :param axis_name: Axis to generate functions for
        :param data: Calibration data as dict {"actual_values": [], "setpoint_values": []}}.
        """
        # Read measurement data from calibration data stored in server configuration file
        try:
            actual_values = data['actual_values']
            setpoint_values = data['setpoint_values']

            # Create linear fits for conversions and add to function dictionary
            # Setpoint as function of actual value
            self._setpoint_to_actual[axis_name] = interpolate.interp1d(actual_values, setpoint_values,
                                                                       fill_value='extrapolate')
            # Actual values as function of setpoint
            self._actual_to_setpoint[axis_name] = interpolate.interp1d(setpoint_values, actual_values,
                                                                       fill_value='extrapolate')

            log.debug("Updated force calibration functions.")

        except (AttributeError, TypeError, KeyError):
            # No calibration data property defined at all, create an empty one
            log.error('No calibration data for force application is available.')

    def _set_axis_parameter(self, reg, val):
        """
        Set force axis parameter:
        Use this method if you're forgetting to cast parameter value to int.
        :param reg: Register ID.
        :param val: Parameter value.
        """
        return self._comm.set_axis_parameter(self._axis, reg, int(val))

    def set_axis_parameter(self, param, value):
        """
        Set force axis parameter value.
        :param param: Parameter ID.
        :param value: Parameter value.
        """
        self._comm.set_axis_parameter(self._axis, param, value)

    def get_axis_parameter(self, reg):
        """
        Get force axis parameter value.
        :param reg: Register ID.
        :return: Value.
        """
        return self._comm.get_axis_parameter(self._axis, reg)

    def _start_scope(self):
        log.debug("Scoping at sample rate {}.".format(self._scope_sample_rate))

        self._scope = self._comm.get_scope(self._axis)

        self._scope.setup(samplerate=self._scope_sample_rate,
                          scope_variables=[SMRegs.ScopeVariables.CAPTURE_DEBUG2],
                          trigger=SMRegs.ScopeTriggers.TRIG_INSTANT,
                          capture_percents_before_trigger=self._scope_capture_percents_before_trigger)

        self._scope.start()

    def _stop_scope(self, duration):
        self._scope.stop()

        # We scope only one channel so take the first member of the list.
        scope_results = self._scope.download()[0]

        # scope_results has always 2048 samples. Take only samples within force mode duration.
        if duration is not None:
            num_samples = int(round(self._scope_sample_rate * duration))

            if num_samples > 2048:
                log.warning(
                    "Number of samples exceeds buffer size 2048. Data is truncated. Decrease sample rate or duration.")

            num_samples = min(num_samples, len(scope_results))
            scope_results = scope_results[:num_samples]

        # Scope data is in units of 10 mg. Convert to grams.
        self._force_feedback_raw = [float(force) * 0.01 for force in scope_results]

        if self._axis in self._actual_to_setpoint:
            self._force_feedback_calibrated = [float(self._actual_to_setpoint[self._axis](force)) for force in
                                               self._force_feedback_raw]
        else:
            self._force_feedback_calibrated = None

        self._scope = None

    def _set_target_setpoint(self, setpoint_mm):
        """
        Sets axis position setpoint.
        :param setpoint_mm: target setpoint in [mm]
        """
        setpoint = int(setpoint_mm * self._position_setpoint_multiplier)
        log.debug("set_target_setpoint to {:.3f} mm ({})".format(setpoint_mm, setpoint))

        self._set_axis_parameter(SMRegs.SMP_ABSOLUTE_SETPOINT, int(setpoint))

    def get_current_position(self):
        """
        Get current axis position.
        :return: Axis position in mm.
        """
        current_position = self._comm.get_axis_parameter(self._axis, SMRegs.SMP_ACTUAL_POSITION_FB) * self._setpoint_position_multiplier

        return current_position

    def get_current_setpoint(self):
        """
        Get current axis setpoint.
        :return: Axis setpoint in mm.
        """
        setpoint = self._comm.get_scaled_axis_setpoint(self._axis)

        return setpoint

    def set_continuous_and_peak_current_limits(self, continous_current_limit, peak_current_limit):
        """
        Sets current limits for allowed continuous and peak current.
        :param continous_current_limit: Continuous current limit in mA.
        :param peak_current_limit: Peak current limit in mA.
        """
        if peak_current_limit is not None:
            self._set_axis_parameter(SMRegs.SMP_TORQUELIMIT_PEAK, peak_current_limit)

        if continous_current_limit is not None:
            self._set_axis_parameter(SMRegs.SMP_TORQUELIMIT_CONT, continous_current_limit)

    def get_continuous_and_peak_current_limits(self):
        """
        Reads limits for continuous and peak current.
        :return: Continuous and peak current limits in mA as a tuple.
        """
        ccl = self._comm.get_axis_parameter(axis=self._axis, param=SMRegs.SMP_TORQUELIMIT_CONT)
        cpl = self._comm.get_axis_parameter(axis=self._axis, param=SMRegs.SMP_TORQUELIMIT_PEAK)

        return ccl, cpl

    @require_force_support
    def get_current_force_reading(self):
        """
        :return: Current force reading in milligrams of force.
        """
        force = self.get_axis_parameter(SMRegs.SMP_FORCE_FEEDBACK_VALUE)    # [mg]

        return force

    @require_force_support
    def in_contact(self):
        """
        Verify that actuator is in contact with DUT.
        :return: True if in contact, False otherwise.
        """
        if self.get_current_force_reading() > self._no_contact_force_threshold * 1000:
            return True
        else:
            return False

    @require_force_support
    def force_tare(self, threshold=None, stabilization_time=None, timeout=None):
        """
        Tares the loadcell to zero reading.
        :param threshold: Loadcell data variation must be within +/- threshold in grams.
        :param stabilization_time: Loadcell data must remain within +/- threshold for specified time in seconds.
        :param timeout: Timeout for tare in seconds.
        """

        if threshold is None:
            threshold = self._force_tare_threshold

        if stabilization_time is None:
            stabilization_time = self._force_tare_stabilization_time

        if timeout is None:
            timeout = self._force_tare_timeout

        # Store current setpoint to move there if tare fails.
        start_setpoint = self.get_current_setpoint()

        log.debug("Executing tare.")

        self._set_axis_parameter(SMRegs.SMP_FORCE_TARE_THRESHOLD, threshold * 1000)  # Convert to milligrams.
        self._set_axis_parameter(SMRegs.SMP_FORCE_TARE_STABILIZE_TIME, stabilization_time * 1000)  # Convert to ms.
        self._set_axis_parameter(SMRegs.SMP_FORCE_MODE, SMRegs.FORCE_MODE_POS_CTRL)
        self._set_axis_parameter(SMRegs.SMP_FORCE_MODE, SMRegs.FORCE_MODE_TARE)

        stop_time = time.time() + timeout

        while self._comm.get_axis_parameter(self._axis, SMRegs.SMP_FORCE_FUNCTIONS_STATUS) & (1 << SMRegs.FFS_TARE_BUSY):
            # Sleep for a while before polling the status again to prevent spamming the communication bus
            time.sleep(0.2)

            if time.time() > stop_time:
                self._set_axis_parameter(SMRegs.SMP_FORCE_MODE, SMRegs.FORCE_MODE_POS_CTRL)
                self.robot.move_joint_position({self._axis: start_setpoint})

                raise Exception("Force actuator tare timeout after {} s.".format(timeout))

        log.debug("Tare finished.")

        self._set_axis_parameter(SMRegs.SMP_FORCE_MODE, SMRegs.FORCE_MODE_POS_CTRL)

        if self._comm.get_axis_parameter(self._axis, SMRegs.SMP_FORCE_FUNCTIONS_STATUS) & (1 << SMRegs.FFS_TARE_SUCCESS):
            log.debug("Tare successful.")
            return None
        else:
            log.error("Taring of force actuator failed.")
            raise Exception("Tare failed")

    def enable_force_mode(self, force, calibrated):
        self.robot.set_current_limits(self.robot.voicecoil_cont_current, self.robot.voicecoil_peak_current)

        self.force_tare()

        # Move robot to surface so that force mode can start smoothly.
        if self._force_seek_surface:
            self.seek_surface()

        # Actual force is the one passed to drive.
        actual_force = force

        if calibrated:
            if self._axis not in self._setpoint_to_actual:
                raise Exception("No force calibration data for {}.".format(self._axis))

            actual_force = float(self._setpoint_to_actual[self._axis](force))

        self._driver.set_axis_force_mode(self._axis, SMRegs.FORCE_MODE_FORCE_CTRL)
        self._set_axis_parameter(SMRegs.SMP_ABSOLUTE_SETPOINT, actual_force * 1000)

        if self._scope_force:
            self._start_scope()

        log.debug("Applying {} grams of force (actual drive force {}).".format(force, actual_force))

    def disable_force_mode(self, duration=None, return_position=0):
        try:
            if self._scope is not None:
                self._stop_scope(duration)

            self._driver.set_axis_force_mode(self._axis, SMRegs.FORCE_MODE_POS_CTRL)

            self.robot.move_joint_position({self._axis: return_position})

            log.debug("Returning {} to {}.".format(self._axis, return_position))
        finally:
            self.robot.set_current_limits(self.robot.voicecoil_nominal_cont_current,
                                          self.robot.voicecoil_nominal_peak_current)

    @require_force_support
    def force_press(self, force, duration=1.0, use_calib: bool = True):
        """
        Applies specified force (use seek surface beforehand to ensure surface contact). If return position is given,
        actuator goes to position mode and lifts up.
        :param force: Force to apply in grams.
        :param duration: Duration of force press in seconds.
        :param use_calib: If True, use force calibration table.
        """
        with ForceMode(self, force, use_calib):
            time.sleep(duration)

    @require_force_support
    def seek_surface(self, pos=20, threshold=None, velocity=None, acceleration=None, timeout=20):
        """
        Find surface by advancing the actuator with given parameters.
        :param pos: Max. position the actuator will attempt to move.
        :param threshold: Threshold in grams for surface touch detection.
        :param velocity: Seeking velocity in mm/s.
        :param acceleration: Seeking acceleration in mm/s^2.
        :param timeout: Seeking timeout.
        :return Found surface position in mm.
        """
        threshold = threshold if threshold is not None else self._force_touch_probing_threshold
        velocity = velocity if velocity is not None else self._force_touch_probing_velocity
        acceleration = acceleration if acceleration is not None else self._force_touch_probing_acceleration

        velocity_setpoint = int(self._velocity_setpoint_multiplier * velocity)
        acceleration_setpoint = max(1, int(acceleration * self._acceleration_setpoint_multiplier))
        force_setpoint = int(threshold * self._force_setpoint_multiplier)

        # Store current setpoint to move there if tare fails.
        start_setpoint = self.get_current_setpoint()

        self._set_axis_parameter(SMRegs.SMP_VEL_LIMIT_IN_TOUCH_PROBING, velocity_setpoint)
        self._set_axis_parameter(SMRegs.SMP_ACCEL_LIMIT_IN_TOUCH_PROBING, acceleration_setpoint)
        self._set_axis_parameter(SMRegs.SMP_FORCE_TOUCH_THRESHOLD, force_setpoint)

        log.debug("Seeking surface...")
        self._set_axis_parameter(SMRegs.SMP_FORCE_MODE, SMRegs.FORCE_MODE_TOUCH_PROBE_CTRL)
        self._set_target_setpoint(pos)
        # SMP_FORCE_FUNCTIONS_STATUS - touch has happened when FFS_TOUCH_PROBE_SUCCESS
        stop_time = time.time() + timeout

        while not self._comm.get_axis_parameter(self._axis, SMRegs.SMP_FORCE_FUNCTIONS_STATUS) & \
                  (1 << SMRegs.FFS_TOUCH_PROBE_SUCCESS):
            time.sleep(0.02)

            if time.time() > stop_time:
                self._set_axis_parameter(SMRegs.SMP_FORCE_MODE, SMRegs.FORCE_MODE_POS_CTRL)
                self.robot.move_joint_position({self._axis: start_setpoint})

                raise Exception("Surface find timeout after {} s.".format(timeout))

        log.debug("Surface seeking finished.")

        currpos = self.get_current_position()
        log.debug("Surface position: {:.3f}".format(currpos))

        return currpos

    def press(self, context, x: float, y: float, force: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                  duration: float = None, press_depth=None, tool_name=None):
        """
        Performs a force press with given parameters.

        :param context: Context where gesture is performed.
        :param x: Target x coordinate.
        :param y: Target y coordinate.
        :param force: Force in grams, to be activated after moving to lower position.
        :param z: Target z coordinate when hovering before and after gesture.
        :param tilt: Tilt angle .
        :param azimuth: Azimuth angle.
        :param duration: How long to keep finger down in seconds.
        :param press_depth: Here for compatibility reasons. Was used for open-loop voice coil force press.
        :param tool_name: Name of tool for perform gesture with. Currently not used.
        """

        f = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)
        f0 = f.copy()
        f1 = f.copy()
        f0.A[2, 3] = z
        f1.A[2, 3] = self._press_start_height

        prg = self.robot.program

        prg.begin(ctx=context, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        prg.move(prg.line(f0, f1))
        prg.run()

        # Verify that approach was successful. Effector shouldn't be in contact when executing robot.force_tare().
        if self.in_contact():
            # Just in case to avoid false positives, wait for a while and check again
            log.info("Waiting for robot movement to stabilize and checking again if end-effector is in contact.")
            time.sleep(self._no_contact_force_stabilization_time)
            if self.in_contact():
                # Return to start position.
                prg.begin(ctx=context, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                          kinematic_name=self.robot.default_kinematic_name)
                prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
                prg.move(prg.point(f0))
                prg.run()

                raise Exception("End-effector reports being in contact with the DUT. Cannot proceed with press gesture."
                                " Tried to lift.")

        self.force_press(force, duration=duration)

        # Return back to z height.
        prg.clear()
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move(prg.point(f0))
        prg.run()

        return {"force_feedback_raw": self._force_feedback_raw, "force_feedback_calibrated": self._force_feedback_calibrated}

    def drag_force(self, context, x1: float, y1: float, x2: float, y2: float, force: float, z: float = None,
                       tilt1: float = 0, tilt2: float = 0, azimuth1: float = 0, azimuth2: float = 0, tool_name=None):
        """
        Performs a drag with force with given parameters.

        :param context: Context where gesture is performed.
        :param x1: Start x coordinate.
        :param y1: Start y coordinate.
        :param x2: End x coordinate.
        :param y2: End y coordinate.
        :param force: Grams of force to apply.
        :param z: Target z coordinate when hovering before and after gesture.
        :param tilt1: Start tilt angle.
        :param tilt2: End tilt angle.
        :param azimuth1: Start azimuth angle.
        :param azimuth2: End azimuth angle.
        :param tool_name: Name of tool for perform gesture with. Currently not used.
        """

        drag_start_up = robotmath.xyz_euler_to_frame(x1, y1, z, 0, tilt1, -azimuth1)
        drag_force_start = robotmath.xyz_euler_to_frame(x1, y1, self._press_start_height, 0, tilt1, -azimuth1)
        drag_force_end = robotmath.xyz_euler_to_frame(x2, y2, self._press_start_height, 0, tilt2, -azimuth2)
        drag_end_up = robotmath.xyz_euler_to_frame(x2, y2, z, 0, tilt2, -azimuth2)

        prg = self.robot.program
        prg.begin(ctx=context, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        # Move to start position.
        prg.move(prg.line(drag_start_up, drag_force_start))
        prg.run()

        # Verify that approach was successful. Effector shouldn't be in contact when executing robot.force_tare().
        if self.in_contact():
            # Return to start position.
            prg.begin(ctx=context, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                      kinematic_name=self.robot.default_kinematic_name)
            prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
            prg.move(prg.point(drag_start_up))
            prg.run()

            raise Exception(
                "End effector reports being in contact with the DUT. Cannot proceed with press gesture. Tried to lift.")

        # Enable force.
        with ForceMode(self, force, calibrated=True):
            # Drag with force enabled.
            # Use "force" kinematics to omit voicecoil in kinematic calculations that assume position control.
            prg.begin(ctx=context, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                      kinematic_name="force")
            prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
            prg.move(prg.line(drag_force_start, drag_force_end))
            prg.run()

        # Return to starting position.
        prg.clear()
        prg.begin(ctx=context, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move(prg.line(drag_force_end, drag_end_up))
        prg.run()

        return {"force_feedback_raw": self._force_feedback_raw, "force_feedback_calibrated": self._force_feedback_calibrated}


class VoicecoilMaxContPeakCurrent:
    """
    State class to temporarily set maximum continuous current and peak current to the voicecoil.
    TODO: Implement using AxisParameterContext.
    """
    def __init__(self, robot, max_cont_current, peak_current):
        self._robot = robot
        self._max_cont_current = max_cont_current
        self._peak_current = peak_current
        self._original_max_cont_currents = None
        self._original_peak_currents = None

    def __enter__(self):
        # Store original settings and apply new values.
        # TODO: Read current values from drive.
        self._original_max_cont_currents = self._robot.voicecoil_nominal_cont_current
        self._original_peak_currents = self._robot.voicecoil_nominal_peak_current

        self._robot.set_current_limits(self._max_cont_current, self._peak_current)

    def __exit__(self, *args, **kwargs):

        # Restore original settings
        self._robot.set_current_limits(self._original_max_cont_currents, self._original_peak_currents)


class ForceMode:
    """
    Set axis to force mode with given force.
    """
    def __init__(self, force_driver, force, calibrated):
        self._force_driver = force_driver
        self._force = force
        self._calibrated = calibrated
        self._start_time = None
        self._return_position = None

    def __enter__(self):
        self._return_position = self._force_driver.get_current_setpoint()

        self._force_driver.enable_force_mode(self._force, self._calibrated)
        self._start_time = time.time()

    def __exit__(self, *args, **kwargs):
        self._force_driver.disable_force_mode(duration=time.time()-self._start_time,
                                              return_position=self._return_position)
