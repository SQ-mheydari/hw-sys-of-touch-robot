import math
import logging

import numpy as np
from scipy.interpolate import UnivariateSpline
from scipy.integrate import romberg
from scipy.optimize import fsolve

from tntserver.Nodes.Node import Node
import tntserver.robotmath as robotmath
from tntserver.robotmath import frame_to_debug_str
import transformations as tr
from .goldenmov.kinematics import RobotKinematics
from .goldenmov import SAMPLES_PER_SECOND, TIME_STEP, create_track, calculate_track_duration
import time

log = logging.getLogger(__name__)


class Primitive:
    def __init__(self):
        self._positions = None
        self._speed = None
        self._acceleration = None

        # Program that primitive is part of.
        self.program = None

    def length(self):
        return 0

    def append_to_path(self, path: list):
        return []

    def set_positions(self, positions):
        self._positions = positions

    def set_speed_acceleration(self, speed, acceleration):
        self._speed = speed
        self._acceleration = acceleration


class LinePrimitive(Primitive):
    def __init__(self, f0, f1, axes=None):
        super().__init__()
        self._f0 = f0
        self._f1 = f1

        # Axes is dict of form {"separation": [s0, s1], "voicecoil1": [vc0, vc1]}.
        self._axes = axes

    def length(self):
        p0 = self._f0.A[0:3, 3]
        p1 = self._f1.A[0:3, 3]
        length = np.linalg.norm(p1-p0)

        #
        # Choose the longer route
        # either line length from p0 to p1
        # or imaginary angle rotation length
        # for the robot might rotate without moving the tip
        #

        # angle "travel lengths"
        a0 = tr.euler_from_matrix(self._f0)
        a1 = tr.euler_from_matrix(self._f1)

        a0 = np.array(a0)
        a1 = np.array(a1)

        a_lengths = a1 - a0

        # now use signed bit magic to handle angle rolling

        # convert to 16 bit angles
        a_lengths = [int(a / math.pi * 0x8000) for a in a_lengths]

        # to signed 16 bit angles
        a_lengths = [((a + 0x8000) & 0xffff) - 0x8000 for a in a_lengths]

        # to angle degrees
        a_lengths = [a * 180 / 0x8000 for a in a_lengths]

        a_lengths = np.array(a_lengths)

        arc_r = self.program.arc_r()

        a_lengths = np.array([abs(a) for a in a_lengths])
        a_maxlen = np.max(a_lengths)

        # maximum length in angle degrees -> maximum travel distance mm
        a_maxlen = arc_r * 2 * np.pi / 360 * a_maxlen

        log.debug("Line length: {:.3f}, rotation length: {:.3f}".format(length, a_maxlen))
        if a_maxlen > length:
            length = a_maxlen

        if self._axes is not None:
            for axis, axis_limits in self._axes.items():
                axis_length = abs(axis_limits[1] - axis_limits[0])

                length = max(length, axis_length)

        return length

    def append_to_path(self, path: list):
        length = self.length()

        if length == 0:
            # If line end positions coincide, add only one position.
            pos = self.program.create_robot_position(frame=self._f0, d=0, t=0)

            # Set first limit of axis positions. The first and last limit are the same in case length is zero.
            if self._axes is not None:
                for axis, axis_limits in self._axes.items():
                    setattr(pos, axis, axis_limits[0])

            path.append(pos)

            return

        d0 = path[-1].d if len(path) > 0 and path[-1].d is not None else 0
        t0 = path[-1].t + TIME_STEP if len(path) > 0 and path[-1].t is not None else 0

        positions = self._positions
        if positions is None:
            positions = create_track(self._speed, self._acceleration, length)

        p0 = self._f0.A[0:3, 3]
        p1 = self._f1.A[0:3, 3]

        q0 = robotmath.quaternion_from_matrix(self._f0.A[0:3, 0:3])
        q1 = robotmath.quaternion_from_matrix(self._f1.A[0:3, 0:3])

        pd = (p1-p0)

        for d, t in positions:
            # TODO: It seems that d can be one step short from length so that target is never fully reached.
            i = d / length
            p_t = p0 + pd * i
            q_t = tr.quaternion_slerp(q0, q1, i)
            m_t = tr.quaternion_matrix(q_t)
            m_t[0:3, 3] = p_t

            p = self.program.create_robot_position(frame=np.matrix(m_t), d=d + d0, t=t0)

            if self._axes is not None:
                for axis, axis_limits in self._axes.items():
                    axis_pos = axis_limits[0] * (1 - i) + axis_limits[1] * i
                    setattr(p, axis, axis_pos)

            path.append(p)

            t0 += TIME_STEP


