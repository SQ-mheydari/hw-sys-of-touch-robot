import tntserver.drivers.robots.sm_regs as SMRegs
import tntserver.Nodes.TnT.Gestures
from tntserver.Nodes.Node import *
from tntserver.drivers.robots.golden_program import primitive_axis_movement
from tntserver.drivers.robots.goldenmov.opto_std_force import VoicecoilMaxContPeakCurrent

# for one finger movements
PRIMARY_FINGER_AXIS_NAME = "voicecoil1"
"""
Voicecoil actuator Gestures
"""


class Gestures(tntserver.Nodes.TnT.Gestures.Gestures):
    """
    Gestures for Synchro robot.
    """

    def __init__(self, name):
        super().__init__(name)

    def _init(self, **kwargs):
        super()._init(**kwargs)

    @json_out
    def put_tap(self, x: float, y: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                clearance: float = 0, duration: float = 0):
        """
        Performs a tap with given parameters.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: (optional) distance from DUT surface during movement
        :param duration: How long to keep finger down in seconds (default: 0s).
        :return: "ok" / error
        """
        log.info("put_tap x={} y={} z={} tilt={} azimuth={} clearance={} duration={}".format(
            x, y, z, tilt, azimuth, clearance, duration))

        # in case of multifinger, fall back to original gesture
        if self.robot.has_multifinger():
            super().put_tap(x=x, y=y, z=z, tilt=tilt, azimuth=azimuth, clearance=clearance, duration=duration)
            return "ok"

        self.move_voicecoil_to_home_position()
        # voicecoil tap if normal finger attached
        prg = self.robot.program

        assert self.parent.base_distance is not None, "DUT base distance not set"
        z = self.parent.base_distance if z is None else z
        voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth())

        # go to starting position for voicecoil move
        p1 = prg.point(robotmath.xyz_euler_to_frame(x, y, voicecoil_distance + clearance, 0, tilt, -azimuth))
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move([p1])
        prg.run()
        with VoicecoilMaxContPeakCurrent(robot=self.robot, max_cont_current=self.robot.voicecoil_cont_current,
                                         peak_current=self.robot.voicecoil_peak_current):
            # use voicecoil to perform tap
            f = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)
            prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                      kinematic_name=self.robot.voicecoil_kinematic_name)
            prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
            tap_primitives = prg.tap(f, voicecoil_distance + clearance, clearance, duration)

            prg.move(tap_primitives)
            prg.run()
        # go back away from DUT to base_distance or z
        p1 = prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth))
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move([p1])
        prg.run()

        return "ok"

    @json_out
    def put_double_tap(self, x: float, y: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                       clearance: float = 0, duration: float = 0, interval: float = 0):
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
        """
        # in case of multifinger, fall back to original gesture
        if self.robot.has_multifinger():
            super().put_double_tap(x=x, y=y, z=z, tilt=tilt, azimuth=azimuth,
                                            clearance=clearance, duration=duration, interval=interval)
            return "ok"

        prg = self.robot.program

        assert self.parent.base_distance is not None, "DUT base distance not set"
        z = self.parent.base_distance if z is None else z
        voicecoil_distance = min(z - clearance, self.robot.get_finger_press_depth())

        self.move_voicecoil_to_home_position()
        # go to starting position for voicecoil move
        p1 = prg.point(robotmath.xyz_euler_to_frame(x, y, voicecoil_distance + clearance, 0, tilt, -azimuth))

        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move([p1])
        prg.run()

        with VoicecoilMaxContPeakCurrent(robot=self.robot, max_cont_current=self.robot.voicecoil_cont_current,
                                         peak_current=self.robot.voicecoil_peak_current):
            # use voicecoil to perform taps
            f = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)
            prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                      kinematic_name=self.robot.voicecoil_kinematic_name)
            prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
            tap_primitives = prg.tap(f, voicecoil_distance + clearance, clearance, duration)
            pause = prg.pause(interval)
            prg.move(tap_primitives + [pause] + tap_primitives)
            prg.run()

        # go back away from DUT to base_distance or z
        p1 = prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth))
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move([p1])
        prg.run()

        return "ok"

    @json_out
    def put_swipe(self, x1: float, y1: float, x2: float, y2: float, tilt1: float = 0, tilt2: float = 0,
                            azimuth1: float = 0, azimuth2: float = 0, clearance: float = 0, radius: float = 6):
        """
        Performs a voicecoil swipe with given parameters.
        Robot accelerates and decelerates along an arc of given radius before and after touching the DUT.
        Movement along an arc in z-axis direction is performed by voicecoil.

        :param x1: Swipe start x coordinate on DUT.
        :param x2: Swipe end x coordinate on DUT.
        :param y1: Swipe start y coordinate on DUT.
        :param y2: Swipe end y coordinate on DUT.
        :param tilt1: Swipe start tilt.
        :param tilt2: Swipe end tilt.
        :param azimuth1: Swipe start azimuth.
        :param azimuth2: Swipe end azimuth.
        :param clearance: Z coordinate on DUT when running swipe (default: 0).
        :param radius: Swipe radius.
        """

        # If gesture can't be performed with voice coil with given arguments, then use TnT swipe gesture.
        # Swipe could probably be done with certain tilt angles using VC kinematics but it's hard to determine
        # the exact conditions.
        if radius > self.robot.get_finger_press_depth() or tilt1 != 0 or tilt2 != 0:
            super().put_swipe(x1=x1, y1=y1, x2=x2, y2=y2, tilt1=tilt1, tilt2=tilt2, azimuth1=azimuth1,
                              azimuth2=azimuth2, clearance=clearance, radius=radius)

            return "ok"

        log.info("put_swipe x1={} y1={} x2={} y2={} tilt1={} tilt2={} azimuth1={} azimuth2={} clearance={} radius={}".format(
            x1, y1, x2, y2, tilt1, tilt2, azimuth1, azimuth2, clearance, radius))

        swipe_start = robotmath.xyz_euler_to_frame(x1, y1, clearance, 0, tilt1, -azimuth1)
        swipe_end = robotmath.xyz_euler_to_frame(x2, y2, clearance, 0, tilt2, -azimuth2)

        # this is just to get first point of the swipe movement - beginning of the arc
        # calculate offset to start location (swipe creates quarter circle arc in the beginning using given radius)
        v = np.array([x2 - x1, y2 - y1])  # swipe effective touch line
        v_len = np.linalg.norm(v)

        if v_len == 0:
            raise Exception("Planned swipe gesture has zero length. Please adjust swipe parameters and retry.")

        dx, dy = -radius * v / v_len
        x, y, z = [x1+dx, y1+dy, radius+clearance]
        self.move_voicecoil_to_home_position()
        prg = self.robot.program

        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        # define first point of the swipe movement
        p0 = prg.point(robotmath.xyz_euler_to_frame(x, y, z, 0, tilt1, -azimuth1))
        # move to starting point with default_kinematic_name
        prg.move([p0])
        prg.run()
        # swipe with voicecoil_kinematic_name
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.voicecoil_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        p1 = prg.swipe(swipe_start, swipe_end, radius)
        prg.move([p1])
        prg.run()
        self.move_voicecoil_to_home_position()

        return "ok"

    def move_voicecoil_to_home_position(self):
        """
        Move voicecoil to home. This should be called after gesture motion if gesture may leave voice coil
        to some other position than zero.
        """
        # TODO: this will fail if for some reason voicecoil moved outside of the limits
        # TODO: it can happen during force moves
        prg = self.robot.program

        # Use robot_velocity and robot_acceleration instead of voicecoil_speed and voicecoil_acceleration because
        # during this motion effector position remains stationary and z axis compensates VC movement.
        p0_vc = primitive_axis_movement('voicecoil1', 0, self.robot.robot_velocity, self.robot.robot_acceleration)

        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)
        prg.move([p0_vc])
        prg.run()
