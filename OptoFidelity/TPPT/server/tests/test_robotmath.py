from tntserver.robotmath import *
import numpy as np


def test_line_line_intersection():
    # Line starting from (10, 20) towards +y.
    start1 = np.array([10, 20])
    dir1 = np.array([0, 1])

    # Line starting at (-15, -5) towards +x.
    start2 = np.array([-15, 15])
    dir2 = np.array([1, 0])

    x = line_line_intersection(start1, dir1, start2, dir2)

    assert np.allclose(x, [-5, 25])


def test_point_distance_to_line():
    start = np.array([5, 10])
    dir = np.array([0, 1])

    point = np.array([15, 10])

    dist = point_distance_to_line(start, dir, point)

    assert np.isclose(dist, 10)


def test_point_distance_to_line_segment():
    start = np.array([5, 10])
    end = np.array([40, 10])

    # Test points within the line segment.
    assert np.isclose(point_distance_to_line_segment(start, end, np.array([20, 20])), 10)
    assert np.isclose(point_distance_to_line_segment(start, end, np.array([20, -10])), 20)

    # Test points before line segment start and after line segment end.
    assert np.isclose(point_distance_to_line_segment(start, end, np.array([0, 10])), 5)
    assert np.isclose(point_distance_to_line_segment(start, end, np.array([50, 10])), 10)


def test_transform_position():
    frame = np.matrix([
        [1, 0, 0, 10],
        [0, 1, 0, 20],
        [0, 0, 1, 30],
        [0, 0, 0, 1]
    ])

    # Position as list.
    result = transform_position(frame, [1, 2, 3])
    assert isinstance(result, list)
    assert np.allclose(result, [11, 22, 33])

    # Position as column vector Numpy matrix.
    result = transform_position(frame, np.matrix([[1], [2], [3]]))
    assert isinstance(result, np.matrix)
    assert np.allclose(result.A1, [11, 22, 33])

    # Position as Numpy array.
    result = transform_position(frame, np.array([1, 2, 3]))
    assert isinstance(result, np.ndarray)
    assert np.allclose(result, [11, 22, 33])


def test_inverse_homogeneous_transform():

    t = xyz_euler_to_frame(10, -20, 45.6, 34, -98, 130)
    t_inv_np = np.linalg.inv(np.array(t))  # Reference result
    t_inv_arr = inv_oht(np.array(t))  # Inverse of np.array
    t_inv_m = inv_oht(t)  # Inverse of np.matrix

    assert np.allclose(t_inv_np, t_inv_arr)
    assert np.allclose(t_inv_np, np.array(t_inv_m))
