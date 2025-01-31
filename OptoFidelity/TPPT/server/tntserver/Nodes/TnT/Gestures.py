import collections
import logging
import math

from tntserver.Nodes.Node import *
from tntserver.Nodes.TnT.Workspace import get_node_workspace

log = logging.getLogger(__name__)

# Limit the distance between azimuth1 and azimuth2 in gestures.
ANGLE_RANGE_LIMIT = 179

"""
Commands needed by TnT Sequencer with Tap test & Swipe test

GET /tnt/workspaces/ws/duts
GET /tnt/workspaces/ws/duts/DUT1
GET /tnt/workspaces/ws/tips
GET /tnt/workspaces/ws/tips/Stylus

PUT /tnt/workspaces/ws/duts/DUT1/gestures/tap
PUT /tnt/workspaces/ws/duts/DUT1/gestures/swipe
GET /tnt/workspaces/ws/duts/DUT1/data/screen_width
GET /tnt/workspaces/ws/duts/DUT1/data/screen_height
GET /tnt/workspaces/ws/duts/DUT1

GET /tnt/workspaces/ws/tips/Tip9

"""

"""
- Gesture has to support Tap, Swipe, Jump, etc...
- Gesture can move robot's effective position in it's own frame
- For all robot movements, maybe there should be an "active" robot in global variables
- In traditional dut.gesture commands the active robot is not defined
"""

""" Type for JSON input list with three numbers"""


