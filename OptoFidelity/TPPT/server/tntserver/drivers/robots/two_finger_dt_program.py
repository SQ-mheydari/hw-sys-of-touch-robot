"""
Program for controlling two-finger DT robot driver.

Unlike golden program, this program does not generate point lists.
All movements are computed on primitive level.
"""
import logging
import copy
from tntserver.Nodes.Node import Node
import tntserver.robotmath as robotmath
import numpy as np
import time

# Utilize some classes defined by golden program.
# TODO: Perhaps there should be some "common program" that defines reusable classes.
from .golden_program import Command, ContextCommand, SpeedCommand, Primitive

log = logging.getLogger(__name__)


class PausePrimitive(Primitive):
    def __init__(self, seconds: float):
        super().__init__()
        self._seconds = seconds

    def length(self):
        # Temporal pause has zero spatial length.
        return 0

    def execute(self, *args):
        # Just sleep to pause execution.
        # Note: Because this is not part of robot API, pause is not noticed by unit tests.
        time.sleep(self._seconds)


class PointPrimitive(Primitive):
    def __init__(self, f0):
        super().__init__()
        self._f0 = f0

    def execute(self, transform, driver, tool_frame, kinematic_name):
        """
        Execute point primitive on driver.
        :param transform: Transforms point frame to robot/root context.
        :param driver: Should be two-finger DT driver.
        """

        driver.speed = self._speed
        driver.acceleration = self._acceleration

        f0 = robotmath.pose_to_frame(transform * self._f0)

        driver.move(f0, tool_frame, kinematic_name)

    @property
    def start_frame(self):
        return self._f0

    @property
    def end_frame(self):
        return self._f0

class LinePrimitive(Primitive):
    def __init__(self, f0, f1):
        super().__init__()

        self._f0 = f0
        self._f1 = f1

    def execute(self, transform, driver, tool_frame, kinematic_name):
        driver.speed = self._speed
        driver.acceleration = self._acceleration

        f0 = robotmath.pose_to_frame(transform * self._f0)

        driver.move(f0, tool_frame, kinematic_name)

        f1 = robotmath.pose_to_frame(transform * self._f1)

        driver.move(f1, tool_frame, kinematic_name)

    @property
    def start_frame(self):
        return self._f0

    @property
    def end_frame(self):
        return self._f1

class TapPrimitive(Primitive):
    def __init__(self, f, clearance, duration):
        super().__init__()

        self.frame = f
        self.clearance = clearance
        self.duration = duration

    def execute(self, transform, driver, tool_frame, kinematic_name):
        driver.speed = self._speed
        driver.acceleration = self._acceleration

        f0 = robotmath.pose_to_frame(transform * self.frame)

        f1 = self.frame.copy()
        f1.A[2, 3] = self.clearance
        f1 = robotmath.pose_to_frame(transform * f1)

        driver.move(f0, tool_frame, kinematic_name)
        driver.tap(f1, tool_frame, kinematic_name, self.duration)

    @property
    def start_frame(self):
        return self.frame

    @property
    def end_frame(self):
        return self.frame

class SwipePrimitive(Primitive):
    def __init__(self, start, end, radius):
        """
        Swipe primitive.
        :param start: Frame of swipe path start point where robot is at swipe height.
        :param end: Frame of swipe path end point where robot is at swipe height.
        :param radius: Radius of arc where robot accelerates towards start frame and decelerates from end frame.
        """
        super().__init__()

        # Compute swipe line unit vector scaled by radius.
        # This is used to map swipe REST API convention of swipe path to two-finger API convention.
        dir = robotmath.get_frame_translation_vector(end) - robotmath.get_frame_translation_vector(start)
        dir /= np.linalg.norm(dir)
        dir *= radius

        self.start = start.copy()
        t_start = robotmath.get_frame_translation_vector(start)
        t_start += np.matrix([-dir.A1[0], -dir.A1[1], radius])
        robotmath.set_frame_translation_vector(self.start, t_start)

        self.end = end.copy()
        t_end = robotmath.get_frame_translation_vector(end)
        t_end += np.matrix([dir.A1[0], dir.A1[1], radius])
        robotmath.set_frame_translation_vector(self.end, t_end)

        self.radius = radius

    def execute(self, transform, driver, tool_frame, kinematic_name):
        driver.speed = self._speed
        driver.acceleration = self._acceleration

        start = robotmath.pose_to_frame(transform * self.start)
        end = robotmath.pose_to_frame(transform * self.end)

        driver.swipe(start, end, self.radius, tool_frame, kinematic_name)

    @property
    def start_frame(self):
        return self.start

    @property
    def end_frame(self):
        return self.end


