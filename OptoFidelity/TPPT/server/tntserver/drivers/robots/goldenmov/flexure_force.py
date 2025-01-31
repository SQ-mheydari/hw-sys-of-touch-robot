import logging

from tntserver.drivers.robots.goldenmov.opto_std_force import OptoStdForce
import tntserver.drivers.robots.sm_regs as SMRegs


log = logging.getLogger(__name__)


class FlexureForce(OptoStdForce):
    """
    Implements flexure force for robot that has flexure based force mechanism and voice coil to lock
    the flexure operation.
    Requires special force firmware for the z axis.
    Implementation is based around OptoStdForce because the force operation is largely the same except that
    voicecoil must be disabled when z axis is set to force mode.
    """
    def __init__(self, robot, parameters):
        # Make default value of seek_surface False as it is usually not needed with flexure.
        if "seek_surface" not in parameters:
            parameters["seek_surface"] = False

        super().__init__(robot, parameters)

        self.voicecoil_axis = parameters.get("voicecoil_axis_name", "voicecoil1")
        self._min_press_duration = parameters.get("min_press_duration", 1.0)

    def enable_force_mode(self, force, calibrated):
        if self.robot.driver.is_axis_enabled(self.voicecoil_axis):
            raise Exception("Voicecoil must be disabled before enabling force.")

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
        if self._scope is not None:
            self._stop_scope(duration)

        self._driver.set_axis_force_mode(self._axis, SMRegs.FORCE_MODE_POS_CTRL)

        self.robot.move_joint_position({self._axis: return_position})

        log.debug("Returning {} to {}.".format(self._axis, return_position))

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

        # Press duration needs to be at least some ad hoc value so that force setpoint is reached.
        # If force is disabled too quickly after it is enabled, the controller goes to some erroneous state.
        if duration < self._min_press_duration:
            duration = self._min_press_duration

            log.warning("Given press duration {} is less than minimum duration {}. Using the minimum duration.".
                        format(duration, self._min_press_duration))

        enable_voicecoil_after_force = False

        # VC must be disabled before moving to press height.
        if self.robot.driver.is_axis_enabled(self.voicecoil_axis):
            self.robot.disable_voicecoil()
            enable_voicecoil_after_force = True

        try:
            super().press(context=context, x=x, y=y, force=force, z=z, tilt=tilt, azimuth=azimuth, duration=duration,
                          press_depth=press_depth, tool_name=tool_name)
        finally:
            if enable_voicecoil_after_force:
                self.robot.enable_voicecoil()

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

        enable_voicecoil_after_force = False

        # VC must be disabled before moving to press height.
        if self.robot.driver.is_axis_enabled(self.voicecoil_axis):
            self.robot.disable_voicecoil()
            enable_voicecoil_after_force = True

        try:
            super().drag_force(context=context, x1=x1, y1=y1, x2=x2, y2=y2, force=force, z=z, tilt1=tilt1, tilt2=tilt2,
                               azimuth1=azimuth1, azimuth2=azimuth2, tool_name=tool_name)
        finally:
            if enable_voicecoil_after_force:
                self.robot.enable_voicecoil()