def get_segment_ix(position, num_segments, total_length):
    """
    Get index of segment in a sequence of adjacent segments.
    :param position: Position in range [0, total_length].
    :param num_segments: Number of segments.
    :param total_length: Sum of segment lengths.
    :return: Index of segment.
    """
    ix = math.floor(position / total_length * num_segments)

    return int(np.clip(ix, 0, num_segments - 1))


def compute_segment_coordinate(position, segment_ix, segment_lengths):
    """
    Compute normalized segment coordinate of current position.
    :param position: Position in range [0, sum(segment_lengths)].
    :param segment_ix: Segment index in range [0, len(segment_lengths) - 1].
    :param segment_lengths: List of segment lengths.
    :return: Coordinate in given segment in range [0, 1].
    """
    length_to_current_segment = sum(segment_lengths[:segment_ix])

    coord = (position - length_to_current_segment) / segment_lengths[segment_ix]

    return np.clip(coord, 0.0, 1.0)


class SplinePrimitive(Primitive):
    """
    Primitive to plan spline path trajectory.
    The trajectory positions interpolate a series of given discrete XYZ positions.
    The velocity is planned to match the given robot velocity in workspace along the path.
    Acceleration is planned so that it matches in the spline parameter space the given robot acceleration
    but in the workspace it may vary depending on the curvature of the spline. User should avoid using high
    robot acceleration with highly curved paths.
    """
    def __init__(self, frames: list, limits):
        super().__init__()
        self._frames = frames
        self._limits = limits

        # Create uniform sampling in range [0, 1]. This defines the spline parameter space which is arbitrary.
        uniform_sampling = np.linspace(0, 1, len(self._frames))

        # Construct arrays of x, y, and z coordinates of path points that are interpolated by spline.
        x_positions = np.array([f.A1[3] for f in self._frames])
        y_positions = np.array([f.A1[7] for f in self._frames])
        z_positions = np.array([f.A1[11] for f in self._frames])

        # By default use 3rd degree spline.
        degree = 3

        # Use lower degree spline if there is not enough points to determine all spline coefficients.
        if len(frames) < 2:
            raise Exception("Spline primitive must have at least 2 frames!")
        if len(frames) == 2:
            degree = 1
        elif len(frames) == 3:
            degree = 2

        # Create spline interpolation functions.
        self.x_spline = UnivariateSpline(uniform_sampling, x_positions, s=0, k=degree)
        self.y_spline = UnivariateSpline(uniform_sampling, y_positions, s=0, k=degree)
        self.z_spline = UnivariateSpline(uniform_sampling, z_positions, s=0, k=degree)

        # Create spline derivate interpolation functions.
        self.spline_dx = self.x_spline.derivative()
        self.spline_dy = self.y_spline.derivative()
        self.spline_dz = self.z_spline.derivative()

        # Compute orientation quaternion for each frame.
        self.orientations = [robotmath.quaternion_from_matrix(frame.A[0:3, 0:3]) for frame in frames]

    def tangent_length(self, s):
        """
        Calculate spline tangent vector length at given spline paramater.
        :param s: Spline parameter in range [0, 1]
        :return: Tangent vector length.
        """
        return np.sqrt(self.spline_dx(s) ** 2 + self.spline_dy(s) ** 2 + self.spline_dz(s) ** 2)

    def length(self):
        """
        Calculate the length of the spline curve in mm.
        :return: Length in mm.
        """
        return self.segment_length(0, 1)

    def segment_length(self, u0, u1):
        """
        Compute the length of a spline segment in mm.
        :param u0: Spline coordinate of segment start point in range [0, 1].
        :param u1: Spline coordinate of segment end point in range [0, 1].
        :return: Length in mm.
        """
        return romberg(self.tangent_length, u0, u1)

    def get_u_at_distance(self, distance, u0, distance0):
        """
        Get spline parameter u at given distance along the spline curve measured from given start distance.
        This is used to construct arc-length parametrized spline.
        Parameters u0 and distance0 are used to speed up evaluation of adjacent partial distances.
        :param distance: Distance along the spline curve where to determine corresponding spline parameter.
        :param u0: Spline curve parameter corresponding to distance0.
        :param distance0: Distance along the spline measured from the start.
        :return: Spline parameter at given distance.
        """
        # Function whose root to find. Integrate curve distance until it equals given distance.
        lenfunc = lambda u: romberg(self.tangent_length, u0, u0 + u) + distance0 - distance

        result = fsolve(lenfunc, 0)

        return result[0] + u0

    def append_to_path(self, path: list):
        start_time = time.time()

        d0 = path[-1].d if len(path) > 0 and path[-1].d is not None else 0
        t0 = path[-1].t + TIME_STEP if len(path) > 0 and path[-1].t is not None else 0

        track_pos, t = zip(*create_track(self._speed, self._acceleration, self.length()))
        track_pos = np.array(track_pos)

        # Keep track of spline parameter and corresponding distance.
        spline_u = 0.0
        spline_distance = 0.0

        # Collect interpolated XYZ positions for inspection.
        positions = np.zeros((len(track_pos), 3))

        num_segments = len(self._frames) - 1

        # Compute the path length of each segment that is delimited by the discrete points.
        segment_lengths = [self.segment_length(i / num_segments, (i + 1) / num_segments) for i in range(num_segments)]

        for i in range(len(track_pos)):
            # Determine spline parameter at track_pos[i].
            spline_u = self.get_u_at_distance(track_pos[i], spline_u, spline_distance)
            spline_distance = track_pos[i]

            # Evaluate splines.
            pos_x = self.x_spline(spline_u)
            pos_y = self.y_spline(spline_u)
            pos_z = self.z_spline(spline_u)

            positions[i, :] = [pos_x, pos_y, pos_z]

            # Determine the segment that we are currently in the spline parameter space.
            segment_ix = get_segment_ix(spline_u, num_segments, 1.0)

            # Compute interpolation parameter in current segment from the start point of the segment to the end point.
            # interp_param is in range [0, 1].
            interp_param = compute_segment_coordinate(track_pos[i], segment_ix, segment_lengths)

            # Interpolate orientation between the endpoints of current segment.
            q_t = tr.quaternion_slerp(self.orientations[segment_ix], self.orientations[segment_ix + 1], interp_param)
            m_t = tr.quaternion_matrix(q_t)

            # Set translation.
            m_t[0:3, 3] = [pos_x, pos_y, pos_z]

            p = self.program.create_robot_position(frame=np.matrix(m_t), d=track_pos[i] + d0, t=t0)
            path.append(p)
            t0 += TIME_STEP

        log.debug("Spline evaluation time: {}".format(time.time() - start_time))

        limit_checks = [np.min(positions[:, 0]) < self._limits["x"][0],
                        np.max(positions[:, 0]) > self._limits["x"][1],
                        np.min(positions[:, 1]) < self._limits["y"][0],
                        np.max(positions[:, 1]) > self._limits["y"][1],
                        np.min(positions[:, 2]) < self._limits["z"][0],
                        np.max(positions[:, 2]) > self._limits["z"][1]]
        if any(limit_checks):
            limit_idx = int(np.argmax(limit_checks))  # first occurrence of True
            axes = ["x", "x", "y", "y", "z", "z"]
            limit_dir = ["minimum", "maximum", "minimum", "maximum", "minimum", "maximum"]
            raise Exception("Computed spline path will exceed DUT active area. Spline path exceeds {} DUT {} "
                            "coordinate value. Aborting gesture.".format(limit_dir[limit_idx], axes[limit_idx]))

        # Uncomment to plot the path for debugging purposes.
        """
        def plot_path():
            speeds = np.diff(positions, axis=0) * 250
            accels = np.diff(speeds, axis=0) * 250

            fig = plt.figure()
            ax = fig.add_subplot(311, projection='3d')
            ax.plot(positions[:,0], positions[:,1], positions[:,2])
            ax = fig.add_subplot(312)
            ax.plot(track_pos[:-1], np.linalg.norm(speeds, axis=1))
            plt.xlabel('Curve position (mm)')
            plt.ylabel("Speed (mm/s)")
            ax = fig.add_subplot(313)
            ax.plot(track_pos[:-2], np.linalg.norm(accels, axis=1))
            plt.xlabel('Curve position (mm)')
            plt.ylabel("Acceleration (mm/s^2)")
            plt.show()

        plot_path()
        """