class PathCommand(Command):
    def __init__(self):
        super().__init__()
        self._primitives = []

    def appendPrimitive(self, p: Primitive):
        self._primitives.append(p)

    def execute(self, *args, **kwargs):
        program = self.program

        speed = program.speed
        acceleration = program.acceleration
        driver = program.driver
        transform = program.transform

        if len(self._primitives) == 0:
            return

        primitives = copy.copy(self._primitives)

        for primitive in primitives:
            primitive.set_speed_acceleration(speed, acceleration)

        # create path from current location to start of user path
        # this is in Robot's coordinate system, not in the selected context anymore
        f0 = program.driver.frame(program.toolframe, program.kinematic_name)
        f0 = robotmath.frame_to_pose(f0) # Primitives convert pose->frame so f0 needs to be pose.
        f1 = transform * primitives[0].start_frame

        closing_line = LinePrimitive(f0, f1)
        closing_line.set_speed_acceleration(speed, acceleration)
        closing_line.execute(robotmath.identity_frame(), driver, program.toolframe, program.kinematic_name)

        for p in primitives:
            p.execute(transform, driver, program.toolframe, program.kinematic_name)

class Program:
    """
    Connect command primitives to one runnable program.
    Primitives create path with given POSEs
    PathCommand uses these paths and gives robot driver list of FRAMEs to run
    TODO: Refactor to share common functionality with Golden Program.
    """
    def __init__(self, robot_base: Node, driver):
        self.robot_base = robot_base
        self.driver = driver
        self.program = []
        self.transform = robotmath.identity_frame()
        self.surface = None
        self.context = None

        # default values
        self.speed = 100
        self.acceleration = 100

        # tool frame to work with
        self.toolframe = None

        # kinematics to work with
        self.kinematic_name = None

    def reset(self):
        """
        call reset *always* after robot homing etc. that moves robot outside of the program.
        otherwise program will remember where it was before and continue from there
        which is dangerous!
        :return:
        """
        self.program = []
        self.transform = robotmath.identity_frame()
        self.surface = None
        self.context = None
        self.toolframe = None

    def begin(self, ctx: Node, toolframe: np.matrix, kinematic_name: str):
        """
        call this always first before adding primitives to path
        :param ctx: Context for coordinates. Mandatory!
        """
        if ctx is None:
            raise Exception("Program context was None")
        self.program = []
        self.toolframe = toolframe
        self.kinematic_name = kinematic_name
        cmd = ContextCommand(ctx)
        cmd.program = self
        self.program.append(cmd)

    def run(self):
        # transform path with self.transform
        # run path with driver
        for i, cmd in enumerate(self.program):
            log.debug("Program running command {}/{} : {}".format(i+1, len(self.program), str(cmd)))

            # push state
            tmp_transform = self.transform.copy() if self.transform is not None else None
            tmp_surface = self.surface
            tmp_context = self.context

            try:
                cmd.execute()
            except Exception as e:
                log.error("Exception while executing command {}".format(str(cmd)))
                log.error(e)

                # restore state
                self.transform = tmp_transform
                self.surface = tmp_surface
                self.context = tmp_context

                # Raise exception again to be handled by caller.
                raise e

    def clear(self):
        """
        Keep settings but clear the primitives used so far
        """
        self.program.clear()

    #
    # Primitive constructors
    #
    def line(self, f0, f1):
        p = LinePrimitive(f0, f1)
        p.program = self

        return p

    def arc(self, f0, f1, f2, degrees=0):
        raise Exception("Not supported")

    def swipe(self, f0, f1, radius):
        p = SwipePrimitive(f0, f1, radius)
        p.program = self

        return p

    def point(self, f0):
        p = PointPrimitive(f0)
        p.program = self

        return p

    def join(self, rounding, primitives):
        raise Exception("Not supported")

    def pause(self, seconds):
        p = PausePrimitive(seconds)
        p.program = self

        return p

    def set_speed(self, speed:float, acceleration:float):
        cmd = SpeedCommand(speed, acceleration)
        cmd.program = self
        self.program.append(cmd)

    def move(self, primitive):

        cmd = PathCommand()
        cmd.program = self

        if isinstance(primitive, list):
            for p in primitive:
                p.program = self
                cmd.appendPrimitive(p)
        else:
            primitive.program = self
            cmd.appendPrimitive(primitive)
        self.program.append(cmd)

    def tap(self, f, base_distance, clearance, duration):
        f0 = f.copy()
        f0.A[2, 3] = base_distance

        p = TapPrimitive(f0, clearance, duration)
        p.program = self

        return p
