from scipy.interpolate import UnivariateSpline
from scipy.ndimage.filters import median_filter
from scipy.signal import argrelmin
import numpy as np
import math
import logging

log = logging.getLogger(__name__)


def scale_trajectory_time(positions, scale, ts):
    """
    Scale the time-span of trajectory to reduce velocity and acceleration by interpolating more positions
    in between given ones. The inverse of velocity is linearly proportional to scale and inverse of acceleration
    is quadratically proportional to scale.
    Note that the positions themselves don't change, more positions are interpolated in-between
    to increase the time-span of the motion.
    :param positions: List of positions corresponding to evenly spaced steps.
    :param scale: Scaling factor. If scale > 1, velocity and acceleration are reduced.
    :param ts: Time step in seconds.
    :return: Scaled positions.
    """
    num_positions = len(positions)

    # If there are 0 or 1 points, scaling does not apply.
    if num_positions < 2:
        return positions

    # Scale duration. num_positions - 1 is the number of time segments.
    new_time_length = np.ceil(scale * (num_positions - 1)) + 1

    t = np.linspace(0, num_positions * ts, num_positions)
    t_new = np.linspace(0, num_positions * ts, int(new_time_length))

    # Use 3rd degree spline with zero smoothing to interpolate positions.
    # The degree must be at least 2 to correctly interpolate acceleration phases (with constant acceleration) but
    # 3rd degree is probably generally most widely used. In rare cases there can be too few points to enable use
    # of 3rd degree spline. In those cases use a degree that is possible.
    # Smoothing is not used because it can significantly change the velocity profile and does not really
    # seem to have any desirable effect.
    k = min(num_positions - 1, 3)
    sp = UnivariateSpline(t, positions, k=k, s=0)

    return sp(t_new)


def compute_velocity(positions, ts, filter_size=0):
    """
    Compute velocity of trajectory.
    :param positions: List of positions corresponding to evenly spaced steps.
    :param ts: Time step in seconds.
    :param filter_size: Size of median filter in number of samples applied on velocity. Zero means no filtering.
    :return: List of velocities.
    """
    v = np.diff(positions) / ts

    if filter_size > 0:
        v = median_filter(v, size=filter_size)

    return v


def compute_max_abs_velocity(positions, ts, filter_size=0):
    """
    Compute maximum absolute velocity of trajectory.
    :param positions: List of positions corresponding to evenly spaced steps.
    :param ts: Time step in seconds.
    :param filter_size: Size of median filter in number of samples applied on velocity. Zero means no filtering.
    :return: Maximum of absolute velocity values.
    """
    v = compute_velocity(positions, ts, filter_size)

    return np.max(np.abs(v))


def compute_acceleration(positions, ts, filter_size=0):
    """
    Compute acceleration of trajectory.
    :param positions: List of positions corresponding to evenly spaced steps.
    :param ts: Time step in seconds.
    :param filter_size: Size of median filter in number of samples applied on acceleration. Zero means no filtering.
    :return: List of accelerations.
    """
    a = np.diff(positions, n=2) / (ts**2)

    if filter_size > 0:
        a = median_filter(a, size=filter_size)

    return a


def compute_max_abs_acceleration(positions, ts, filter_size=0):
    """
    Compute maximum absolute acceleration of trajectory.
    :param positions: List of positions corresponding to evenly spaced steps.
    :param ts: Time step in seconds.
    :param filter_size: Size of median filter in number of samples applied on acceleration. Zero means no filtering.
    :return: Maximum of absolute acceleration values.
    """
    a = compute_acceleration(positions, ts, filter_size)

    return np.max(np.abs(a))


def compute_total_velocity(axis_positions, ts):
    """
    Compute total velocity in joint space. Notice that this is not the same as effector velocity in the workspace.
    This can be used to find times when joints are at rest by finding the roots of total velocity.
    :param axis_positions: Axis positions as dict {"x": [0, 1, 2], "y": [0, 2, 4]}.
    :param ts: Time step in seconds.
    :return: List of total velocities.
    """
    v_tot = None

    for alias, positions in axis_positions.items():
        v = compute_velocity(positions, ts)

        if v_tot is None:
            v_tot = np.array(v) ** 2
        else:
            v_tot += np.array(v) ** 2

    v_tot = np.sqrt(v_tot)

    return v_tot