class ArcPrimitive(Primitive):
    def __init__(self, f0, f1, f2, degrees=0, separation=None):
        """

        :param f0: first 4x4 matrix frame on arc travel
        :param f1: second 4x4 matrix frame on arc travel
        :param f2: third 4x4 matrix frame on arc travel
        :param degrees: travel this many degrees on arc path from a0. If 0 then travel from f0 to f2 through f1.
        :param separation: Separation to set for each appended position. If None then no separation is set.
        """
        super().__init__()

        # matrix to rotate points to and from x/y plane ( z==0 for each point )
        p0, p1, p2 = robotmath.frame_to_xyz(f0), robotmath.frame_to_xyz(f1), robotmath.frame_to_xyz(f2)
        plane_i = robotmath.three_point_frame(p0, p1, p2)
        plane = plane_i.I

        # rotate points to x/y plane
        fp0, fp1, fp2 = plane * f0, plane * f1, plane * f2
        pp0, pp1, pp2 = robotmath.frame_to_xyz(fp0), robotmath.frame_to_xyz(fp1), robotmath.frame_to_xyz(fp2)

        # calculate mid point of the circle
        mx, my = self.arc_mid_2d(pp0, pp1, pp2)

        # angles for p0, p2
        a0 = math.atan2(pp0[1] - my, pp0[0] - mx)
        a2 = math.atan2(pp2[1] - my, pp2[0] - mx)
        arc_len_radians = math.fabs(a2 - a0)
        if degrees:
            arc_len_radians = math.radians(degrees)

        arc_radius = math.sqrt((pp0[0] - mx) ** 2 + (pp0[1] - my) ** 2)

        circle_len_mm = 2 * math.pi * arc_radius
        arc_len_mm = arc_len_radians / math.pi / 2 * circle_len_mm

        self.arc_len_mm = arc_len_mm
        self.angles = a0, a2
        self.radius = arc_radius
        self.arc_mid = mx, my
        # self.rodriquez = u, phi
        self.q0 = robotmath.quaternion_from_matrix(f0.A[0:3, 0:3])
        self.q2 = robotmath.quaternion_from_matrix(f2.A[0:3, 0:3])
        self.plane = plane
        self.start_rotation = self.rotm(f0)
        self.f_end = f2
        self.degrees = degrees
        self.separation = separation

    def length(self):
        return self.arc_len_mm

    def append_to_path(self, path: list):
        d0 = path[-1].d if len(path) > 0 and path[-1].d is not None else 0
        t0 = path[-1].t + TIME_STEP if len(path) > 0 and path[-1].t is not None else 0

        positions = self._positions
        if positions is None:
            positions = create_track(self._speed, self._acceleration, self.length())

        a0, a1 = self.angles
        arc_radius = self.radius
        mx, my = self.arc_mid
        plane, plane_i = self.plane, self.plane.I

        distance = self.arc_len_mm

        # draw the arc on x/y plane
        frames = []

        for d, t in positions:

            # TODO: t is overridden here
            # current rotation matrix
            t = d / distance
            q = tr.quaternion_slerp(self.q0, self.q2, t)
            rm = tr.quaternion_matrix(q)

            # current location matrix
            angle = d / self.radius + a0
            x = mx + arc_radius * math.cos(angle)
            y = my + arc_radius * math.sin(angle)
            pm = np.eye(4)
            pm[0, 3] = x
            pm[1, 3] = y
            frame = np.matrix(pm)

            # transform location matrix to arc plane
            frame = plane_i * frame

            # append current rotation
            frame.A[0:3, 0:3] = rm[0:3, 0:3]

            if self.separation is not None:
                p = self.program.create_robot_position(frame=frame, d=d + d0, t=t0, separation=self.separation)
            else:
                p = self.program.create_robot_position(frame=frame, d=d + d0, t=t0)

            frames.append(p)

            t0 += TIME_STEP

        path += frames

    def rotm(self, frame):
        return np.matrix(frame.A[0:3, 0:3])

    def arc_mid_2d(self, p0, p1, p2):
        """

        :param p0: first point on arc
        :param p1: mid point on arc
        :param p2: last point on arc
        :return: x, y of the arc center point
        """

        # three points form two lines
        # from the middle of the two lines draw normals
        # the center point is at the intersection of the two lines
        x1 = p0[0]
        y1 = p0[1]
        x2 = p1[0]
        y2 = p1[1]
        x3 = x2
        y3 = y2
        x4 = p2[0]
        y4 = p2[1]

        dx1 = (x2 - x1)
        dy1 = (y2 - y1)
        dx2 = (x4 - x3)
        dy2 = (y4 - y3)

        mx1 = 0.5 * (x1 + x2)
        my1 = 0.5 * (y1 + y2)
        mx2 = 0.5 * (x3 + x4)
        my2 = 0.5 * (y3 + y4)

        x1 = mx1
        y1 = my1
        x2 = x1 - dy1
        y2 = y1 + dx1

        x3 = mx2
        y3 = my2
        x4 = x3 - dy2
        y4 = y3 + dx2

        # https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection
        d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / d
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / d
        return px, py