class Gestures(Node):
    """
    TnT™ Compatible Gestures resource
    Should work together with
    - TnT Sequencer
    - TnT Positioning Tool

    is an add-on for DUT resource
    """

    # not saved to config
    # always just piggybacking duts
    transient = True

    def __init__(self, name):
        super().__init__(name)
        self._robot_name = None
        self.robot = None

    def _init(self, robot=None, **kwargs):
        if robot is not None:
            log.warning("Gestures robot argument is deprecated. Please remove from configuration.")
            if self._robot_name is None:
                self._robot_name = robot

        # By default use robot in the same workspace as DUT. Can be changed via API.
        ws = get_node_workspace(self)
        robots = Node.find_class_from(ws, "Robot")

        if len(robots) == 0:
            log.warning("Could not find robot for gestures within the same workspace.")
        else:
            # Use the first robot found in the workspace. Normally there should be only one robot in a workspace.
            self.robot = robots[0]

    @json_out
    def put_robot(self, robot_name):
        """
        Set robot to be used to perform gestures on the DUT.
        :param robot_name: Name of the robot.
        """

        # Find robot from the workspace.
        ws = get_node_workspace(self)
        robot = Node.find_from(ws, robot_name)

        if robot is None:
            raise Exception("Could not find robot '{}' to be set for DUT '{}' gestures.".format(robot_name, self.parent.name))

        self.robot = robot

        log.info("Set robot '{}' for DUT '{}' gestures.".format(robot_name, self.parent.name))

    def dut_to_robot_transform(self):
        return robotmath.translate(robotmath.identity_frame(), self.parent, self.robot.object_parent)

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
        :param clearance: Target z coordinate on DUT when tapping (default: 0).
        :param duration: How long to keep finger down in seconds (default: 0s).
        """

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        log.info("put_tap x={} y={} z={} tilt={} azimuth={} clearance={} duration={}".format(
            x, y, z, tilt, azimuth, clearance, duration))


        f = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)

        prg = self.robot.program

        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        tap_primitives = prg.tap(f, z, clearance, duration)

        prg.move(tap_primitives)
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

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        log.info("put_double_tap x={} y={} z={} tilt={} azimuth={} clearance={} duration={} interval={}".format(
                 x, y, z, tilt, azimuth, clearance, duration, interval))

        f = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)
        f0 = f.copy()
        f1 = f.copy()
        f1.A[2, 3] = clearance

        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)

        p1 = prg.line(f0, f1)
        p2 = prg.pause(duration)
        p3 = prg.line(f1, f0)
        p4 = prg.pause(interval)
        p5 = prg.line(f0, f1)
        p6 = prg.pause(duration)
        p7 = prg.line(f1, f0)

        prg.move([p1, p2, p3, p4, p5, p6, p7])
        prg.run()

        return "ok"

    @json_out
    def put_fasttap(self, depth: float = 1, n: float = 1, duration: float = 0):
        """
        Performs tap at current position using voice coil with given parameters.

        :param depth: Distance to move voice coil (default: 1).
        :param n: Number of taps (default: 1).
        :param duration: How long to keep actuator down in seconds (default: 0s).
        """
        log.info("put_voicecoiltap depth={} n={} duration={}".format(depth, n, duration))
        # self.robot.put_voicecoiltap(depth, n, duration)
        return "not supported"

    @json_out
    def put_watchdog_tap(self, x: float, y: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                         clearance: float = 0, duration: float = 0, trigger_direction: str = None):
        """
        Performs a tap designed for HW level triggering based on when the DUT is touched.
        Example use case is watchdog measurement.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: (optional) distance from DUT surface during movement
        :param duration: How long to keep finger down in seconds (default: 0s).
        :param trigger_direction: Trigger when touching the DUT.
                                  None means that no triggering is done.
                                  "TOUCH_START" triggers when tool goes down to start touching the DUT.
                                  "TOUCH_END" triggers when tool goes up from DUT detach from it.
        :return: "ok" / error
        """
        log.info("put_watchdog_tap x={} y={} z={} tilt={} azimuth={} clearance={} duration={} "
                 "trigger_direction={}".format(x, y, z, tilt, azimuth, clearance, duration, trigger_direction))

        if trigger_direction is not None:
            if self.robot.triggersensor is not None:
                # Set triggering
                if trigger_direction == "TOUCH_START":
                    self.robot.triggersensor.set_trigger_touch_start()
                elif trigger_direction == "TOUCH_END":
                    self.robot.triggersensor.set_trigger_touch_end()
                else:
                    raise Exception("Invalid trigger_direction={} given. "
                                    "Allowed values are 'TOUCH_START' and 'TOUCH_END'".format(trigger_direction))
            else:
                raise Exception("{} doesn't have triggersensor configured but trigger_direction parameter "
                                "was given.".format(self.robot.name))

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        f = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth)

        prg = self.robot.program

        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        tap_primitives = prg.tap(f, z, clearance, duration)

        prg.move(tap_primitives)
        prg.run()

        return "ok"

    @json_out
    def put_spin_tap(self, x: float, y: float, z: float = None, tilt: float = 0, azimuth1: float = 0,
                     azimuth2: float = 0, clearance: float = 0, duration: float = 0, spin_at_contact: bool = True):
        """
        Performs a spinning tap with given parameters.
        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth1: Azimuth angle at start of gesture in DUT frame (default: 0).
        :param azimuth2: Azimuth angle at end of gesture in DUT frame (default: 0)
        :param clearance: Target z coordinate on DUT when tapping (default: 0).
        :param duration: How long to keep finger down in seconds (default: 0s).
        :param spin_at_contact: True: rotation from azimuth1 to azimuth2 happens only when finger is at lowest
        position. False: Rotation from azimuth1 to azimuth2 happens parallel with Z-movement.
        """

        if abs(azimuth2 - azimuth1) > ANGLE_RANGE_LIMIT:
            raise ValueError("Spin tap gesture angle range cannot exceed {} degrees".format(ANGLE_RANGE_LIMIT))

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        log.info("put_spin_tap x={} y={} z={} tilt={} azimuth1={} azimuth2={} clearance={} duration={} "
                 "spin_at_contact={}".format(x, y, z, tilt, azimuth1, azimuth2, clearance, duration, spin_at_contact))

        f0 = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth1)
        f1 = robotmath.xyz_euler_to_frame(x, y, z, 0, tilt, -azimuth2)
        f2 = f0.copy()
        f3 = f1.copy()
        f1.A[2, 3] = clearance
        f2.A[2, 3] = clearance

        prg = self.robot.program
        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)
        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        if spin_at_contact is True:
            p1 = prg.line(f0, f2)
            p2 = prg.line(f2, f1)
            primitives = [p1, p2]
        else:
            p1 = prg.line(f0, f1)
            primitives = [p1]

        p3 = prg.pause(duration)
        p4 = prg.line(f1, f3)
        primitives += [p3, p4]
        prg.move(primitives)
        prg.run()

        return "ok"

    @json_out
    def put_press(self, x: float, y: float, force: float, z: float = None, tilt: float = 0, azimuth: float = 0,
                  duration: float = 0, press_depth: float = -1):
        """
        Performs a press gesture in DUT context.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param force: Force in grams, to be activated after moving to lower position.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param duration: How long to keep specified force active in seconds (default: 0s).
        :param press_depth: Distance from DUT surface during press, negative values being below/through DUT surface.
        Value may be ignored by some force drivers.
        :return: "ok" / error
        """
        log.info("put_press x={} y={} force={} z={} tilt={} azimuth={} duration={}".format(
            x, y, force, z, tilt, azimuth, duration))

        dut = self.parent

        assert dut.base_distance is not None, "DUT base distance not set"

        z = dut.base_distance if z is None else z

        press_depth = -1

        if self.robot.force_driver is None:
            raise Exception("Robot has no force driver.")

        ret = self.robot.force_driver.press(context=self, x=x, y=y, force=force, z=z, tilt=tilt,
                                            azimuth=azimuth, duration=duration, press_depth=press_depth,
                                            tool_name="tool1")

        # Ensure the voicecoil returns to zero.
        self.robot.move_joint_position({"voicecoil1": 0.0})

        return ret


    @json_out
    def put_swipe(self, x1: float, y1: float, x2: float, y2: float, tilt1: float = 0, tilt2: float = 0,
                  azimuth1: float = 0, azimuth2: float = 0, clearance: float = 0, radius: float = 6):
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
        :param clearance: Z coordinate on DUT when running swipe (default: 0).
        :param radius: Swipe radius.
        """
        log.info("put_swipe x1={} y1={} x2={} y2={} tilt1={} tilt2={} azimuth1={} azimuth2={} clearance={} radius={}".format(
            x1, y1, x2, y2, tilt1, tilt2, azimuth1, azimuth2, clearance, radius))

        swipe_start = robotmath.xyz_euler_to_frame(x1, y1, clearance, 0, tilt1, -azimuth1)
        swipe_end = robotmath.xyz_euler_to_frame(x2, y2, clearance, 0, tilt2, -azimuth2)

        prg = self.robot.program

        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        p1 = prg.swipe(swipe_start, swipe_end, radius)

        prg.move([p1])
        prg.run()

        return "ok"

    @json_out
    def put_drag(self, x1, y1, x2, y2, z: float = None, tilt1: float = 0, tilt2: float = 0,
                 azimuth1: float = 0, azimuth2: float = 0, clearance: float = 0, predelay: float = 0,
                 postdelay: float = 0):
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
        """

        log.info("put_drag x1={} y1={} x2={} y2={} z={} tilt1={} tilt2={} azimuth1={} azimuth2={} clearance={} "
                 "predelay={} postdelay={}".format(
            x1, y1, x2, y2, z, tilt1, tilt2, azimuth1, azimuth2, clearance, predelay, postdelay))

        self.drag(x1, y1, x2, y2, z, tilt1, tilt2, azimuth1, azimuth2, clearance, predelay, postdelay)

        return "ok"

    def drag(self, x1, y1, x2, y2, z: float = None, tilt1: float = 0, tilt2: float = 0,
                 azimuth1: float = 0, azimuth2: float = 0, clearance: float = 0, predelay: float = 0,
                 postdelay: float = 0, tool_name=None):
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
        :param tool_name: Name of tool to perform drag with. If None, default tool is used.
        """

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        drag_start_up = robotmath.xyz_euler_to_frame(x1, y1, z, 0, tilt1, -azimuth1)
        drag_start_down = robotmath.xyz_euler_to_frame(x1, y1, clearance, 0, tilt1, -azimuth1)
        drag_end_up = robotmath.xyz_euler_to_frame(x2, y2, z, 0, tilt2, -azimuth2)
        drag_end_down = robotmath.xyz_euler_to_frame(x2, y2, clearance, 0, tilt2, -azimuth2)

        prg = self.robot.program

        kinematic_name = self.robot.default_kinematic_name if tool_name is None else tool_name
        tool_frame = self.robot.tool_frame(kinematic_name)

        prg.begin(ctx=self, toolframe=tool_frame, kinematic_name=kinematic_name)

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        p1 = prg.line(drag_start_up, drag_start_down)
        p2 = prg.line(drag_start_down, drag_end_down)
        p3 = prg.line(drag_end_down, drag_end_up)

        p_predelay = prg.pause(predelay)
        p_postdelay = prg.pause(postdelay)

        prg.move([p1, p_predelay, p2, p_postdelay, p3])

        prg.run()

    @json_out
    def put_drag_force(self, x1: float, y1: float, x2: float, y2: float, force: float, z: float = None,
                       tilt1: float = 0, tilt2: float = 0, azimuth1: float = 0, azimuth2: float = 0):
        """
        Performs a drag with force with given parameters.

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
        """
        log.info("put_drag_force x1={} y1={} x2={} y2={} force={} z={} tilt1={} tilt2={} azimuth1={} azimuth2={}".format(
            x1, y1, x2, y2, force, z, tilt1, tilt2, azimuth1, azimuth2))

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        if self.robot.force_driver is None:
            raise Exception("Robot has no force driver.")

        if self.robot.force_driver is None:
            raise Exception("Robot has no force driver.")

        return self.robot.force_driver.drag_force(context=self, x1=x1, y1=y1, x2=x2, y2=y2, force=force,
                                           z=z, tilt1=tilt1, tilt2=tilt2, azimuth1=azimuth1, azimuth2=azimuth2,
                                           tool_name="tool1")

    @json_out
    def put_jump(self, x: float, y: float, z: float = 0, jump_height: float = None):
        """
        Performs a jump with given parameters.
        In case jump_height is not given, robot jumps to maximum height along robot z axis.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT.
        :param jump_height: Height of the jump from DUT surface (default: jump to robot maximum height).
        """
        log.info("put_jump: x={} y={} z={} jump_height={}".format(x, y, z, jump_height))

        self.parent.validate_orientation(self.robot)

        curr_frame = self.robot.effective_pose()
        curr_frame_dut = robotmath.translate(curr_frame, self.robot.object_parent, self.object_parent)
        curr_rot = curr_frame_dut[0:3, 0:3]

        xc, yc, zc = robotmath.frame_to_xyz(curr_frame_dut)

        if jump_height is None:
            # Target frame in workspace (target position with current orientation).
            target_frame = robotmath.translate(robotmath.xyz_to_frame(x, y, z), self.object_parent, self.robot.object_parent)
            target_frame[0:3, 0:3] = curr_frame[0:3, 0:3]

            # Get robot maximum z value where to jump to.
            bounds = self.robot.bounds()
            max_z = bounds['z'][1]

            # Set the z value of the first two frames in robot context to the maximum z.
            frame1 = curr_frame.copy()
            robotmath.set_frame_xyz(frame1, z=max_z)

            frame2 = target_frame.copy()
            robotmath.set_frame_xyz(frame2, z=max_z)

            # Perform jump in robot parent context
            prg = self.robot.program
            prg.begin(ctx=self.robot.object_parent, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                      kinematic_name=self.robot.default_kinematic_name)
            prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

            line1 = prg.line(frame1, frame2)
            line2 = prg.line(frame2, target_frame)
            prg.move([line1, line2])

            prg.run()

        else:
            # Create movement in DUT context
            frames = []

            # Jump should not go lower than current z.
            z0 = max(jump_height, zc)

            frames.append(robotmath.xyz_rot_to_frame(xc, yc, z0, curr_rot))
            frames.append(robotmath.xyz_rot_to_frame(x, y, z0, curr_rot))
            frames.append(robotmath.xyz_rot_to_frame(x, y, z, curr_rot))

            # Perform jump in DUT context
            prg = self.robot.program
            prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                      kinematic_name=self.robot.default_kinematic_name)
            prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

            for frame in frames:
                prg.move(prg.point(frame))

            prg.run()

        return "ok"

    @json_out
    def put_circle(self, x: float, y: float, r: float, n: float = 1, angle: float = 0, z: float = None, tilt: float = 0,
                   azimuth: float = 0, clearance: float = 0, clockwise: bool = False):
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
        """

        log.info("put_circle: x={} y={} r={} n={} angle={} z={} tilt={} azimuth={} clearance={} clockwise={}".format(
            x, y, r, n, angle, z, tilt, azimuth, clearance, clockwise))

        self.circle(x, y, r, n, angle, z, tilt, azimuth, clearance, clockwise)

        return "ok"

    def circle(self, x: float, y: float, r: float, n: float = 1, angle: float = 0, z: float = None, tilt: float = 0,
                   azimuth: float = 0, clearance: float = 0, clockwise: bool = False, tool_name=None):
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
        :param tool_name: Name of tool to perform circle with. If None, default tool is used.
        """

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        rad = math.radians(angle)
        stp = math.radians(10)
        rad_end = math.radians(angle + n*360)
        if not clockwise:
            stp = -stp
            rad_end = math.radians(angle - n*360)

        px0 = x + math.cos(rad) * r
        py0 = y + math.sin(rad) * r
        px1 = x + math.cos(rad+stp) * r
        py1 = y + math.sin(rad+stp) * r
        px2 = x + math.cos(rad+stp*2) * r
        py2 = y + math.sin(rad+stp*2) * r

        pxe = x + math.cos(rad_end) * r
        pye = y + math.sin(rad_end) * r

        f0_up = robotmath.xyz_euler_to_frame(px0, py0, z, 0, tilt, -azimuth)
        f0 = robotmath.xyz_euler_to_frame(px0, py0, clearance, 0, tilt, -azimuth)
        f1 = robotmath.xyz_euler_to_frame(px1, py1, clearance, 0, tilt, -azimuth)
        f2 = robotmath.xyz_euler_to_frame(px2, py2, clearance, 0, tilt, -azimuth)

        fe = robotmath.xyz_euler_to_frame(pxe, pye, clearance, 0, tilt, -azimuth)
        fe_up = robotmath.xyz_euler_to_frame(pxe, pye, z, 0, tilt, -azimuth)

        degrees = 360 * n

        prg = self.robot.program

        kinematic_name = self.robot.default_kinematic_name if tool_name is None else tool_name
        tool_frame = self.robot.tool_frame(kinematic_name)

        prg.begin(ctx=self, toolframe=tool_frame, kinematic_name=kinematic_name)

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        p1 = prg.line(f0_up, f0)
        p2 = prg.arc(f0, f1, f2, degrees)
        p3 = prg.line(fe, fe_up)

        prg.move([p1, p2, p3])

        prg.run()

    @json_out
    def put_multiswipe(self, x1: float, y1: float, x2: float, y2: float, z: float = None,
                       tilt: float = 0, azimuth: float = 0, clearance: float = 0, n: float = 2):
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
        """

        log.info("put_multiswipe x1={} y1={} x2={} y2={} z={} tilt={} azimuth={} clearance={} n={}".format(
            x1, y1, x2, y2, z, tilt, azimuth, clearance, n))

        self.multiswipe(x1, y1, x2, y2, z, tilt, azimuth, clearance, n)

        return "ok"

    def multiswipe(self, x1: float, y1: float, x2: float, y2: float, z: float = None,
                       tilt: float = 0, azimuth: float = 0, clearance: float = 0, n: float = 2, tool_name=None):
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
        :param tool_name: Name of tool to perform multiswipe with. If None, default tool is used.
        """

        assert self.parent.base_distance is not None, "DUT base distance not set"

        z = self.parent.base_distance if z is None else z

        n = int(n)
        if n < 1:
            return "NOK: n must be at least 1"

        drag_start_up = robotmath.xyz_euler_to_frame(x1, y1, z, 0, tilt, -azimuth)
        drag_start_down = robotmath.xyz_euler_to_frame(x1, y1, clearance, 0, tilt, -azimuth)
        drag_end_up = robotmath.xyz_euler_to_frame(x2, y2, z, 0, tilt, -azimuth)
        drag_end_down = robotmath.xyz_euler_to_frame(x2, y2, clearance, 0, tilt, -azimuth)

        prg = self.robot.program

        kinematic_name = self.robot.default_kinematic_name if tool_name is None else tool_name
        tool_frame = self.robot.tool_frame(kinematic_name)

        prg.begin(ctx=self, toolframe=tool_frame, kinematic_name=kinematic_name)

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        gestures = []

        gestures.append(prg.line(drag_start_up, drag_start_down))
        for i in range(n):
            if (i & 1) == 0:
                gestures.append(prg.line(drag_start_down, drag_end_down))
            else:
                gestures.append(prg.line(drag_end_down, drag_start_down))

        if (n & 1) == 1:
            gestures.append(prg.line(drag_end_down, drag_end_up))
        else:
            gestures.append(prg.line(drag_start_down, drag_start_up))

        prg.move(gestures)

        prg.run()

    def path(self, points, clearance=0, tool_name=None):
        """
        Performs path movement through given points.

        :param points: List of points to go through.
        :param clearance: Clearance added to z value of each point.
        :param tool_name: Name of tool to perform path with. If None, default tool is used.
        """
        frames = []
        for pose in points:
            x, y, z = [float(pose[v]) for v in ['x', 'y', 'z']]
            tilt = pose['tilt'] if 'tilt' in pose and pose['tilt'] is not None else 0
            azimuth = pose['azimuth'] if 'azimuth' in pose and pose['azimuth'] is not None else 0

            frame = robotmath.xyz_euler_to_frame(x, y, z + clearance, 0, tilt, -azimuth)
            frames.append(frame)

        prg = self.robot.program

        kinematic_name = self.robot.default_kinematic_name if tool_name is None else tool_name
        tool_frame = self.robot.tool_frame(kinematic_name)

        prg.begin(ctx=self, toolframe=tool_frame, kinematic_name=kinematic_name)

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        lines = []
        if len(frames) == 1:
            f0 = frames[0]
            single_point = prg.point(f0)
            prg.move(single_point)
        else:
            for i in range(len(frames) - 1):
                f0 = frames[i]
                f1 = frames[i + 1]
                line = prg.line(f0, f1)
                lines.append(line)
            prg.move(lines)

        prg.run()

    def smooth_path(self, points, clearance=0):
        """
        Performs smooth path movement through given points.

        :param points: List of points to go through.
        :param clearance: Clearance added to z value of each point.
        """
        frames = []
        for pose in points:
            x, y, z = [float(pose[v]) for v in ['x', 'y', 'z']]
            tilt = pose['tilt'] if 'tilt' in pose and pose['tilt'] is not None else 0
            azimuth = pose['azimuth'] if 'azimuth' in pose and pose['azimuth'] is not None else 0

            frame = robotmath.xyz_euler_to_frame(x, y, z + clearance, 0, tilt, -azimuth)
            frames.append(frame)

        prg = self.robot.program

        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        spline_limits = {"x": (0, self.object_parent.width), "y": (0, self.object_parent.height),
                         "z": (clearance, 1e6)}
        lines = []
        if len(frames) == 1:
            f0 = frames[0]
            single_point = prg.point(f0)
            prg.move(single_point)
        else:
            line = prg.spline(frames, spline_limits)
            lines.append(line)
            prg.move(lines)

        prg.run()

    @json_out
    def put_multi_tap(self, points, lift=2, clearance=0):
        """
        Performs multiple tap gestures in DUT context according to given points.
        Start and end of multi-tap sequence is the base distance of the DUT.

        :param points: List of TnTDUTPoint objects indicating where to tap. Z coordinates of the points
                       are ignored and lift and clearance are used for tap movement.
        :param lift: Distance of how high the effector is raised from the DUT between the taps.
        :param clearance: Z coordinate on DUT on tap down (default: 0).
        """

        assert self.parent.base_distance is not None, "DUT base distance not set"

        base_distance = self.parent.base_distance

        # Make one path

        poselist = [{
            "x": points[0]["x"],
            "y": points[0]["y"],
            "z": base_distance  # safe approach height
        }]

        for p in points:
            poselist += [{
                "x": p["x"],
                "y": p["y"],
                "z": lift
            }, {
                "x": p["x"],
                "y": p["y"],
                "z": clearance
            }, {
                "x": p["x"],
                "y": p["y"],
                "z": lift,
            }]

        poselist += [{
            "x": points[-1]["x"],
            "y": points[-1]["y"],
            "z": base_distance  # safe height
        }]

        self.path(poselist)

    @json_out
    def put_path(self, points, clearance=0):
        """
        Performs path movement through given points.

        :param points: List of points to go through.
        :param clearance: Clearance added to z value of each point.
        """

        log.info("put_path points={} clearance={}".format(points, clearance))


        self.path(points, clearance)

        return "ok"

    @json_out
    def put_smooth_path(self, points, clearance=0):
        """
        Performs continuous movement along a cubic spline path that interpolates the given points.

        Notice that the points should constitute a rather dense sampling of a low-curvature path.
        If the curvature is too high the robot acceleration at those parts might not be sufficient for the
        accurate execution of the path positions. Individual joints may also fail due to over-current error.
        The velocity along the path is planned to match the currently set robot velocity but the velocity
        in conjunction with spline curvature affect the resulting robot joint accelerations.

        Warning:
        Notice that due to the behavior of splines, the robot may travel outside of DUT extents even if
        all the given discrete points are within the DUT extents.

        :param points: List of points to go through.
        :param clearance: Clearance added to z value of each point.
        """

        log.info("put_smooth_path points={}".format(points))

        self.smooth_path(points, clearance)
        return "ok"

    @staticmethod
    def _to_gesture_frames(robot_to_dut, poses):
        e = collections.OrderedDict([
                ('x', []),
                ("y", []),
                ("z", []),
                ("x_roll", []),
                ("y_roll", []),
                ("z_roll", [])
        ])
        r = collections.OrderedDict([("effective", e)])
        for pose in poses:
            frame = robot_to_dut * pose

            x, y, z, a, b, c = robotmath.frame_to_xyz_euler(frame)

            e["x"].append(x)
            e["y"].append(y)
            e["z"].append(z)
            e["x_roll"].append(a)
            e["y_roll"].append(b)
            e["z_roll"].append(c)
        return r

    @json_out
    def put_scan(self, x1: float, y1: float, x2: float, y2, z: float = None):
        """
        Performs a scan with given parameters.

        :param x1: Start x coordinate on DUT.
        :param y1: Start y coordinate on DUT.
        :param x2: End x coordinate on DUT.
        :param y2: End y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        """

        raise NotImplemented

    @json_out
    def put_pose(self, pose):
        """
        Moves to a pose at DUT coordinates.

        :param pose: pose in DUT coordinates.
        """
        f0 = np.matrix(pose)

        log.info("put_pose {}".format(robotmath.frame_to_xyz_abc_string(f0)))

        prg = self.robot.program

        prg.begin(ctx=self, toolframe=self.robot.tool_frame(self.robot.default_kinematic_name),
                  kinematic_name=self.robot.default_kinematic_name)

        prg.set_speed(self.robot.robot_velocity, self.robot.robot_acceleration)

        p0 = prg.point(f0)
        prg.move(p0)

        prg.run()

        return "ok"

    # program tries if surface is found in target context
    # here in gestures we use a lot of "self" as context
    @property
    @private
    def surface(self):
        return self.parent.surface
