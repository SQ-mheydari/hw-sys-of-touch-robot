from tntserver.drivers.robots.goldenmov import *
from tntserver.drivers.robots.goldenmov.trajectory import *
from tntserver.drivers.robots.golden_program import create_track
import pytest
from scipy.ndimage.filters import median_filter


def create_positions(max_speed, acceleration, distance):
    track = create_track(max_speed, acceleration, distance)
    positions = [p for p, t in track]

    return positions


def test_compute_max_velocity():
    positions = create_positions(max_speed=100, acceleration=400, distance=50)

    v_max = compute_max_abs_velocity(positions, ts=TIME_STEP)

    assert v_max == pytest.approx(100)


def test_compute_max_acceleration():
    positions = create_positions(max_speed=100, acceleration=400, distance=50)

    a_max = compute_max_abs_acceleration(positions, ts=TIME_STEP)

    assert a_max == pytest.approx(400)


def test_scale_trajectory_time():
    speed = 100
    acceleration = 400
    positions = create_positions(max_speed=speed, acceleration=acceleration, distance=50)

    positions = scale_trajectory_time(positions, scale=2.0, ts=TIME_STEP)

    # Uncomment statements below to plot acceleration.
    #a = compute_acceleration(positions, filter_size=10)
    #v = compute_velocity(positions)
    #import matplotlib.pyplot as plt
    #plt.figure(1)
    #plt.plot(np.linspace(0, 1, len(a)), a)
    #plt.show()

    # Use filtering to ignore the effect of oscillations caused by use of discontinuous
    # acceleration in create_track().
    v_max = compute_max_abs_velocity(positions, ts=TIME_STEP, filter_size=50)
    a_max = compute_max_abs_acceleration(positions, ts=TIME_STEP, filter_size=50)

    # Velocity scales linearly with scaling.
    assert v_max == pytest.approx(speed / 2)

    # Acceleration scales quadratically with scaling.
    assert a_max == pytest.approx(acceleration / 4)


def test_limit_trajectory_speed_and_acceleration():
    positions = create_positions(max_speed=150, acceleration=1500, distance=50)

    # Create trajectory where y-axis is 2x faster than x-axis.
    axis_positions = {
        "x": positions,
        "y": np.array(positions) * 2
    }

    axis_specs = {
        1: {"alias": "x", "max_velocity": 200, "max_acceleration": 4000},
        2: {"alias": "y", "max_velocity": 200, "max_acceleration": 4000}
    }

    #t = time.time()

    _, factors = limit_trajectory_speed_and_acceleration(axis_positions, axis_specs, TIME_STEP)

    # ~1 ms - seems ok
    #print("Duration: " + str(time.time() - t))

    # x-axis does no violate velocity nor acceleration.
    assert factors["x"]["k_v"] == pytest.approx(150 / 200) and factors["x"]["k_a"] == pytest.approx(1500 / 4000)

    # y-axis violates velocity.
    assert factors["y"]["k_v"] == pytest.approx(300 / 200) and factors["y"]["k_a"] == pytest.approx(3000 / 4000)


def test_limit_trajectory_speed_and_acceleration_2():
    positions = create_positions(max_speed=150, acceleration=1500, distance=50)

    axis_positions = {
        "x": positions,
        "y": np.array(positions)
    }

    axis_specs = {
        1: {"alias": "x", "max_velocity": 200, "max_acceleration": 4000},
        2: {"alias": "y", "max_velocity": 200, "max_acceleration": 4000}
    }

    #t = time.time()

    axis_positions_2, _ = limit_trajectory_speed_and_acceleration(axis_positions, axis_specs, TIME_STEP)

    # ~1 ms - seems ok
    #print("Duration: " + str(time.time() - t))

    assert axis_positions is axis_positions_2


def test_compute_total_velocity():
    axis_positions = {
        "x": create_positions(max_speed=50, acceleration=700, distance=50),
        "y": create_positions(max_speed=50, acceleration=700, distance=50)
    }

    v = compute_total_velocity(axis_positions, TIME_STEP)

    assert np.max(v) == pytest.approx(math.sqrt(2 * 50**2))