class PausePrimitive(Primitive):
    """
    Pauses robot movement for a specified time
    """
    def __init__(self, seconds:float):
        super().__init__()
        self._seconds = seconds

    def length(self):
        return 0

    def append_to_path(self, path:list):
        # In case of exactly zero duration, don't append any points.
        if self._seconds == 0:
            return

        # how many copies of latest path position are appended to path
        n = max([int(self._seconds * SAMPLES_PER_SECOND), 1])

        d0 = path[-1].d if len(path) > 0 and path[-1].d is not None else 0
        t0 = path[-1].t + TIME_STEP if len(path) > 0 and path[-1].t is not None else 0

        # if last position of path does not exist, get robot current position
        position = path[-1] if len(path) > 0 else self.program.position()

        for _ in range(n):
            p = position.copy()
            p.t = t0
            p.d = d0
            path.append(p)

            t0 += TIME_STEP


class JoinPrimitive(Primitive):
    def __init__(self, primitives:list, joinSeconds:float):
        super().__init__()
        self._primitives = primitives
        self._joinSeconds = joinSeconds  # TODO: Seems to be unused.

    def length(self):
        l = 0
        for p in self._primitives:
            p.program = self.program
            l += p.length()
        return l

    def append_to_path(self, path:list):
        # Create track that is split for each primitive.
        track = create_track(self._speed, self._acceleration, self.length())

        # Index to track list where primitive starts using track points.
        track_ix = 0

        # Total distance traveled along the track.
        travel = 0

        # Loop through each primitive and assign corresponding segment from track.
        for primitive in self._primitives:
            primitive.program = self.program
            primitive_length = primitive.length()

            primitive_positions = []

            for i in range(track_ix, len(track)):
                d, t = track[i]

                # Offset track position for current primitive so that its track positions add up to its length.
                d -= travel

                # When primitive length is exceeded, change to next primitive.
                if d > primitive_length:
                    track_ix = i
                    break

                primitive_positions.append((d, t))

            primitive.set_positions(primitive_positions)

            primitive.append_to_path(path)
            travel += primitive_length


