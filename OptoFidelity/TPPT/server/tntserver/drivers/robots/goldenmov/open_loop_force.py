import tntserver.drivers.robots.sm_regs as SMRegs
from tntserver.drivers.robots.goldenmov.force import Force
from tntserver import robotmath
from scipy import interpolate
import time
import logging


log = logging.getLogger()


class OpenLoopForce(Force):
    """
    Implements open loop force functionality for robots that have a voice coil actuator.
    Robot may also have multiple voice coils and force can be applied with any of them individually
    or with all of them at once.
    - Convert force values <-> current values
    - Implement press gesture
    - Implement drag force gesture
    """
    def __init__(self, robot, parameters):
        super().__init__(robot)

        # Minimum and maximum currents in mA to use with force.
        self.min_current = parameters.get("min_current", 100)
        self.max_current = parameters.get("max_current", 1360)
        self.current_step = parameters.get("current_step", 100)

        # z-coordinate in DUT context before and after press.
        # Note that force calibration is bound to this value.
        self.press_distance = parameters.get("press_distance", 2.5)

        # z-coordinate in DUT context during press.
        self.press_depth = parameters.get("press_depth", -1.0)

        # z-coordinate in DUT context before and after drag.
        self.drag_distance = parameters.get("drag_distance", 2.5)

        # Voicecoil axis position during drag.
        self.drag_stroke = parameters.get("drag_stroke", 3.5)

        # z-coordinate in DUT context during drag.
        # In ideal case we would not need this parameter by we have some inconsistency in kinematics.
        # For synchro kinematics drag_clearance must equal drag_distance. This is the default.
        # For voicecoil kinematics drag_clearance should be drag_distance - drag_stroke.
        # This is due to the difference in how the kinematics consider voicecoil position during tool movement.
        # If default drag_clearance is used for VC robot, the drag will happen over the DUT instead of against it.
        self.drag_clearance = parameters.get("drag_clearance", self.drag_distance)

        self.driver = robot.driver

        self._current_to_grams = {}
        self._grams_to_current = {}

    @property
    def axis(self):
        """
        Name of axis used to apply force.
        """

        # Open loop force may be used with multiple axes so this property returns the default axis.
        return "voicecoil1"

    def set_force_calibration_table(self, table):
        """
        Set interpolation table for force calibration data.
        :param table: Dict where key is axis name and value is of type {"force": [], "current": []}}.
        """

        # Dictionary {axis_name: {force: [], current: []}}.
        for axis_name, data in table.items():
            self._force_functions_from_calibration_table(axis_name, data)

    def _force_functions_from_calibration_table(self, axis_name, data):
        """
        Generate force conversion function for the given axis from calibration table data
        :param axis_name: Axis to generate functions for
        :param data: Calibration data as dict {"force": [], "current": []}}.
        """

        # Read measurement data from calibration data stored in server configuration file
        try:
            # Force calibration property exists, but has no content -> Handle same way as empty dict would be handled
            if data is None:
                raise AttributeError

            current_ma = data['current']
            force_g = data['force']

            # Create piecewise linear interpolation for conversions and add functions dictionary
            self._current_to_grams[axis_name] = interpolate.interp1d(current_ma, force_g, fill_value='extrapolate')
            self._grams_to_current[axis_name] = interpolate.interp1d(force_g, current_ma, fill_value='extrapolate')

            log.debug("Updated force calibration functions.")
        except (AttributeError, KeyError):
            # No calibration data property defined at all, or no calibration data for given axis is available.
            # Catch exceptions to allow Robot node to initialize normally without force support.
            pass

    def force_usage_allowed(self, axis_name):
        """
        Check if force can be used for given axis.
        :param axis_name: Name of axis.
        :return: True or False.
        """

        if axis_name in self._current_to_grams and axis_name in self._grams_to_current:
            return True

        return False

    def set_force_limit(self, axis_name, grams):
        """
        Set axis force limit.
        :param axis_name: The axis that force limit should be set for.
        :param grams: Force limit to apply in grams.
        :return:
        """

        if axis_name not in self._grams_to_current:
            raise Exception("No force calibration data for axis '{}'. Please calibrate force.".format(axis_name))

        grams_in_milliamps = int(round(float(self._grams_to_current[axis_name](grams))))

        self.set_torque_limit(axis_name, grams_in_milliamps)

    def read_torque_limit(self, axis_name):
        """
        Read current axis torque limit.
        :param axis_name: The axis that torque limit should be read for.
        :return: Torque limit in milliamperes.
        """

        current_cont_limit = self.driver.read_axis_parameter(axis_name, SMRegs.SMP_TORQUELIMIT_CONT)

        return current_cont_limit

    def set_torque_limit(self, axis_name, torque_limit):
        """
        Set axis torque limit.
        :param axis_name: The axis that torque limit should be set for.
        :param torque_limit: Torque limit in milliamperes.
        """
        if torque_limit > self.max_current:
            log.warning('Force exceeds maximum torque limit for motor. Clipping force to {} g.'.format(
                int(self._current_to_grams[axis_name](self.max_current))))
            torque_limit = self.max_current

        self.driver.set_axis_parameter(axis_name, SMRegs.SMP_TORQUELIMIT_PEAK, torque_limit)
        self.driver.set_axis_parameter(axis_name, SMRegs.SMP_TORQUELIMIT_CONT, torque_limit)

    def tap_with_force(self, force, duration, target_stroke, axis_name='voicecoil1'):
        """
        Tap primitive movement with force limit in grams. Used in force press gesture.

        :param force: Force limit in grams, will be converted to axis torque limit based on calibration.
        :param duration: How many seconds the tap is held down.
        :param target_stroke: How many millimeters the voice coil moves from the home position.
        :param axis_name: Name of the axis. One of 'voicecoil1', 'voicecoil2' or 'both'.
        """

        if axis_name == "voicecoil1":
            axis_force_grams = {"voicecoil1": force}

            start_joint_positions = {'voicecoil1': 0}
            target_joint_positions = {'voicecoil1': target_stroke}
        elif axis_name == "voicecoil2":
            axis_force_grams = {"voicecoil2": force}

            start_joint_positions = {'voicecoil2': 0}
            target_joint_positions = {'voicecoil2': target_stroke}
        elif axis_name == "both":
            axis_force_grams = {"voicecoil1": force, "voicecoil2": force}

            start_joint_positions = {'voicecoil1': 0, 'voicecoil2': 0}
            target_joint_positions = {'voicecoil1': target_stroke, 'voicecoil2': target_stroke}
        else:
            raise Exception("Invalid axis_name '{}'. Must be one of 'voicecoil1', 'voicecoil2' or 'both'.".format(axis_name))

        with VoicecoilForce(self, axis_force_grams):
            # TODO: Make configurable.
            speed = self.robot.robot_velocity
            acceleration = 10

            # Move voicecoil in joint space. This is easiest way to make it work with robots that have
            # different z-voicecoil kinematics.
            self.robot.move_joint_position(start_joint_positions, speed=speed, acceleration=acceleration)
            self.robot.move_joint_position(target_joint_positions, speed=speed, acceleration=acceleration)

            time.sleep(duration)

            self.robot.move_joint_position(start_joint_positions, speed=speed, acceleration=acceleration)

    def tap_with_current(self, current, duration, target_stroke, axis_name='voicecoil1'):
        """
        Tap primitive movement with axis torque limit in milliamperes. Used for calibrating force gram values for axis.

        :param current: Torque limit in milliamperes.
        :param duration: How many seconds the tap is held down.
        :param target_stroke: How many millimeters the voice coil moves from the home position.
        :param axis_name: Name of the axis.
        """
        previous_torque_limit = self.read_torque_limit(axis_name)

        try:
            self.set_torque_limit(axis_name, current)

            # TODO: Make configurable.
            speed = self.robot.robot_velocity
            acceleration = 10

            # Move voicecoil in joint space. This is easiest way to make it work with robots that have
            # different z-voicecoil kinematics.
            self.robot.move_joint_position({axis_name: 0}, speed=speed, acceleration=acceleration)
            self.robot.move_joint_position({axis_name: target_stroke}, speed=speed, acceleration=acceleration)

            time.sleep(duration)

            self.robot.move_joint_position({axis_name: 0}, speed=speed, acceleration=acceleration)
        finally:
            # Set axis torque limit back to original value
            self.set_torque_limit(axis_name, previous_torque_limit)

    def press(self, context, x: float, y: float, force: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                  duration: float = 0, press_depth: float = None, tool_name=None):
        """
        Performs a press gesture in given context.

        :param context: Context where gesture is performed.
        :param x: Target x coordinate.
        :param y: Target y coordinate.
        :param force: Force in grams, to be activated after moving to lower position.
        :param z: Target z coordinate when hovering before and after gesture.
        :param tilt: Tilt angle.
        :param azimuth: Azimuth angle.
        :param duration: How long to keep specified force active in seconds (default: 0s).
        :param press_depth: Distance from z=0 surface during press, negative values being below/through surface.
        :param tool_name: Name of tool for perform gesture with. Can be "tool1", "tool2" or "both".
        :return: "ok" / error
        """
        if tool_name == "tool1":
            kinematic_name = "tool1"
            axis_name = "voicecoil1"
        elif tool_name == "tool2":
            kinematic_name = "tool2"
            axis_name = "voicecoil2"
        elif tool_name == "both":
            kinematic_name = "mid"
            axis_name = "both"
        else:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        if press_depth is None:
            press_depth = self.press_depth

        robot = self.robot

        toolframe = robot.tool_frame(kinematic_name)

        prg = robot.program
        prg.begin(ctx=context, toolframe=toolframe, kinematic_name=kinematic_name)
        prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

        # 1. Move over target position at base distance
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)))

        # 2. Move down to press height, fixed distance because voice coil force depends on stroke length
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, self.press_distance, 0, tilt, -azimuth)))

        # 3. Run program to move over DUT
        prg.run()

        # 4. Start new set of commands for tap
        prg.clear()
        prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

        # 5. Perform tap primitive with given parameters and stroke of 1.0 mm through the surface to fix the force applied
        # Press depth inside the surface is negative so to add it to the stroke distance we need to reverse it
        target_stroke = self.press_distance - press_depth
        self.tap_with_force(force=force, duration=duration, target_stroke=target_stroke,
                       axis_name=axis_name)

        # 6. Clear tap from program and reset speed and acceleration values
        prg.clear()
        prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

        # 7. Move back over target position at base distance
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)))
        prg.run()

        # Force feedback not supported.
        return {}

    def drag_force(self, context, x1: float, y1: float, x2: float, y2: float, force: float, z: float = None,
                       tilt1: float = 0, tilt2: float = 0, azimuth1: float = 0, azimuth2: float = 0,
                       tool_name=None):
        """
        Performs a drag with force with given parameters.

        :param context: Context where gesture is performed.
        :param x1: Start x coordinate.
        :param y1: Start y coordinate .
        :param x2: End x coordinate.
        :param y2: End y coordinate.
        :param force: Grams of force to apply when running on target surface.
        :param z: Target z coordinate when hovering before and after gesture.
        :param tilt1: Start tilt angle.
        :param tilt2: End tilt angle.
        :param azimuth1: Start azimuth angle.
        :param azimuth2: End azimuth angle.
        :param tool_name: Name of tool for perform gesture with. Can be "tool1", "tool2" or "both".
        """

        robot = self.robot

        target_stroke = self.drag_stroke

        if tool_name is None:
            tool_name = "tool1"

        if tool_name == "tool1":
            axis_force_grams = {"voicecoil1": force}
            kinematic_name = "tool1"

            start_joint_positions = {'voicecoil1': 0}
            target_joint_positions = {'voicecoil1': target_stroke}
        elif tool_name == "tool2":
            axis_force_grams = {"voicecoil2": force}
            kinematic_name = "tool2"

            start_joint_positions = {'voicecoil2': 0}
            target_joint_positions = {'voicecoil2': target_stroke}
        elif tool_name == "both":
            axis_force_grams = {"voicecoil1": force, "voicecoil2": force}
            kinematic_name = "mid"

            start_joint_positions = {'voicecoil1': 0, 'voicecoil2': 0}
            target_joint_positions = {'voicecoil1': target_stroke, 'voicecoil2': target_stroke}
        else:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        # Reset voiceceoils to zero.
        self.robot.move_joint_position(start_joint_positions, speed=robot.robot_velocity, acceleration=robot.robot_acceleration)

        drag_start_up = robotmath.xyz_euler_to_frame(x1, y1, z, 0, tilt1, -azimuth1)
        drag_start_distance = robotmath.xyz_euler_to_frame(x1, y1, self.drag_distance, 0, tilt1, -azimuth1)
        drag_start_clearance = robotmath.xyz_euler_to_frame(x1, y1, self.drag_clearance, 0, tilt1, -azimuth1)
        drag_end_up = robotmath.xyz_euler_to_frame(x2, y2, z, 0, tilt2, -azimuth2)
        drag_end_distance = robotmath.xyz_euler_to_frame(x2, y2, self.drag_distance, 0, tilt2, -azimuth2)
        drag_end_clearance = robotmath.xyz_euler_to_frame(x2, y2, self.drag_clearance, 0, tilt2, -azimuth2)

        prg = robot.program

        tool_frame = robot.tool_frame(kinematic_name)

        # Move down to drag start position.
        prg.begin(ctx=context, toolframe=tool_frame, kinematic_name=kinematic_name)
        prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

        prg.move(prg.line(drag_start_up, drag_start_distance))
        prg.run()

        # Move voicecoils to target stroke and perform drag movement against DUT with given force.
        with VoicecoilForce(self, axis_force_grams):
            self.robot.move_joint_position(target_joint_positions, speed=robot.robot_velocity, acceleration=robot.robot_acceleration)

            prg.begin(ctx=context, toolframe=tool_frame, kinematic_name=kinematic_name)
            prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

            prg.move(prg.line(drag_start_clearance, drag_end_clearance))
            prg.run()

        # Reset voiceceoils to zero.
        self.robot.move_joint_position(start_joint_positions, speed=robot.robot_velocity, acceleration=robot.robot_acceleration)

        # Move up.
        prg.begin(ctx=context, toolframe=tool_frame, kinematic_name=kinematic_name)
        prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

        prg.move(prg.line(drag_end_distance, drag_end_up))
        prg.run()

        # Force feedback not supported.
        return {}


class VoicecoilForce:
    """
    Enables usage in with block.
    Example (executes drag gesture with force applied with primary finger):
            with VoicecoilForce(self.robot, {"voicecoil1": force}):
                super().drag(x1, y1, x2, y2, None, tilt1, tilt2, azimuth1, azimuth2, clearance)
    TODO: Implement using AxisParameterContext.

    """
    def __init__(self, force_driver, axis_force_grams):
        """

        :param robot: Robot Node.
        :param axis_force_grams: Force to apply in grams as dictionary e.g. {"axis1": force1, "axis2": force2}.
        """
        self._force_driver = force_driver
        self._axis_force_grams = axis_force_grams
        self._original_torque = None

    def __enter__(self):
        self._original_torque = {axis_name: self._force_driver.read_torque_limit(axis_name)
                                 for axis_name in self._axis_force_grams.keys()}

        for axis_name, force_grams in self._axis_force_grams.items():
            self._force_driver.set_force_limit(axis_name, force_grams)

    def __exit__(self, *args, **kwargs):
        for axis_name, torque in self._original_torque.items():
            self._force_driver.set_torque_limit(axis_name, torque)