def limit_trajectory_speed_and_acceleration(axis_positions, axis_specs, ts):
    """
    Limit trajectory speed and acceleration so that axis performance is respected
    by scaling the time-span of the movement. Scaling factor is chosen according to the most severe violation of
    velocity or acceleration. After scaling there should be no violations. With discontinuous acceleration
    (infinite jerk) however there can be some oscillations in acceleration after the scaling. This
    oscillation occurs at the acceleration discontinuities. This may cause the acceleration limits to be
    momentarily violated by some amount. Hence the limits should be set somewhat smaller than the actual
    HW limits.
    :param axis_positions: Axis positions as dict {"x": [0, 1, 2], "y": [0, 2, 4]}.
    :param axis_specs: Axis specification dict as defines by kinematics.
    :param ts: Time step in seconds.
    :return: Scaled axis positions and dictionary of used scaling factors for velocity and acceleration.
    """
    axis_specs = {s["alias"]: s for _, s in axis_specs.items()}

    k_v = 1.0
    k_a = 1.0

    factors = {alias : {"k_v": 1.0, "k_a": 1.0} for alias in axis_positions.keys()}

    # TODO: Determine zero-velocity positions and perform time scaling individually in segments separated
    # by zero velocity. This would allow e.g. jump gesture to perform xy movement faster than z movements.
    # However detecting zero-velocity positions in robust way requires some amount signal processing.
    #v_tot = compute_total_velocity(axis_positions, ts)

    for alias, positions in axis_positions.items():
        # There must be at least three points in the trajectory to be able to compute velocity and acceleration.
        if len(positions) < 3:
            continue

        axis_spec = axis_specs[alias]

        # Determine velocity scaling factor.
        if "max_velocity" in axis_spec:
            spec_max_v = axis_spec["max_velocity"]

            assert spec_max_v != 0

            max_v = compute_max_abs_velocity(positions, ts)

            if max_v > spec_max_v:
                log.warning("Axis '{}' velocity {} exceed maximum velocity {}.".format(alias, max_v, spec_max_v))

            max_v_ratio = max_v / spec_max_v

            k_v = max(k_v, max_v_ratio)

            factors[alias]["k_v"] = max_v_ratio

        # Determine acceleration scaling factor.
        if "max_acceleration" in axis_spec:
            spec_max_a = axis_spec["max_acceleration"]

            assert spec_max_a != 0

            max_a = compute_max_abs_acceleration(positions, ts)

            if max_a > spec_max_a:
                log.warning("Axis '{}' acceleration {} exceed maximum acceleration {}.".format(alias, max_a, spec_max_a))

            max_a_ratio = max_a / spec_max_a

            k_a = max(k_a, max_a_ratio)

            factors[alias]["k_a"] = max_a_ratio

    # Trajectory velocity scales linearly with k and acceleration scales quadratically with k.
    k = max(1.0, k_v, math.sqrt(k_a))

    # If no scaling is needed, return original positions.
    if k == 1.0:
        return axis_positions, factors

    log.warning("Scaling trajectory time by factor {}.".format(k))

    scaled_axis_positions = {}

    # Scale trajectory time.
    for alias, positions in axis_positions.items():
        scaled_axis_positions[alias] = scale_trajectory_time(positions, k, ts)

    return scaled_axis_positions, factors


def log_trajectory_stats(axis_positions, ts):
    """
    Log trajectory statistics of axes. This is useful in debugging of some axis goes to fault or
    trajectory time scaling does not work as expected.
    :param axis_positions: Axis positions as dict {"x": [0, 1, 2], "y": [0, 2, 4]}.
    :param ts: Time step in seconds.
    """
    for alias, positions in axis_positions.items():
        # There must be at least three points in the trajectory to be able to compute velocity and acceleration.
        if len(positions) < 3:
            log.debug("Axis '{}' has less than 3 points. No stats computed.".format(alias))
            continue

        v = compute_velocity(positions, ts)
        a = compute_acceleration(positions, ts)

        v_max = max(abs(v))
        v_median = np.median(abs(v))
        a_max = max(abs(a))
        a_median = np.median(abs(a))

        if abs(v_max) > 0.1 or abs(v_median) > 0.1 or abs(a_max) > 0.1 or abs(a_median) > 0.1:
            log.debug("Axis '{}' stats: v_max={:.1f}, v_median={:.1f}, a_max={:.1f}, a_median={:.1f}.".
                      format(alias, v_max, v_median, a_max, a_median))