class PointPrimitive(Primitive):
    def __init__(self, f0):
        super().__init__()
        self._f0 = f0

    def append_to_path(self, path:list):
        # if first primitive on path, it is okay to just add this position
        if len(path) == 0:
            path.append(self.program.create_robot_position(frame=self._f0, d=0, t=0))
        else:
            # otherwise a line must be created
            # TODO: The frame path[-1].frame will occur as duplicate in the path. Is this a problem?
            p = LinePrimitive(path[-1].frame, self._f0)
            p.program = self.program
            p.set_speed_acceleration(self.program.speed, self.program.acceleration)
            p.append_to_path(path)


def _get_swipe_points(f0, f1, r):
    p0 = f0[0:3, 3]
    p1 = f1[0:3, 3]
    d = (p1-p0)
    if not np.allclose(d, 0.0):
        d /= np.linalg.norm(d)
    else:
        raise Exception("Planned swipe gesture has zero length. Please adjust swipe parameters and retry.")

    # start arc through pf0, pf1, pf2
    pf0 = f0.copy()
    pf1 = f0.copy()
    pf2 = f0

    # line through pf2 -> pf3

    # end arc through pf3, pf4, pf5
    pf3 = f1
    pf4 = f1.copy()
    pf5 = f1.copy()

    pf0[0:3, 3] -= d * r
    pf0[2, 3] += r  # positive UP

    # arc mid point at 45 degrees
    m_mid = math.cos(math.radians(45))
    pf1[0:3, 3] -= d * (r * m_mid)
    pf1[2, 3] += r * (1-m_mid)

    pf4[0:3, 3] += d * (r * m_mid)
    pf4[2, 3] += r * (1-m_mid)

    pf5[0:3, 3] += d * r
    pf5[2, 3] += r  # positive UP

    return pf0, pf1, pf2, pf3, pf4, pf5


