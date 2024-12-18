from tntserver.Nodes.Node import *
from tntserver.drivers.robots import golden_program
from tntserver.drivers.robots.golden_program import AxisPrimitive, KeyFrameAxisPrimitive, ModifyPrimitive, calculate_track_duration, primitive_axis_movement
import tntserver.Nodes.TnT.Gestures
import math

"""
Azimuth Synchro Voicecoil Fingers
Gestures
"""

# constants

# for one finger movements
PRIMARY_FINGER_AXIS_NAME = "voicecoil1"

# for voicecoil movements (like tap)
VOICECOIL_SPEED = 700
VOICECOIL_ACCELERATION = 8000

SMP_TORQUELIMIT_CONT = 410
SMP_TORQUELIMIT_PEAK = 411
# How many milliamperes the peak current is allowed to go higher than the continuous current
PEAK_OVER_CONT = 0

# Limit the distance between azimuth1 and azimuth2 in gestures.
ANGLE_RANGE_LIMIT = 179


class VoicecoilMaxContCurrent:
    """
    State class to temporarily set maximum continuous current of specific axes to some value.
    TODO: Implement using AxisParameterContext.
    """
    def __init__(self, robot, max_cont_current, axis_names):
        self._robot = robot
        self._max_cont_current = max_cont_current
        self._axis_names = axis_names
        self._original_max_cont_currents = {}

    def __enter__(self):
        for axis_name in self._axis_names:
            self._original_max_cont_currents[axis_name] = self._robot.read_torque_limit(axis_name)

            self._robot.set_torque_limit(axis_name, self._max_cont_current)

    def __exit__(self, *args, **kwargs):
        for axis_name in self._axis_names:
            self._robot.set_torque_limit(axis_name, self._original_max_cont_currents[axis_name])