def create_swipe_primitive(f0, f1, r): 
    pf0, pf1, pf2, pf3, pf4, pf5 = _get_swipe_points(f0, f1, r)

    p0 = ArcPrimitive(pf0, pf1, pf2)
    p1 = LinePrimitive(pf2, pf3)
    p2 = ArcPrimitive(pf3, pf4, pf5)

    pj = JoinPrimitive([p0, p1, p2], 0.01)
    return pj, pf0


class KeyFrameAxisPrimitive(Primitive):
    """
    Primitive to run motion where axis movements are glued to existing motion using temporal or spatial keys.
    """
    def __init__(self, name: str, key_positions: list=None, key_times: list=None):
        """
        :param name: Name of the axis to move.
        :param key_positions: List of positions where to apply the predefined movement (optional).
        :param key_times: List of times where to apply the predefined movement (optional).
        """

        super().__init__()
        self._axis_name = name
        self._key_positions = key_positions
        self._key_times = key_times
        self._axis_positions = []

    def length(self):
        # needs a ready-made path to join to
        return 0

    @property
    def duration(self):
        """
        Duration of the primitive in seconds.
        """
        return len(self._axis_positions) * TIME_STEP

    def append_to_path(self, path: list):
        """
        Joins axis motion to existing path at keyed times or positions.
        :param path: Path to append to.
        """

        # Modify existing path by adding predefined axis values to positions of time or location
        l = len(path)

        # if key positions are defined, add to predefined track locations
        if self._key_positions is not None:
            for pp in self._key_positions:
                for i in range(l):
                    if path[i].d >= pp:
                        # this is the right location
                        # check that we don't write past the given path limits
                        n = len(self._axis_positions)
                        if i + n >= l:
                            n = l - i
                        # and copy predefined axis values to existing path
                        for j in range(n):
                            setattr(path[i + j], self._axis_name, self._axis_positions[j])
                        break

        # if key times are defined, add to predefined track time locations
        if self._key_times is not None:
            for tt in self._key_times:
                for i in range(l):
                    if path[i].t >= tt:
                        # this is the right location in time
                        # check that we don't write past the given path limits
                        n = len(self._axis_positions)
                        if i + n >= l:
                            n = l - i
                        # and copy predefined axis values to existing path
                        for j in range(n):
                            setattr(path[i + j], self._axis_name, self._axis_positions[j])
                        break

    def plan_tap(self, length, speed, acceleration, duration=0):
        """
        Plan a predefined axis movement: tap
        this movement is appended or joined to existing path in 'append_to_path'
        when this Primitive is run in program.
        :param length: movement length in one direction, mm
        :param speed: axis speed
        :param acceleration: axis acceleration
        :param duration: Tap duration.
        """
        # use same track mirrored to get up & down movements
        track = create_track(speed, acceleration, length)
        pause_positions = [track[-1]] * int(round((SAMPLES_PER_SECOND * duration)))
        z_positions = track + pause_positions + track[::-1]
        path = [z for z, t in z_positions]
        self._axis_positions = path


class AxisPrimitive(Primitive):
    """
    Primitive to run single axis only.
    """
    def __init__(self, name: str):
        """
        :param name: Name of the axis to move.
        """

        super().__init__()
        self._axis_name = name
        self.target_value = None
        self.speed_override = None
        self.acceleration_override = None

    def length(self):
        # needs a ready-made path to join to
        return 0

    def append_to_path(self, path: list):
        """
        Appends axis motion to path.
        :param path: Path to append to.
        """

        # Create a piece of new path instead of joining to existing path
        # Here we will have self.target_value to interpolate to

        # we need current axis position for interpolation
        # from the existing path or from driver otherwise
        position = path[-1] if len(path) > 0 else self.program.position()
        t0 = path[-1].t if len(path) > 0 and path[-1].t is not None else 0
        d0 = path[-1].d if len(path) > 0 and path[-1].d is not None else 0

        current_value = getattr(position, self._axis_name)
        if current_value is None:
            p_temp = self.program.position()
            current_value = getattr(p_temp, self._axis_name)

        # calculate distance and direction
        # create track with stored speed and acceleration
        l = abs(self.target_value - current_value)
        if l == 0:
            track = []
        else:
            direction = (self.target_value - current_value) / l
            speed = self._speed if self.speed_override is None else self.speed_override
            acceleration = self._acceleration if self.acceleration_override is None else self.acceleration_override
            track = create_track(speed, acceleration, l)

        # append to path creating RobotPosition for each sample on track
        # including axis position, d, t
        last_p = 0
        d = 0
        for p, t in track:
            d = d + np.abs(p - last_p)
            pos = position.copy()
            setattr(pos, self._axis_name, p * direction + current_value)
            pos.t = t + t0
            pos.d = d + d0
            path.append(pos)
            last_p = p


def primitive_axis_movement(axis_name, target, speed=None, acceleration=None):
    p = AxisPrimitive(axis_name)
    p.target_value = target
    p.speed_override = speed
    p.acceleration_override = acceleration

    return p


class ModifyPrimitive(Primitive):
    """
    Simple primitive that can be added in the middle / end of an existing command to modify the path
    """
    def __init__(self, func):
        """
        :param func: function that is used to modify the existing path.
                        should accept one argument: "path"
        """
        super().__init__()
        self._path_func = func

    def length(self):
        # needs a ready-made path to join to
        return 0

    def append_to_path(self, path: list):
        """
        Modify existing path by calling the function that was passed
        """

        self._path_func(path)


class Command:
    def __init__(self):
        # Program that command is part of.
        self.program = None

    def execute(self):
        pass


class PathCommand(Command):
    def __init__(self):
        super().__init__()
        self._primitives = []

    def appendPrimitive(self, p: Primitive):
        self._primitives.append(p)

    def execute(self, *args, **kwargs):
        speed = self.program.speed
        acceleration = self.program.acceleration
        driver = self.program.robot.driver

        # TODO: This is often "unknown" because context is Gestures node. We should use Dut node as context instead.
        context_name = getattr(self.program.context, "name", None) if self.program.context is not None else None

        log.debug("Executing path command (context={}, speed={}, acceleration={})."
                  .format(context_name, speed, acceleration))

        positions = [] # list of RobotPositions in target context

        for primitive in self._primitives:
            primitive.program = self.program
            primitive.set_speed_acceleration(speed, acceleration)
            primitive.append_to_path(positions)

        if len(positions) == 0:
            return

        # Check if transformation local z-vector direction wrt robot base frame is within allowed robot-specific limit
        if np.degrees(tr.angle_between_vectors(self.program.transform.A[:3, 2], np.array([0, 0, 1]))) \
                > self.program.robot.maximum_dut_tilt_angle:
            raise Exception("Planned movement exceeds robot rotation capability. Check movement parameters and / or "
                            "DUT corner point values.")

        # to target context
        for p in positions:
            p.frame = self.program.transform * p.frame

        # create path from current location to start of user path
        # this is in Robot's coordinate system, not in the selected context anymore
        p0, joint_pos = self.program.robot.driver.position(tool=self.program.toolframe,
                                                           kinematic_name=self.program.kinematic_name,
                                                           return_joint_positions=True)

        log.debug("Current position: " + robotmath.frame_to_debug_str(p0.frame))
        log.debug("Current joint positions: %s", joint_pos)

        p1 = positions[0]
        closing_positions = []
        closing_line = LinePrimitive(p0.frame, p1.frame)
        closing_line.program = self.program
        closing_line.set_speed_acceleration(speed, acceleration)
        closing_line.append_to_path(closing_positions)

        # adjust position, time of path to one after closing line
        # here the whole path (closing_line + path from primitives)
        # is made linear by the parameters 't', 'd'

        # Notice: there is absolutely no need for this NOW but maybe later on
        # some extra functions are put between this point and driver.exec_positions and then
        # maybe the timeline and position line must be linear through the whole track.
        # (exec_positions doesn't care about 'd', 't' parameters on path at all)
        if len(closing_positions) > 0:
            d0, t0 = closing_positions[-1].d, closing_positions[-1].t + TIME_STEP
            for p in positions:
                p.d += d0
                p.t += t0

        positions = closing_positions + positions

        log.debug("Destination: " + robotmath.frame_to_debug_str(positions[-1].frame))

        driver.exec_positions(positions, toolframe=self.program.toolframe,
                                         kinematic_name=self.program.kinematic_name)

    def length(self):
        l = 0
        for primitive in self._primitives:
            l += primitive.length()
        return l


class ContextCommand(Command):
    def __init__(self, ctx: Node):
        super().__init__()
        self._ctx = ctx

    def execute(self):
        t = robotmath.translate(robotmath.identity_frame(), self._ctx, self.program.robot_base)
        self.program.context = self._ctx
        self.program.transform = t
        self.program.surface = None

        try:
            if self._ctx.surface is not None:
                self.program.surface = self._ctx.surface
        except AttributeError:
            pass
        except Exception as e:
            log.exception(e)