class VoicecoilGesture(Object):
    """
    Enables primary finger down with voicecoil with easy-to-use with block.
    Mandatory parameters are the calling gesture class and x, y start position for the following gesture.
    """
    def __init__(self, gestures, x, y, z, finger_depth=None, tilt=None, azimuth=None, separation=None,
                 tool_name="tool1", kinematic_name=None):
        """

        :param gestures: Gestures class instance.
        :param x: Gesture start x position.
        :param y: Gesture start y position.
        :param z: Gesture start z position.
        :param finger_depth: (optional) How much to bring primary finger down for the gesture. .
                             Note: hardware setup limits this value to somewhere 5-8mm with synchro robot.
        :param tilt: (optional) Gesture start tilt.
        :param azimuth: (optional) Gesture start azimuth.
        :param separation: Separation to use during gesture. If None, then default separation is used.
        :param tool_name: Name of tool to perform gesture with. This must be one of 'tool1', 'tool2', or 'both'.
        :param kinematic_name: Name of kinematic to perform gesture with. This must be one of 'tool1', 'tool2', 'mid', 'synchro' or None.
                               In case of None value, the kinematic is selected depending on the value of tool_name.
        """
        super().__init__()
        self._gestures = gestures
        self._start_pos = x, y, z
        self._start_tilt = tilt
        self._start_azimuth = azimuth
        self.frame = robotmath.identity_frame()
        self.object_parent = gestures
        if finger_depth is not None:
            self._finger_depth = finger_depth
        else:
            self._finger_depth = self._gestures.robot.get_finger_press_depth(PRIMARY_FINGER_AXIS_NAME)
        self._multifinger = gestures.robot.has_multifinger()

        if separation is None:
            separation = self._gestures.robot.default_separation
        self._separation = separation
        self._tool_name = tool_name
        self._kinematic_name = kinematic_name

    def __enter__(self):
        robot = self._gestures.robot
        prg = robot.program
        finger_depth = self._finger_depth
        x, y, z = self._start_pos
        tilt = self._start_tilt
        azimuth = self._start_azimuth

        kinematic_name = self._kinematic_name

        # Variable kinematic_name determines which part of the robot the kinematics is applied to. For example
        # value 'tool1' controls the left finger while 'mid' controls the mid point between the two fingers.
        # Variable tool_name determines which tool is used to apply gesture on target. For example with value 'tool1'
        # the voice coil on the left finger performs a tap. With value 'both' the voicecoils on both fingers
        # perform a tap simultaneously. If kinematic_name is not given, it is determined according to value of
        # tool_name as seen below.
        if kinematic_name is None:
            if self._tool_name == "tool1":
                kinematic_name = "tool1"
            elif self._tool_name == "tool2":
                kinematic_name = "tool2"
            elif self._tool_name == "both":
                kinematic_name = "mid"
            else:
                assert False
        else:
            if kinematic_name not in ["tool1", "tool2", "mid", "synchro"]:
                raise Exception("Parameter 'kinematic_name' must be one of 'tool1', 'tool2', 'mid' or 'synchro'.")

        toolframe = robot.tool_frame(kinematic_name)

        if not self._multifinger:
            # Set Gestures-node frame temporarily so that DUT appears to be
            # offset finger_depth distance along the DUT surface normal direction.
            # Assumes that gestures are executed in Gestures-context.
            # This is done because kinematics does not account for voice coil offset that is applied for the duration
            # of voice coil gesture.
            self._gestures.frame = robotmath.xyz_to_frame(0, 0, finger_depth)

            prg.begin(ctx=self, toolframe=toolframe, kinematic_name=kinematic_name)
            prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

            # 1. move to gesture start location, at base distance
            # 2. move separation to robot.default_separation() if separation movement is allowed.
            # 3. move primary finger to FINGER_PRESS_DEPTH mm. if finger movement is allowed.

            #TODO: remove this thingy because tilt and azimuth should be explicitly specified
            # optional tilt, azimuth
            if tilt is None or azimuth is None:
                # robot doesn't define effective pose base frame so we just guess it is robot.object_parent
                current_pose = robotmath.translate(robot.effective_pose(), robot.object_parent, self)
                cx, cy, cz, ca, cb, cc = robotmath.frame_to_xyz_euler(current_pose)
                tilt = cb
                azimuth = -cc

            # safe start position
            p1 = prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth))

            # separation
            p2 = primitive_axis_movement("separation", target=self._separation)

            # voicecoil to press depth
            if self._tool_name == "tool1":
                p3 = primitive_axis_movement("voicecoil1", finger_depth, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)

                prg.move([p1, p2, p3])
            elif self._tool_name == "tool2":
                p3 = primitive_axis_movement("voicecoil2", finger_depth, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)

                prg.move([p1, p2, p3])
            elif self._tool_name == "both":
                p3 = primitive_axis_movement("voicecoil1", finger_depth, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)
                p4 = primitive_axis_movement("voicecoil2", finger_depth, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)

                prg.move([p1, p2, p3, p4])
            else:
                assert False

            prg.run()

        # preset program for the gesture:
        prg.begin(ctx=self, toolframe=toolframe, kinematic_name=kinematic_name)
        prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

    def __exit__(self, *args, **kwargs):
        robot = self._gestures.robot
        prg = robot.program
        finger_depth = self._finger_depth

        if not self._multifinger:
            toolframe = robot.tool_frame(robot.default_kinematic_name)
            kinematic_name = robot.default_kinematic_name

            pose = robotmath.translate(robot.effective_pose(), robot.object_parent, self)
            pose.A[2, 3] -= finger_depth

            prg.begin(ctx=self, toolframe=toolframe, kinematic_name=kinematic_name)
            prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

            # Move voice coil to default position (zero).
            prg.clear()
            prg.set_speed(robot.robot_velocity, robot.robot_acceleration)

            if self._tool_name == "tool1":
                prg.move(primitive_axis_movement("voicecoil1", 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
            elif self._tool_name == "tool2":
                prg.move(primitive_axis_movement("voicecoil2", 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
            elif self._tool_name == "both":
                prg.move([primitive_axis_movement("voicecoil1", 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION),
                          primitive_axis_movement("voicecoil2", 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)])
            else:
                assert False

            prg.run()

            # Move robot to position that compensates the voice coil movement.
            prg.clear()
            prg.set_speed(robot.robot_velocity, robot.robot_acceleration)
            prg.move(prg.point(pose))
            prg.run()

            # Set separation to default value in case the gesture changed it.
            prg.clear()
            prg.set_speed(robot.robot_velocity, robot.robot_acceleration)
            prg.move(primitive_axis_movement("separation", robot.default_separation))  # separation, primary finger up
            prg.run()

        # Reset gesture node frame to identity (assuming it was identity before voice coil gesture).
        self._gestures.frame = robotmath.identity_frame()


def primitive_tap_at_time(v, axis_name, depth, speed, acceleration):
    p = KeyFrameAxisPrimitive(axis_name, key_times=[v])
    p.plan_tap(depth, speed, acceleration)
    return p


def primitive_tap_at_position(v, axis_name, depth):
    p = KeyFrameAxisPrimitive(axis_name, key_positions=[v])
    p.plan_tap(depth, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)
    return p


def primitive_axis_movement(axis_name, target, speed=None, acceleration=None):
    p = AxisPrimitive(axis_name)
    p.target_value = target
    p.speed_override = speed
    p.acceleration_override = acceleration
    return p


def primitive_separation(v):
    return primitive_axis_movement("separation", v)


class Gestures(tntserver.Nodes.TnT.Gestures.Gestures):
    """
    Gestures for Synchro robot.
    """

    def __init__(self, name):
        super().__init__(name)

    def _init(self, **kwargs):
        super()._init(**kwargs)

    @json_out
    def put_pinch(self, x: float, y: float, d1: float, d2: float, azimuth: float, z: float=None, clearance: float=0):
        """
        Performs a pinch gesture in DUT context.

        :param x: Target x coordinate on DUT. Target is the middle position between fingers.
        :param y: Target y coordinate on DUT. Target is the middle position between fingers.
        :param d1: Distance between fingers at the beginning.
        :param d2: Distance between fingers at the end.
        :param azimuth: Azimuth angle during the pinch.
        :param z: Overrides base distance.
        :param clearance: Distance from DUT surface during gesture.
        :return: "ok" / error
        """
        if self.robot.has_multifinger():
            raise Exception("Pinch gesture can't be performed with multifinger")

        dut = self.parent

        assert dut.base_distance is not None, "DUT base distance not set"

        z = dut.base_distance if z is None else z


        # Use tool frame of "tool1" as if it was attached to kinematic "mid".
        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame("tool1"), kinematic_name="mid")
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        # 1. Move over the start point
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, 0, -azimuth)))

        # 2. Move start separation
        prg.move(primitive_separation(d1))

        # 3. Move to start point
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, clearance, 0, 0, -azimuth)))

        # 4. Move pinch gesture (to the target separation)
        prg.move(primitive_separation(d2))

        # 5. Move up
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, 0, -azimuth)))

        # run the sequence
        prg.run()

        return "ok"

    @json_out
    def put_drumroll(self, x: float, y: float, azimuth: float, separation: float,
                     tap_count: int, tap_duration: float, clearance: float=0):
        """
        Taps tap_count times with two fingers, one finger at a time, starting with finger 1 (left finger).
        Tapping is done with given azimuth angle and finger separation.
        Tapping is done tap_duration seconds, to which period the tap_count number of taps is layed out evenly.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param azimuth: Azimuth angle during the gesture.
        :param separation: Separation between the fingers during the gesture, millimeters.
        :param tap_count: Number of taps to perform.
        :param tap_duration: Duration of all taps together, seconds.
        :param clearance: Distance from DUT surface during gesture.
        :return: "ok" / error
        """

        if self.robot.has_multifinger():
            raise Exception("Drumroll gesture can't be performed with multifinger")

        # Specification requires 12 taps per second.
        # For 5 mm tap depth this translates to 250 mm/s speed and 12500 mm/s^2 acceleration at minimum.
        # Use slightly higher values to account for some variance.
        # This movement also requires higher than normal continuous current limit for voice coils.
        VOICECOIL_SPEED_DRUMROLL = 270
        VOICECOIL_ACCELERATION_DRUMROLL = 13000

        # Calculate press depth for some of the prg.move operations. As it cannot be certain which kinematic is used
        # get the finger depth from the tool that has smaller depth.
        vc1_press_depth = self.robot.get_finger_press_depth("voicecoil1")
        vc2_press_depth = self.robot.get_finger_press_depth("voicecoil2")
        press_depth = min(vc1_press_depth, vc2_press_depth)

        # Create one dummy voicecoil tap primitive to check the duration of a single tap before any movements.
        p_tap = primitive_tap_at_time(0, "voicecoil1", vc1_press_depth,
                                      VOICECOIL_SPEED_DRUMROLL, VOICECOIL_ACCELERATION_DRUMROLL)
        if p_tap.duration > tap_duration / tap_count:
            raise Exception("Too many taps in given tap duration: 12 taps per second is the maximum. Increase duration or decrease tap count.")

        # Use tool frame of "tool1" as if it was attached to kinematic "mid".
        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame("tool1"), kinematic_name="mid")
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        # 1. move over target position, target angle
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, press_depth + clearance, 0, 0, -azimuth)))

        # 2. open target separation, zero voicecoils
        prg.move(primitive_separation(separation))
        prg.move(primitive_axis_movement("voicecoil1", 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
        prg.move(primitive_axis_movement("voicecoil2", 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))

        # 3. run program so far
        prg.run()

        # 4. start new set of commands, two seconds pause with drumrolling
        prg.clear()
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        primitives = [
            prg.pause(tap_duration)
        ]
        for i in range(int(tap_count)):
            actuator_name = ["voicecoil1", "voicecoil2"][i & 1]
            tap_time = i / tap_count * tap_duration
            p_tap = primitive_tap_at_time(tap_time, actuator_name, self.robot.get_finger_press_depth(actuator_name),
                                          VOICECOIL_SPEED_DRUMROLL, VOICECOIL_ACCELERATION_DRUMROLL)

            primitives.append(p_tap)

        prg.move(primitives)

        # 5. move up after drumming, zero voicecoils
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, press_depth, 0, 0, -azimuth)))
        prg.move(primitive_axis_movement("voicecoil1", 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
        prg.move(primitive_axis_movement("voicecoil2", 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))

        # Run program with voicecoil current limits set higher to make sure that the required acceleration is achieved.
        with VoicecoilMaxContCurrent(self.robot, self.robot.max_voicecoil_current, ["voicecoil1", "voicecoil2"]):
            prg.run()

        return "ok"

    @json_out
    def put_compass(self, x: float, y: float, azimuth1: float, azimuth2: float, separation: float,
                    z: float=None, clearance: float=0, kinematic_name="tool1"):
        """
        Compass movement.
        Primary finger (the left finger) stays at x, y position while the other finger rotates around it.
        Rotation starts at azimuth angle azimuth1 and ends at azimuth angle azimuth2.
        Rotation will be done to shortest route direction.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param azimuth1: Start azimuth angle.
        :param azimuth2: End azimuth angle.
        :param separation: Distance between fingers during the gesture
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param clearance: Distance from DUT surface during gesture.
        :param kinematic_name: Name of kinematic to perform the gesture with
        :return: "ok" / error
        """

        if self.robot.has_multifinger():
            raise Exception("Compass gesture can't be performed with multifinger")

        if abs(azimuth2 - azimuth1) > ANGLE_RANGE_LIMIT:
            raise Exception("Compass gesture angle range cannot exceed {} degrees".format(ANGLE_RANGE_LIMIT))

        dut = self.parent

        assert dut.base_distance is not None, "DUT base distance not set"

        z = dut.base_distance if z is None else z

        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(kinematic_name), kinematic_name=kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        primitives = []
        primitives.append(prg.line(robotmath.xyz_euler_to_frame(x, y, clearance, 0, 0, -azimuth1),
                                   robotmath.xyz_euler_to_frame(x, y, clearance, 0, 0, -azimuth2)))

        # 1. move over starting position, set separation, move down to touch position
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, 0, -azimuth1)))
        prg.move(primitive_separation(separation))
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, clearance, 0, 0, -azimuth1)))

        # 2. do the arc movement
        prg.move(primitives)

        # 3. move up
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, 0, -azimuth2)))
        prg.run()

        return "ok"

    @json_out
    def put_compass_tap(self, x: float, y: float, azimuth1: float, azimuth2: float, separation: float,
                        tap_azimuth_step: float, z: float=None, tap_with_stationary_finger: bool=False,
                        clearance: float=0):
        """
        Compass movement with tapping.
        Primary finger (the left finger) stays at x, y position while the other finger rotates around it.
        Rotation starts at azimuth angle azimuth1 and ends at azimuth angle azimuth2.
        Rotation will be done to shortest route direction.
        Tapping is done with selected finger. (moving finger by default)

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param azimuth1: Start azimuth angle.
        :param azimuth2: End azimuth angle.
        :param separation: Distance between fingers during the gesture.
        :param tap_azimuth_step: Angle in degrees between taps.
        :param z: Target z coordinate on DUT when hovering before and after gesture and in-between taps (default: DUT's base_distance).
        :param tap_with_stationary_finger: Stationary or moving finger does the tapping.
        :param clearance: Distance from DUT surface during gesture.
        :return: "ok" / error
        """

        if self.robot.has_multifinger():
            raise Exception("Compass tap gesture can't be performed with multifinger")

        if abs(azimuth2 - azimuth1) > ANGLE_RANGE_LIMIT:
            raise Exception("Compass tap gesture angle range cannot exceed {} degrees".format(ANGLE_RANGE_LIMIT))

        # for tapping
        if tap_with_stationary_finger:
            touching_actuator_name = "voicecoil2"
            tapping_actuator_name = "voicecoil1"
        else:
            touching_actuator_name = "voicecoil1"
            tapping_actuator_name = "voicecoil2"

        # rotate around this tool
        kinematic_name = "tool1"

        dut = self.parent

        assert dut.base_distance is not None, "DUT base distance not set"

        z = dut.base_distance if z is None else z

        touching_voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth(touching_actuator_name))
        tapping_voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth(tapping_actuator_name))

        # z-position before voice coil tap (when voice coil is at zero).
        pre_voicecoil_z = tapping_voicecoil_distance + clearance

        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(kinematic_name), kinematic_name=kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        primitives = [prg.line(robotmath.xyz_euler_to_frame(x, y, pre_voicecoil_z, 0, 0, -azimuth1),
                               robotmath.xyz_euler_to_frame(x, y, pre_voicecoil_z, 0, 0, -azimuth2))]

        # 1. move over starting position
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, 0, -azimuth1)))

        # 2. move to target separation
        prg.move(primitive_separation(separation))

        # 3. move to touch surface
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, pre_voicecoil_z, 0, 0, -azimuth1)))
        prg.move(primitive_axis_movement(touching_actuator_name, touching_voicecoil_distance))
        prg.run()

        # 4. do the arc movement with tapping
        prg.clear()
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move(primitives)
        length = prg.length()

        dpa = length / np.abs(azimuth2 - azimuth1)
        num_taps = int(length / dpa / tap_azimuth_step)

        for i in range(num_taps):
            p_tap = primitive_tap_at_position(i * dpa * tap_azimuth_step, tapping_actuator_name,
                                              tapping_voicecoil_distance)
            primitives.append(p_tap)

        prg.clear()
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move(primitives)

        # move up at the end
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, 0, -azimuth2)))
        prg.move(primitive_axis_movement(touching_actuator_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
        prg.move(primitive_axis_movement(tapping_actuator_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
        prg.run()

        return "ok"

    @json_out
    def put_touch_and_tap(self, touch_x: float, touch_y: float, tap_x: float, tap_y: float, z: float=None,
                          number_of_taps=1, tap_predelay=0, tap_duration=0, tap_interval=0, clearance: float=0,
                          touch_duration=None):
        """
        Performs a gesture where primary finger is touching a location and secondary finger is doing a tapping gesture
        at another location.
        You can define the x, y coordinates for both fingers separately.

        :param touch_x: Touching finger x, millimeters.
        :param touch_y: Touching finger y, millimeters.
        :param tap_x: Tapping finger x, millimeters.
        :param tap_y: Tapping finger y, millimeters.
        :param z: Target z coordinate on DUT when hovering before and after gesture and in-between taps (default: DUT's base_distance).
        :param number_of_taps: Number of taps to perform. 1 for single tap, 2 for double tap, ...
        :param tap_predelay: Delay between primary finger touch down and secondary finger first touch down.
        :param tap_duration: Time to wait while the tap finger is down in seconds.
        :param tap_interval: Time interval between the taps, seconds. Only affects number_of_taps >= 2
        :param clearance: Distance from DUT surface during movement.
        :param touch_duration: Duration of primary finger touch in seconds. If None, the finger will touch during the secondary finger tapping motion.
        :return: "ok" / error
        """

        if self.robot.has_multifinger():
            raise Exception("Touch and tap gesture can't be performed with multifinger.")

        # Finger 1 touches, Finger 2 taps
        tapping_actuator_name = "voicecoil2"
        touching_actuator_name = "voicecoil1"
        kinematic_name = "tool1"

        azimuth = np.degrees(-np.arctan2(tap_y - touch_y, tap_x - touch_x))
        separation = np.linalg.norm((tap_x - touch_x, tap_y - touch_y))

        dut = self.parent

        assert dut.base_distance is not None, "DUT base distance not set"

        z = dut.base_distance if z is None else z

        touching_voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth(touching_actuator_name))
        tapping_voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth(tapping_actuator_name))

        # z-position before voice coil tap (when voice coil is at zero).
        pre_voicecoil_z = tapping_voicecoil_distance + clearance

        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(kinematic_name), kinematic_name=kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        # 1. move over starting position
        prg.move(prg.point(robotmath.xyz_euler_to_frame(touch_x, touch_y, z, 0, 0, -azimuth)))

        # 2. move to target separation
        prg.move(primitive_separation(separation))

        # 3. move down to Z height where to start gesture utilizing voice coil
        prg.move(prg.point(robotmath.xyz_euler_to_frame(touch_x, touch_y, pre_voicecoil_z, 0, 0, -azimuth)))

        # 5. single, double or x number tap

        # Primary finger motions.
        p_touch_down = primitive_axis_movement(touching_actuator_name, touching_voicecoil_distance, VOICECOIL_SPEED,
                                               VOICECOIL_ACCELERATION)
        p_touch_up = primitive_axis_movement(touching_actuator_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)

        # tap parts: finger down + duration + finger up
        p_tap_1 = primitive_axis_movement(tapping_actuator_name, tapping_voicecoil_distance, VOICECOIL_SPEED,
                                          VOICECOIL_ACCELERATION)
        p_tap_2 = prg.pause(tap_duration)
        p_tap_3 = primitive_axis_movement(tapping_actuator_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)
        p_pause = prg.pause(tap_interval)

        if touch_duration is None:
            # In this case, move primary finger down and tap with secondary finger after predelay.

            # tap ( + interval + tap + interval + tap...), after last tap there is no interval so that is removed
            taps = (number_of_taps * [p_tap_1, p_tap_2, p_tap_3, p_pause])[:-1]

            tap_primitives = [p_touch_down, prg.pause(tap_predelay)] + taps
        else:
            # In this case, tap with primary finger and tap with secondary finger with delay. The tapping of the
            # two fingers may overlap in time.

            # Estimate the duration of VC moving from 0 to voicecoil_distance.
            # Currently this can't be easily obtained from axis primitive.
            vc_movement_duration = calculate_track_duration(VOICECOIL_SPEED, VOICECOIL_ACCELERATION,
                                                            tapping_voicecoil_distance)

            # Duration of secondary finger taps.
            taps_duration = (vc_movement_duration * 2 + tap_duration) * number_of_taps + tap_interval * (number_of_taps - 1)

            # First plan a motion where primary finger taps and then waits for the duration of second finger movement.
            # The waiting is required because this motion is for the primary finger but must span the duration of
            # the entire motion. Secondary finger motion is glued over this motion below.
            tap_primitives = [p_touch_down, prg.pause(touch_duration), p_touch_up,
                              prg.pause(max(0, tap_predelay + taps_duration - touch_duration))]

            # Then plan motion for secondary finger taps which are inserted at proper times over the previously planned motion.
            # First tap time is chosen here so that if tap_predelay is zero, then both fingers will touch target simultaneously.
            tap_time = tap_predelay

            for i in range(number_of_taps):
                p = KeyFrameAxisPrimitive(tapping_actuator_name, key_times=[tap_time])
                p.plan_tap(tapping_voicecoil_distance, VOICECOIL_SPEED, VOICECOIL_ACCELERATION, tap_duration)

                tap_time += p.duration + tap_interval

                tap_primitives.append(p)

        prg.move(tap_primitives)

        # move up at the end
        prg.move(prg.point(robotmath.xyz_euler_to_frame(touch_x, touch_y, z, 0, 0, -azimuth)))
        prg.move(p_touch_up)
        prg.run()

        return "ok"

    @json_out
    def put_line_tap(self, x1: float, y1: float, x2: float, y2: float, tap_distances: list,
                     separation: float=None, azimuth: float=0, z: float=None, clearance: float=0):
        """
        Moves the robot along a line between x1, y1 and x2, y2 and taps the surface with primary finger
        at given distances relative to the x1, y1 starting position.

        :param x1: Line start x, millimeters.
        :param y1: Line start y, millimeters.
        :param x2: Line end x, millimeters.
        :param y2: Line end y, millimeters.
        :param tap_distances: List of tap locations as in distances from the beginning of the line, millimeters.
        :param separation: Distance between finger centers, millimeters. If not defined then default distance is used.
        :param azimuth: Azimuth angle to use during the line.
        :param z: Target z coordinate on DUT when hovering before and after gesture and in-between taps.
                  (default: DUT's base_distance).
        :param clearance: (optional) Distance from DUT surface during movement.
        :return: "ok" / error
        """

        if self.robot.has_multifinger():
            raise Exception("Line tap gesture can't be performed with multifinger")

        tapping_actuator_name = "voicecoil1"
        kinematic_name = "tool1"

        dut = self.parent

        assert dut.base_distance is not None, "DUT base distance not set"

        z = dut.base_distance if z is None else z

        voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth(tapping_actuator_name))

        # z-position before voice coil tap (when voice coil is at zero).
        pre_voicecoil_z = voicecoil_distance + clearance

        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(kinematic_name), kinematic_name=kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        primitives = [prg.line(robotmath.xyz_euler_to_frame(x1, y1, pre_voicecoil_z, 0, 0, -azimuth),
                               robotmath.xyz_euler_to_frame(x2, y2, pre_voicecoil_z, 0, 0, -azimuth))]

        # 1. move over starting position
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x1, y1, z, 0, 0, -azimuth)))

        # 2. move to target separation
        if separation is None:
            separation = self.robot.default_separation
        prg.run()
        prg.clear()
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move(primitive_axis_movement("separation", separation, self.robot.robot_velocity, self.robot.robot_acceleration))
        prg.run()
        prg.clear()
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        # 3. move down to Z height where to start gesture utilizing voice coil
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x1, y1, pre_voicecoil_z, 0, 0, -azimuth)))
        prg.run()

        # 4. do the line movement with tapping
        prg.clear()
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move(primitives)

        for d in tap_distances:
            p_tap = primitive_tap_at_position(d, tapping_actuator_name, voicecoil_distance)
            primitives.append(p_tap)

        prg.clear()
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move(primitives)

        # move up at the end
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x2, y2, z, 0, 0, -azimuth)))
        prg.move(primitive_axis_movement(tapping_actuator_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
        prg.run()

        return "ok"

    @json_out
    def put_press(self, x: float, y: float, force: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                  duration: float = 0, press_depth: float = -1, separation=None, tool_name=None):
        """
        Performs a press gesture in DUT context.

        Force can be applied with tool1, tool2 or with both simultaneously. Note that the tool that is used
        must have a valid force calibration table in the configuration. Otherwise exception is raised.
        In case both tools are used, the given force is per tool so that force=100 & tool_name="both" will apply
        200 gF on the target.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param force: Force in grams, to be activated after moving to lower position.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param duration: How long to keep specified force active in seconds (default: 0s).
        :param press_depth: Distance from DUT surface during press, negative values being below/through DUT surface.
        Tip will be pressed to the desired depth if the force limit is not reached before that.
        If the force limit is reached before desired depth, the movement will stop there. (default: -1mm).
        :param separation: Separation during press. If None, then current separation is used.
        :param tool_name: Name of tool to perform press with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        :return: "ok" / error
        """

        log.info("put_press x={} y={} force={} z={} tilt={} azimuth={} duration={} press_depth={} separation={} tool_name={}".format(
            x, y, force, z, tilt, azimuth, duration, press_depth, separation, tool_name))

        if self.robot.has_multifinger():
            raise Exception("Press gesture can't be performed with multifinger")

        if tool_name is None:
            tool_name = "tool1"

        if tool_name not in ["tool1", "tool2", "both"]:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        dut = self.parent

        assert dut.base_distance is not None, "DUT base distance not set"

        z = dut.base_distance if z is None else z

        if tool_name == "tool1":
            kinematic_name = "tool1"
        elif tool_name == "tool2":
            kinematic_name = "tool2"
        elif tool_name == "both":
            kinematic_name = "mid"
        else:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        toolframe = self.robot.tool_frame(kinematic_name)

        # Set separation if given.
        if separation is not None:
            prg = self.robot.program
            prg.begin(ctx=self, toolframe=toolframe, kinematic_name=kinematic_name)
            prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

            # 1. Move over target position at base distance
            prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)))

            prg.move(primitive_axis_movement("separation", target=separation))
            prg.run()

        self.robot.force_driver.press(context=self, x=x, y=y, force=force, z=z, tilt=tilt,
                                      azimuth=azimuth, duration=duration, press_depth=press_depth, tool_name=tool_name)

        return "ok"

    def get_test(self, f: str, method: str, **kwargs):
        """
        Test any of the gesture functions by using HTTP GET
        :param f: name of the function to test (pinch, compass, press...)
        :param method: HTTP method (get, put, post)
        :param kwargs: arguments for the gesture
        :return: usually "ok" or error
        """
        f = getattr(self, "{}_{}".format(method, f))
        return f(**kwargs)

    #
    # Overriden base class gestures
    #

    @json_out
    def put_tap(self, x: float, y: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                clearance: float = 0, duration: float = 0, separation=None, tool_name=None, kinematic_name=None):
        """
        Performs a tap with given parameters.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: (optional) distance from DUT surface during movement
        :param duration: How long to keep finger down in seconds (default: 0s).
        :param separation: Separation during tap. If None, then default separation is used.
        :param tool_name: Name of tool to perform tap with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        :param kinematic_name: Name of kinematic to perform tap with. One of 'tool1', 'tool2', 'mid', 'synchro' or None.  None is the same as 'tool1'.
        :return: "ok" / error
        """
        log.info("put_tap x={} y={} z={} tilt={} azimuth={} clearance={} duration={} "
                 "separation={}, tool_name={} kinematic_name={}".format(x, y, z, tilt, azimuth, clearance,
                                                      duration, separation, tool_name, kinematic_name))

        # in case of multifinger, fall back to original gesture
        if self.robot.has_multifinger():
            super().put_tap(x=x, y=y, z=z, tilt=tilt, azimuth=azimuth, clearance=clearance, duration=duration)
            return "ok"

        # voicecoil tap if normal finger attached
        prg = self.robot.program

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        if tool_name is None:
            tool_name = "tool1"

        if tool_name == "tool1":
            axis_name = "voicecoil1"
        elif tool_name == "tool2":
            axis_name = "voicecoil2"
        elif tool_name == "both":
            axis_name = "voicecoil1"
            # Copy motion to VC2 in motion planning below.
        else:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth(axis_name))

        p2 = primitive_axis_movement(axis_name, voicecoil_distance, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)
        p3 = prg.pause(duration)
        p4 = primitive_axis_movement(axis_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)

        with VoicecoilGesture(self, x, y, z, finger_depth=0, tilt=tilt, azimuth=azimuth, separation=separation,
                              tool_name=tool_name, kinematic_name=kinematic_name):
            prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, voicecoil_distance + clearance, 0, tilt, -azimuth)))

            if tool_name == "both":
                # Use ModifyPrimitive to copy VC1 motion to VC2.
                def path_func(path):
                    for pos in path:
                        pos.voicecoil2 = pos.voicecoil1

                prg.move([p2, p3, p4, ModifyPrimitive(path_func)])
            else:
                prg.move([p2, p3, p4])

            prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)))
            prg.run()

        return "ok"

    @json_out
    def put_swipe(self, x1: float, y1: float, x2: float, y2: float, tilt1: float = 0, tilt2: float = 0,
                  azimuth1: float = 0, azimuth2: float = 0, clearance: float = 0, radius: float = 6,
                  separation=None, tool_name=None):
        """
        Performs a swipe with given parameters.
        Robot accelerates and decelerates along an arc of given radius before and after touching the DUT.

        :param x1: Swipe start x coordinate on DUT.
        :param x2: Swipe end x coordinate on DUT.
        :param y1: Swipe start y coordinate on DUT.
        :param y2: Swipe end y coordinate on DUT.
        :param tilt1: Swipe start tilt.
        :param tilt2: Swipe end tilt.
        :param azimuth1: Swipe start azimuth.
        :param azimuth2: Swipe end azimuth.
        :param clearance: (optional) distance from DUT surface during movement
        :param radius: Swipe radius.
        :param separation: Separation during swipe. If None, then default separation is used.
        :param tool_name: Name of tool to perform swipe with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        :return: "ok" / error
        """
        log.info("put_swipe x1={} y1={} x2={} y2={} tilt1={} tilt2={} azimuth1={} azimuth2={} clearance={} radius={} "
                 "separation={}, tool_name={}".format(x1, y1, x2, y2, tilt1, tilt2, azimuth1, azimuth2, clearance,
                                                      radius, separation, tool_name))

        if abs(azimuth2 - azimuth1) > ANGLE_RANGE_LIMIT:
            raise Exception("Swipe gesture angle range cannot exceed {} degrees".format(ANGLE_RANGE_LIMIT))

        # calculate offset to start location (swipe creates quarter circle arc in the beginning using given radius)
        v = np.array([x2 - x1, y2 - y1])  # swipe effective touch line
        v_len = np.linalg.norm(v)

        if v_len == 0:
            raise Exception("Planned swipe gesture has zero length. Please adjust swipe parameters and retry.")

        dx, dy = -radius * v / v_len

        if tool_name is None:
            tool_name = "tool1"

        with VoicecoilGesture(gestures=self, x=x1+dx, y=y1+dy, z=radius+clearance, tilt=tilt1, azimuth=azimuth1, separation=separation, tool_name=tool_name):
            swipe_start = robotmath.xyz_euler_to_frame(x1, y1, clearance, 0, tilt1, -azimuth1)
            swipe_end = robotmath.xyz_euler_to_frame(x2, y2, clearance, 0, tilt2, -azimuth2)

            prg = self.robot.program

            if tool_name == "tool1":
                toolframe = self.robot.tool_frame("tool1")
                kinematic_name = "tool1"
            elif tool_name == "tool2":
                toolframe = self.robot.tool_frame("tool2")
                kinematic_name = "tool2"
            elif tool_name == "both":
                toolframe = self.robot.tool_frame("tool1")
                kinematic_name = "mid"
            else:
                raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

            prg.begin(ctx=self, toolframe=toolframe, kinematic_name=kinematic_name)

            prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

            p1 = prg.swipe(swipe_start, swipe_end, radius)

            prg.move([p1])
            prg.run()

        return "ok"

    @json_out
    def put_fast_swipe(self, x1: float, y1: float, x2: float, y2: float, separation1: float, separation2: float,
                       speed: float, acceleration: float, tilt1: float = 0, tilt2: float = 0,
                         clearance: float = 0, radius: float = 6):
        """
        Performs a fast swipe:
        - Azimuth is first rotated so that synchro tool is parallel to the swipe direction
        - While swiping with main XY axis, separation axis is moved to gain additional speed

        The fast swipe speed can be at most 2 * min(max_xy_speed, max_separation_speed).
        The speed is also limited by the swipe length and maximum separation change.
        TODO: Need more detailed description of limitations.

        :param x1: Swipe start x coordinate on DUT.
        :param y1: Swipe start y coordinate on DUT.
        :param x2: Swipe end x coordinate on DUT.        
        :param y2: Swipe end y coordinate on DUT.
        :param separation1: Swipe start separation.
        :param separation2: Swipe end separation.
        :param speed: Fast swipe speed.
        :param acceleration: Fast swipe acceleration.
        :param tilt1: Fast swipe start tile angle.
        :param tilt2: Fast swipe end tile angle.
        :param clearance: (optional) distance from DUT surface during movement
        :param radius: Swipe radius.
        :return: "ok" / error
        """

        # Angle between positive x axis and a vector defined by 2 points
        # :return: angle in range -180 to 180
        def angle_between(x1, y1, x2, y2):
            return np.degrees(np.arctan2(y2 - y1, x2 - x1))

        azimuth1 = angle_between(x1, y1, x2, y2)

        log.info("Azimuth_1: {}".format(azimuth1))

        # To be able to use separation axis for more swipe speed:
        # - synchro needs to be rotated in the same direction as main XY stage is swiping
        # - synchro rotation needs to be such that tool1 is always leading the movement (so that it travels ahead of tool2).
        #   otherwise increasing separation during swipe would actually slow down the total tip movement on DUT surface.
        #   to ensure this, we need to add / subtract 180 degrees in some cases below.
        #
        # NOTE: this if-else block assumes that:
        # - when azimuth == 0, synchro tool is parallel with robot x axis, and tip1 is on the left
        # - when azimuth > 0, synchro is rotated counter-clockwise
        # - when azimuth < 0, synchro is rotated clockwise
        if -180 <= azimuth1 <= 90:
            azimuth1 = -(azimuth1 + 180)
        elif -90 < azimuth1 <= 0:
            azimuth1 = azimuth1 + 180
        elif 0 < azimuth1 <= 90:
            azimuth1 = -azimuth1
        elif 90 < azimuth1 <= 180:
            azimuth1 = 180 - azimuth1
        else:
            raise Exception("Azimuth should be between -180 and 180")

        log.info("put_fast_swipe x1={} y1={} x2={} y2={} tilt1={} tilt2={} azimuth1={} clearance={} radius={}".format(
            x1, y1, x2, y2, tilt1, tilt2, azimuth1, clearance, radius))

        # calculate offset to start location (swipe creates quarter circle arc in the beginning using given radius)
        v = np.array([x2 - x1, y2 - y1])  # swipe effective touch line
        dx, dy = -radius * v / np.linalg.norm(v)

        robot = self.robot

        orig_speed = robot.robot_velocity
        orig_acc = robot.robot_acceleration

        with VoicecoilGesture(gestures=self, x=x1+dx, y=y1+dy, z=radius+clearance, tilt=tilt1, azimuth=azimuth1, separation=separation1):
            swipe_start = robotmath.xyz_euler_to_frame(x1, y1, clearance, 0, tilt1, -azimuth1)
            swipe_end = robotmath.xyz_euler_to_frame(x2, y2, clearance, 0, tilt2, -azimuth1)

            prg = self.robot.program

            prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                      kinematic_name=self.robot.default_kinematic_name)

            try:
                prg.set_speed(speed, acceleration)
                swipe_primitive = prg.swipe(swipe_start, swipe_end, radius)

                def modify_separation(path):
                    # Create track that matches the one used for swipe planning.
                    length = swipe_primitive.length()
                    track = golden_program.create_track(speed, acceleration, length)

                    assert len(track) == len(path)

                    for ind, pos in enumerate(track):
                        d = pos[0]

                        t = d / length

                        # Interpolate separation values according to the track.
                        separation = separation1 + (separation2 - separation1) * t

                        # This will not affect the effector speed or position from what swipe gesture has planned.
                        # However the x and y joint speeds will be affected. If separation increases with constant speed,
                        # the x and/or y joint speeds will be decreased by corresponding amount.
                        setattr(path[ind], "separation", separation)

                prg.move([swipe_primitive, ModifyPrimitive(modify_separation)])
                prg.run()
            finally:
                # Reset program speed and acceleration.
                # Speed and acceleration should be set each time program is used but in case they aren't,
                # it is safer to set original values here as fast swipe speed can be very high.
                prg.clear()
                prg.set_speed(orig_speed, orig_acc)
                prg.run()

        return "ok"        

    @json_out
    def put_double_tap(self, x: float, y: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                       clearance: float = 0, duration: float = 0, interval: float = 0, separation=None,
                       tool_name=None):
        """
        Performs a double tap with given parameters.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: Target z coordinate on DUT when tapping (default: 0).
        :param duration: How long to keep finger down in seconds (default: 0s).
        :param interval: How long to pause between taps in seconds (default: 0s).
        :param separation: Separation during tap. If None, then default separation is used.
        :param tool_name: Name of tool to perform tap with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """
        # in case of multifinger, fall back to original gesture
        if self.robot.has_multifinger():
            super().put_double_tap(x=x, y=y, z=z, tilt=tilt, azimuth=azimuth,
                                            clearance=clearance, duration=duration, interval=interval)
            return "ok"

        log.info("put_double_tap x={} y={} z={} tilt={} azimuth={} clearance={} duration={} interval={} "
                 "separation={}, tool_name={}".format(x, y, z, tilt, azimuth, clearance, duration, interval,
                                                      separation, tool_name))

        prg = self.robot.program

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        if tool_name is None:
            tool_name = "tool1"

        if tool_name == "tool1":
            axis_name = "voicecoil1"
        elif tool_name == "tool2":
            axis_name = "voicecoil2"
        elif tool_name == "both":
            axis_name = "voicecoil1"
            # Copy motion to VC2 in motion planning below.
        else:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth(axis_name))

        p2 = primitive_axis_movement(axis_name, voicecoil_distance, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)
        p3 = prg.pause(duration)
        p4 = primitive_axis_movement(axis_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION)

        # 3. tap with optional pause (down duration)
        with VoicecoilGesture(self, x, y, z, finger_depth=0, tilt=tilt, azimuth=azimuth, separation=separation, tool_name=tool_name):
            prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, voicecoil_distance + clearance, 0, tilt, -azimuth)))

            if tool_name == "both":
                # Use ModifyPrimitive to copy VC1 motion to VC2.
                def path_func(path):
                    for pos in path:
                        pos.voicecoil2 = pos.voicecoil1

                prg.move([p2, p3, p4, prg.pause(interval), p2, p3, p4, ModifyPrimitive(path_func)])
            else:
                prg.move([p2, p3, p4, prg.pause(interval), p2, p3, p4])

            prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)))
            prg.run()

        return "ok"

    @json_out
    def put_drag(self, x1, y1, x2, y2, z: float = None, tilt1: float = 0, tilt2: float = 0,
                 azimuth1: float = 0, azimuth2: float = 0, clearance: float = 0, predelay: float = 0,
                 postdelay: float = 0, separation=None, tool_name=None):
        """
        Performs a drag with given parameters.

        :param x1: Start x coordinate on DUT.
        :param y1: Start y coordinate on DUT.
        :param x2: End x coordinate on DUT.
        :param y2: End y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt1: Start tilt angle in DUT frame.
        :param tilt2: End tilt angle in DUT frame.
        :param azimuth1: Start azimuth angle in DUT frame.
        :param azimuth2: End azimuth angle in DUT frame.
        :param clearance: Z coordinate on DUT when running drag (default: 0)
        :param predelay: Delay between touchdown and move in seconds.
        :param postdelay: Delay between the end of movement and touchup in seconds.
        :param separation: Separation during drag. If None, then default separation is used.
        :param tool_name: Name of tool to perform drag with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """

        log.info("put_drag x1={} y1={} x2={} y2={} z={} tilt1={} tilt2={} azimuth1={} azimuth2={} clearance={} "
                 "predelay={} postdelay={} separation={} tool_name={}".format(
            x1, y1, x2, y2, z, tilt1, tilt2, azimuth1, azimuth2, clearance, predelay, postdelay, separation, tool_name))

        if abs(azimuth2 - azimuth1) > ANGLE_RANGE_LIMIT:
            raise Exception("Drag gesture angle range cannot exceed {} degrees".format(ANGLE_RANGE_LIMIT))

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        if tool_name is None:
            tool_name = "tool1"

        if tool_name not in ["tool1", "tool2", "both"]:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        with VoicecoilGesture(gestures=self, x=x1, y=y1, z=z, tilt=tilt1, azimuth=azimuth1, separation=separation, tool_name=tool_name):
            super().drag(x1, y1, x2, y2, z, tilt1, tilt2, azimuth1, azimuth2, clearance,
                                      predelay, postdelay, "mid" if tool_name == "both" else tool_name)
        return "ok"

    @json_out
    def put_drag_force(self, x1: float, y1: float, x2: float, y2: float, force: float, z: float = None,
                       tilt1: float = 0, tilt2: float = 0, azimuth1: float = 0, azimuth2: float = 0,
                       separation=None, tool_name=None):
        """
        Performs a drag with force with given parameters.

        Force can be applied with tool1, tool2 or with both simultaneously. Note that the tool that is used
        must have a valid force calibration table in the configuration. Otherwise exception is raised.
        In case both tools are used, the given force is per tool so that force=100 & tool_name="both" will apply
        200 gF on the target.

        :param x1: Start x coordinate on DUT.
        :param y1: Start y coordinate on DUT.
        :param x2: End x coordinate on DUT.
        :param y2: End y coordinate on DUT.
        :param force: Grams of force to apply when running on DUT surface.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt1: Start tilt angle in DUT frame.
        :param tilt2: End tilt angle in DUT frame.
        :param azimuth1: Start azimuth angle in DUT frame.
        :param azimuth2: End azimuth angle in DUT frame.
        :param separation: Separation during drag force. If None, then default separation is used.
        :param tool_name: Name of tool to perform drag force with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """
        log.info("put_drag_force x1={} y1={} x2={} y2={} force={} z={} tilt1={} tilt2={} azimuth1={} azimuth2={}".format(
            x1, y1, x2, y2, force, z, tilt1, tilt2, azimuth1, azimuth2))

        if self.robot.has_multifinger():
            # maybe this could be done by controlling current on both voicecoils?
            raise Exception("drag force not supported with multifinger tool!")

        if abs(azimuth2 - azimuth1) > ANGLE_RANGE_LIMIT:
            raise Exception("Drag force gesture angle range cannot exceed {} degrees".format(ANGLE_RANGE_LIMIT))

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        if tool_name is None:
            tool_name = "tool1"

        if tool_name == "tool1":
            kinematic_name = "tool1"
        elif tool_name == "tool2":
            kinematic_name = "tool2"
        elif tool_name == "both":
            kinematic_name = "mid"
        else:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        toolframe = self.robot.tool_frame(kinematic_name)

        # Set separation if given.
        if separation is not None:
            prg = self.robot.program
            prg.begin(ctx=self, toolframe=toolframe, kinematic_name=kinematic_name)
            prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

            # 1. Move over target position at base distance
            prg.move(prg.point(robotmath.xyz_euler_to_frame(x1, y1, z, 0, tilt1, -azimuth1)))

            prg.move(primitive_axis_movement("separation", target=separation))
            prg.run()

        self.robot.force_driver.drag_force(context=self, x1=x1, y1=y1, x2=x2, y2=y2, force=force,
                                           z=z, tilt1=tilt1, tilt2=tilt2, azimuth1=azimuth1, azimuth2=azimuth2,
                                           tool_name=tool_name)

        return "ok"

    @json_out
    def put_circle(self, x: float, y: float, r: float, n: float = 1, angle: float = 0, z: float = None, tilt: float = 0,
                   azimuth: float = 0, clearance: float = 0, clockwise: bool = False, separation=None, tool_name=None):
        """
        Performs a circle movement with given parameters.

        :param x: Circle center x coordinate on DUT.
        :param y: Circle center y coordinate on DUT.
        :param r: Circle radius.
        :param n: How many circles should be moved. Can be floating point.
        :param angle: Start angle in degrees. For 0 angle, start x is x+r and start y is y.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: Coordinate z on dut when moving in circle (default: 0).
        :param clockwise: True if moving clockwise, false to move counter clockwise (default: false).
        :param separation: Separation during circle. If None, then default separation is used.
        :param tool_name: Name of tool to perform circle with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """
        log.info("put_circle: x={} y={} r={} n={} angle={} z={} tilt={} azimuth={} clearance={} clockwise={}"
                 "separation={} tool_name={}".format(x, y, r, n, angle, z, tilt, azimuth, clearance, clockwise,
                                                     separation, tool_name))

        rad = np.radians(angle)

        start_x = x + np.cos(rad) * r
        start_y = y + np.sin(rad) * r

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        if tool_name is None:
            tool_name = "tool1"

        if tool_name not in ["tool1", "tool2", "both"]:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        with VoicecoilGesture(gestures=self, x=start_x, y=start_y, z=z,  tilt=tilt, azimuth=azimuth,
                              separation=separation, tool_name=tool_name):
            super().circle(x=x, y=y, r=r, n=n, angle=angle, z=z, tilt=tilt, azimuth=azimuth, clearance=clearance,
                           clockwise=clockwise, tool_name="mid" if tool_name == "both" else tool_name)
        return "ok"

    @json_out
    def put_multiswipe(self, x1: float, y1: float, x2: float, y2: float, z: float = None,
                       tilt: float = 0, azimuth: float = 0, clearance: float = 0, n: float = 2,
                       separation=None, tool_name=None):
        """
        Performs multiple swipe movements with given parameters.

        :param x1: Start x coordinate on DUT.
        :param y1: Start y coordinate on DUT.
        :param x2: End x coordinate on DUT.
        :param y2: End y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: Coordinate z on DUT when running swipe (default: 0).
        :param n: Number of swipes to draw. Back and forth counts as two (default: 2).
        :param separation: Separation during multiswipe. If None, then default separation is used.
        :param tool_name: Name of tool to perform multiswipe with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """

        log.info("put_multiswipe x1={} y1={} x2={} y2={} z={} tilt={} azimuth={} clearance={} n={}"
                 "separation={} tool_name={}".format(x1, y1, x2, y2, z, tilt, azimuth, clearance, n,
                                                     separation, tool_name))

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        if tool_name is None:
            tool_name = "tool1"

        if tool_name not in ["tool1", "tool2", "both"]:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        with VoicecoilGesture(gestures=self, x=x1, y=y1, z=z, tilt=tilt, azimuth=azimuth,
                              separation=separation, tool_name=tool_name):
            super().multiswipe(x1=x1, y1=y1, x2=x2, y2=y2, z=z, tilt=tilt, azimuth=azimuth, clearance=clearance, n=n,
                               tool_name="mid" if tool_name == "both" else tool_name)
        return "ok"

    @json_out
    def put_path(self, points, clearance=0, separation=None, tool_name=None):
        """
        Performs path movement through given points.

        :param points: List of points to go through.
        :param clearance: Clearance added to z value of each point.
        :param separation: Separation during path. If None, then default separation is used.
        :param tool_name: Name of tool to perform path with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """

        log.info("put_path points={} clearance={} separation={} tool_name={}".format(points, clearance,
                                                                                     separation, tool_name))

        if tool_name is None:
            tool_name = "tool1"

        if tool_name not in ["tool1", "tool2", "both"]:
            raise Exception("Invalid tool_name '{}'. Must be one of 'tool1', 'tool2' or 'both'.".format(tool_name))

        if len(points) > 0:
            p = points[0]
            x, y, z, tilt, azimuth = p['x'], p['y'], p['z'], p.get('tilt', 0), p.get('azimuth', 0)

            with VoicecoilGesture(gestures=self, x=x, y=y, z=z, tilt=tilt, azimuth=azimuth,
                                  separation=separation, tool_name=tool_name):
                super().path(points=points, clearance=clearance, tool_name="mid" if tool_name == "both" else tool_name)
        return "ok"

    @json_out
    def put_rotate(self, x: float, y: float, azimuth1: float, azimuth2: float, separation: float,
                    z: float=None, clearance: float=0):
        """
        Rotate movement:
        - Middle point of the fingers is moved to (x, y)
        - Both fingers are lowered to touch the surface
        - Azimuth axis is rotated from azimuth1 to azimuth2

        :param x: Target x coordinate on DUT. Target is the middle position between fingers.
        :param y: Target y coordinate on DUT. Target is the middle position between fingers.
        :param azimuth1: Start azimuth angle.
        :param azimuth2: End azimuth angle.
        :param separation: Distance between fingers during the gesture
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param clearance: Distance from DUT surface during gesture.
        :return: "ok" / error
        """

        if self.robot.has_multifinger():
            raise Exception("Rotate gesture can't be performed with multifinger")

        if abs(azimuth2 - azimuth1) > ANGLE_RANGE_LIMIT:
            raise Exception("Rotate gesture angle range cannot exceed {} degrees".format(ANGLE_RANGE_LIMIT))

        assert self.parent.base_distance is not None, "DUT base distance not set"

        dut = self.parent
        base_distance = dut.base_distance if z is None else z

        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame("tool1"), kinematic_name="mid")
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        # 1. move over starting position, set separation, move down to touch position
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, base_distance, 0, 0, -azimuth1)))
        prg.move(primitive_separation(separation))
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, clearance, 0, 0, -azimuth1)))

        # 2. Rotate azimuth axis
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, clearance, 0, 0, -azimuth2)))

        # # 3. move up
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x, y, base_distance, 0, 0, -azimuth2)))
        prg.run()
        
    @json_out
    def put_touch_and_drag(self, x0: float, y0: float, x1: float, y1: float, x2: float, y2: float, z: float=None,
                           clearance: float=0, delay=0, touch_duration=None):
        """
        Perform touch and drag:
        - Keep touching point (x0, y0) with tip1
        - Simultaneously, use tip2 to draw an interpolated line from (x1, y1) to (x2, y2)

        :param x0: Tip1 x coordinate on DUT
        :param y0: Tip1 y coordinate on DUT
        :param x1: Line start x coordinate on DUT
        :param y1: Line start y coordinate on DUT
        :param x2: Line end x coordinate on DUT
        :param y2: Line end y coordinate on DUT
        :param z: Target z coordinate on DUT when hovering before and after gesture
                  (default: DUT's base_distance).
        :param clearance: (optional) Distance from DUT surface during movement.
        :param delay: Delay from start of primary finger touch to secondary finger drag.
        :param touch_duration: Duration of primary finger touch. None value means that primary finger touches during entire drag motion.
        :return: "ok" / error
        """
        if self.robot.has_multifinger():
            raise Exception("Touch swipe gesture can't be performed with multifinger")

        line_start = np.array([x1, y1])
        line_end = np.array([x2, y2])

        azimuth1 = -math.degrees(math.atan2(y1 - y0, x1 - x0))
        azimuth2 = -math.degrees(math.atan2(y2 - y0, x2 - x0))
        log.debug("azimuth1: {}".format(azimuth1))
        log.debug("azimuth2: {}".format(azimuth2))

        start_separation = np.linalg.norm(([x0 - x1, y0 - y1]))

        min_separation = robotmath.point_distance_to_line_segment(line_start, line_end, np.array([x0, y0]))

        # Check for a trivial case that would lead to division by zero error.
        # The case where touch point is too close to the swipe line is handled by error checking at
        # robot driver level.
        if min_separation == 0:
            raise Exception("Touch point cannot be on the drag line.")

        # Analogous to touch and tap.
        touching_actuator_name = "voicecoil1"
        dragging_actuator_name = "voicecoil2"
        kinematic_name = "tool2"

        assert self.parent.base_distance is not None, "DUT base distance not set"

        dut = self.parent
        z = dut.base_distance if z is None else z

        touching_voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth(touching_actuator_name))
        dragging_voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth(dragging_actuator_name))

        # z-position before voice coil tap (when voice coil is at zero).
        pre_voicecoil_z = touching_voicecoil_distance + clearance

        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(kinematic_name), kinematic_name=kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        # 1. move over starting position
        prg.move(primitive_axis_movement(touching_actuator_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
        prg.move(primitive_axis_movement(dragging_actuator_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x1, y1, z, 0, 0, -azimuth1)))
        prg.run()
        prg.clear()

        # 2. move to target separation
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move(primitive_axis_movement("separation", start_separation, self.robot.robot_velocity, self.robot.robot_acceleration))
        prg.run()
        prg.clear()

        # 3. move down to Z height where to start gesture utilizing voice coil
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x1, y1, pre_voicecoil_z, 0, 0, -azimuth1)))
        prg.run()
        prg.clear()

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        if touch_duration is None:
            # 4. lower both voicecoils
            prg.move(primitive_axis_movement(touching_actuator_name, touching_voicecoil_distance))
            prg.move(primitive_axis_movement(dragging_actuator_name, dragging_voicecoil_distance))

            # 5. prepare drag movement based on tool2 kinematics
            primitives = [prg.pause(delay),
                          prg.line(robotmath.xyz_euler_to_frame(x1, y1, pre_voicecoil_z, 0, 0, -azimuth1),
                                   robotmath.xyz_euler_to_frame(x2, y2, pre_voicecoil_z, 0, 0, -azimuth1))]


        else:
            axes = {dragging_actuator_name: [dragging_voicecoil_distance, dragging_voicecoil_distance]}

            # These primitives plan motion for the dragging finger. It starts with pause because during that time
            # the touching finger can perform its own movement. That movement is glued on top by use of
            # KeyFrameAxisPrimitive below.
            # For the line primitive, the voicecoil position of dragging finger must be specified because otherwise
            # no VC positions would be specified for the line motion and IK would place current VC setpoint which
            # is zero.
            primitives = [prg.pause(delay),
                          primitive_axis_movement(dragging_actuator_name, dragging_voicecoil_distance),
                          prg.line(robotmath.xyz_euler_to_frame(x1, y1, pre_voicecoil_z, 0, 0, -azimuth1),
                                   robotmath.xyz_euler_to_frame(x2, y2, pre_voicecoil_z, 0, 0, -azimuth1),
                                   axes=axes)]

        # Add separation and azimuth movement for each drag step, ensuring that finger 2 is stationary.
        def modify_separation(path):
            for p in path:
                cx, cy, cz = robotmath.frame_to_xyz(p.frame)

                # Determine robot x-direction so that the tool points towards the stationary finger.
                robot_x = np.array([x0 - cx, y0 - cy, 0])
                robot_x = robot_x / np.linalg.norm(robot_x)

                # Calculate the other two basis vectors by orthogonality.
                robot_z = np.array([0, 0, -1])
                robot_y = np.cross(robot_z, robot_x)

                # Set new basis.
                robotmath.set_frame_x_basis_vector(p.frame, robot_x)
                robotmath.set_frame_y_basis_vector(p.frame, robot_y)
                robotmath.set_frame_z_basis_vector(p.frame, robot_z)

                # Separation is the distance from robot position to the stationary finger.
                separation = np.linalg.norm(np.array([cx - x0, cy - y0]))

                setattr(p, "separation", separation)

        if touch_duration is not None:
            p = KeyFrameAxisPrimitive(touching_actuator_name, key_times=[0])
            p.plan_tap(touching_voicecoil_distance, self.robot.robot_velocity, self.robot.robot_acceleration,
                       touch_duration)
            primitives.append(p)

        separation_primitive = ModifyPrimitive(modify_separation)
        primitives.append(separation_primitive)

        prg.move(primitives)

        # move up at the end
        prg.move(prg.point(robotmath.xyz_euler_to_frame(x2, y2, z, 0, 0, -azimuth2)))

        # run() might throw an exception if tips are in danger of colliding with these azimuth and separation params
        try:
            prg.run()
        finally:
            prg.clear()
            prg.move(primitive_axis_movement(touching_actuator_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
            prg.move(primitive_axis_movement(dragging_actuator_name, 0, VOICECOIL_SPEED, VOICECOIL_ACCELERATION))
            prg.run()

        return "ok"