class SpeedCommand(Command):
    def __init__(self, speed: float, acceleration: float):
        super().__init__()
        self._speed = speed
        self._acceleration = acceleration

    def execute(self):
        self.program.speed = self._speed
        self.program.acceleration = self._acceleration


class Program:
    """
    Connect command primitives to one runnable program.
    Primitives create path with given POSEs
    PathCommand uses these paths and gives robot driver list of FRAMEs to run

    Example:

    prg.begin()
    prg.context("DUT1")
    prg.set_speed(10, 10)
    p1 = prg.line(f0, f1)
    p2 = prg.arc(f1, f2, f3)
    p3 = prg.line(f3, f0)
    prg.move([p1, p2, p3])

    prg.context("DUT2")
    p1 = prg.line(f0, f1)
    p2 = prg.line(f1, f2)
    p3 = prg.line(f2, f3)
    p4 = prg.line(f3, f0)
    p1 = prg.join([p1, p2, p3, p4])
    prg.move(p1)

    start_sampling();
    prg.set_speed(100, 100);
    prg.move(p1)
    end_sampling();
    prg.run()

    """

    def __init__(self, robot):
        self.robot = robot
        self.robot_base = robot.object_parent
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

    def position(self):
        """
        get current position. stored or fresh from the robot.
        :return: current robot position
        """
        position = self.robot.driver.position(kinematic_name=self.kinematic_name, tool=self.toolframe)
        position.frame = robotmath.translate(position.frame, self.robot_base, self.context)
        return position

    def create_robot_position(self, **kwargs):
        return self.robot.driver.create_robot_position(**kwargs)

    def arc_r(self):
        """
        Radius to use when calculating rotation-only motion length
        :return: r
        """
        r = self.robot.driver._kinematics.arc_r(self.toolframe, self.kinematic_name)
        return r

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
            # push state
            tmp_transform = self.transform.copy() if self.transform is not None else None
            tmp_surface = self.surface
            tmp_context = self.context

            try:
                cmd.execute()
            except Exception as e:
                log.exception(e)

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
    def line(self, pose0, pose1, axes=None):
        f0 = robotmath.pose_to_frame(pose0)
        f1 = robotmath.pose_to_frame(pose1)

        p = LinePrimitive(f0, f1, axes=axes)
        p.program = self

        return p

    def spline(self, poses: list, limits):
        p = SplinePrimitive([robotmath.pose_to_frame(pose) for pose in poses], limits)
        p.program = self

        return p

    def arc(self, pose0, pose1, pose2, degrees=0):
        f0 = robotmath.pose_to_frame(pose0)
        f1 = robotmath.pose_to_frame(pose1)
        f2 = robotmath.pose_to_frame(pose2)

        p = ArcPrimitive(f0, f1, f2, degrees)
        p.program = self

        return p

    def swipe(self, pose0, pose1, radius):
        f0 = robotmath.pose_to_frame(pose0)
        f1 = robotmath.pose_to_frame(pose1)
        swipe_primitive, f = create_swipe_primitive(f0, f1, radius)
        swipe_primitive.program = self

        return swipe_primitive

    def point(self, pose):
        frame = robotmath.pose_to_frame(pose)
        p = PointPrimitive(frame)
        p.program = self

        return p

    def join(self, rounding, primitives):
        p = JoinPrimitive(primitives, rounding)
        p.program = self

        return p

    def pause(self, seconds):
        p = PausePrimitive(seconds)
        p.program = self

        return p

    def set_speed(self, speed:float, acceleration:float):
        cmd = SpeedCommand(speed, acceleration)
        cmd.program = self

        self.program.append(cmd)

    def move(self, primitive):
        # TODO: Should probably make sure that begin() has been called.
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
        f1 = f.copy()
        f2 = f.copy()
        f0.A[2, 3] = base_distance
        f1.A[2, 3] = clearance
        f2.A[2, 3] = base_distance

        p1 = self.line(f0, f1)
        p2 = self.pause(duration)
        p3 = self.line(f1, f2)

        return [p1, p2, p3]

    def length(self):
        """
        Calculate total length of current command set
        :return: path length in millimeters
        """
        l = 0
        for cmd in self.program:
            length_function = getattr(cmd, "length", None)
            if length_function is not None and callable(length_function):
                l += length_function()
        return l

