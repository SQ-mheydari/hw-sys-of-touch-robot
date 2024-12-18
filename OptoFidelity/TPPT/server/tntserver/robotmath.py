import math
import numpy as np

import transformations as tr

"""
Math related to robot control
"""


class matrix(np.matrix):
    def __new__(cls, inputarr, dtype=None, copy=None, meta=None):
        obj = np.asmatrix(inputarr).view(cls)
        if meta is not None:
            obj.meta = meta
        return obj

    def __array_finalize__(self, obj):
        try:
            self.meta = obj.meta
        except:
            self.meta = ""

    def __mul__(self, other):
        v = super().__mul__(other)
        v.meta = self.meta
        return asmatrix(v)

    def __rmul__(self, other):
        v = super().__rmul__(other)
        v.meta = self.meta
        return asmatrix(v)

    def __imul__(self, other):
        v = super().__imul__(other)
        v.meta = self.meta
        return asmatrix(v)

    def __pow__(self, other):
        v = super().__pow__(other)
        v.meta = self.meta
        return asmatrix(v)

    def __ipow__(self, other):
        v = super().__ipow__(other)
        v.meta = self.meta
        return asmatrix(v)


def asmatrix(data, dtype=None):
    return matrix(data, dtype=dtype, copy=False)


# FRAME and POSE:
#
# FRAME and POSE are both transformation matrices, both contain position and orientation in 4x4 matrix
#
# FRAME is designed to be chained in kinematics
# - the table of the robot defines the world where
#   z points up, x points right and y points to the front side of the robot
#
#   ^ Z
#   |
#   |____> X   ROBOT BASE FRAME
#   /
#  /
# Y
#
# The kinematics built on this base should follow the rule that the chained next node in the kinematic tree
# is always connected to the Z axis direction of the previous node.
# This results the robot's frame to point down so that the tools and tips can be chained to the correct direction
#
# X<----o      ROBOT (effector) FRAME (rotated 180 degrees around X and Z axis compared to ROBOT BASE FRAME )
#      /|
#     / |
#    /  |
#   Y   Z
#
#
# POSE is intended only for end user usage:
#   it is much easier to think "I want to touch point at x, y, z with 10 degrees tilt" than
#   " to which direction the tooltip frame axis points when I rotate tooltip 10 degrees at x, y, z"
# POSE with user interface zero tilt, azimuth has zero rotation in the matrix.

# functions to convert between FRAME and POSE when handling requests in the API requests:

def pose_to_frame(pose):
    frame = pose.copy()
    frame.A[0:3, 0] *= -1
    frame.A[0:3, 2] *= -1
    return frame


def frame_to_pose(frame):
    pose = frame.copy()
    pose.A[0:3, 0] *= -1
    pose.A[0:3, 2] *= -1
    return pose


def identity_frame():
    return np.matrix(np.eye(4))


def scale_xyz_to_frame(sx, sy, sz):
    m = np.matrix(np.eye(4))
    m.A[0:3, 0] *= sx
    m.A[0:3, 1] *= sy
    m.A[0:3, 2] *= sz

    return m

def xyz_to_frame(x, y, z):
    m = np.matrix(np.eye(4))
    m.A1[3] = float(x)
    m.A1[7] = float(y)
    m.A1[11] = float(z)
    return m


def xyz_rot_to_frame(x, y, z, rot):
    m = np.matrix(np.eye(4))
    m.A1[3] = float(x)
    m.A1[7] = float(y)
    m.A1[11] = float(z)
    m[0:3, 0:3] = rot
    return m


def xyz_euler_to_frame(x, y, z, a, b, c, axis="sxyz"):
    frame = tr.euler_matrix(math.radians(a), math.radians(b), math.radians(c), axis)
    frame[0:3, 3] = [x, y, z]
    frame = np.matrix(frame)
    return frame


def xyz_tas_to_frame_2(x, y, z, tilt, azimuth, spin):
    frame = tr.euler_matrix(math.radians(spin), math.radians(tilt), math.radians(-azimuth), 'szyz')
    frame = np.matrix(frame)
    frame.A[0:3, 3] = x, y, z
    return frame


def set_frame_xyz(frame, x=None, y=None, z=None):
    if x is not None:
        frame.A1[3] = float(x)

    if y is not None:
        frame.A1[7] = float(y)

    if z is not None:
        frame.A1[11] = float(z)


def frame_to_xyz(m):
    x = m.A1[3]
    y = m.A1[7]
    z = m.A1[11]
    return x, y, z


def frame_to_debug_str(frame):
    """
    Convert frame to a string that can be used in debugging.
    :param frame: Frame as 4x4 matrix.
    :return: String object.
    """
    x, y, z, a, b, c = frame_to_xyz_euler(frame)

    return "({:.3f}, {:.3f}, {:.3f}) Euler: ({:.3f}, {:.3f}, {:.3f})".format(x, y, z, a, b, c)

def frame_to_xyz_euler(m, axis="sxyz"):
    a, b, c = tr.euler_from_matrix(m, axis)
    x = m.A1[3]
    y = m.A1[7]
    z = m.A1[11]
    return x, y, z, math.degrees(a), math.degrees(b), math.degrees(c)


def frame_to_xyz_tas(frame:np.matrix):
    """
    heavily optimized version
    Note: tilt==0 results in both Azimuth and Spin ending up in the exactly same axis
          and the result (spin - azimuth) will only show in Spin
    :param frame:
    :return: x, y, z, tilt, azimuth, spin (degrees)
    """
    reverse = False

    # get up vector
    x, y, z = frame.A[0:3, 2]
    if z <= 0:
        # vector pointing down instead of up
        # might be illegal
        reverse = True

    # azimuth is z-vector rotation around z-axis
    azimuth = -round(math.degrees(math.atan2(y, x)), 8)

    # tilt is the same no matter where x/y points
    tilt = round(math.degrees(math.acos(z)), 8)
    b = math.radians(azimuth)

    # inverse rotation with tilt, azimuth
    b11 = math.cos(b)
    b21 = math.sin(b)

    (c11, c12), (c21, c22) = frame.A[0:2, 0:2]

    x = b21 * c11 + b11 * c21
    y = b21 * c12 + b11 * c22

    # now only spin remains in the matrix
    spin = round(math.degrees(math.atan2(x, y)), 8)

    if reverse:
        # maybe there is a way to rescue the numbers here
        # the angle values are almost sane and can be corrected
        # by negating / adding 180 degrees etc. but not with one rule
        raise(Exception("upside down pose not supported for tilt azimuth spin"))

    x, y, z = frame.A[0:3, 3]
    return x, y, z, tilt, azimuth, spin


def rotation_matrix_from_vectors(x, y, z=None):
    try:
        x0 = x / np.linalg.norm(x)
        y0 = y / np.linalg.norm(y)

        if z is not None:
            z0 = z / np.linalg.norm(z)
            B = np.array([1, 0, 0]).reshape((3, 1)) * x0 + np.array([0, 1, 0]).reshape((3, 1)) * y0 + np.array(
                [0, 0, 1]).reshape((3, 1)) * z0
        else:
            B = np.array([1, 0, 0]).reshape((3, 1)) * x0 + np.array([0, 1, 0]).reshape((3, 1)) * y0

        U, s, Vh = np.linalg.svd(B)
        M = np.diag([1, 1, np.linalg.det(U) * np.linalg.det(Vh)])
        R = U.dot(M).dot(Vh)
    except:
        raise(Exception("Could not create plane from x={} y={} z={}".format(x, y, z)))

    return R


def three_point_frame(p1, p2, p3):
    """
    Creates transformation matrix from three 3D points.
    Translation part of the matrix will be p1
    :param p1: tuple of xyz or numpy matrix, top left corner
    :param p2: tuple of xyz or numpy matrix, top right corner
    :param p3: tuple of xyz or numpy matrix, bottom left corner
    :return: frame defined by three corners
    """
    if isinstance(p1, np.matrix):
        p1 = np.array([p1.A1[3], p1.A1[7], p1.A1[11]])
        p2 = np.array([p2.A1[3], p2.A1[7], p2.A1[11]])
        p3 = np.array([p3.A1[3], p3.A1[7], p3.A1[11]])
    else:
        p1 = np.array(p1)
        p2 = np.array(p2)
        p3 = np.array(p3)

    vx = p2 - p1
    vy = p3 - p1
    rotation_matrix = rotation_matrix_from_vectors(vx, vy).T

    frame = np.eye(4)
    frame[0:3,0:3] = rotation_matrix
    frame[0:3,3] = p1
    frame = np.matrix(frame)

    return frame


def translate(frame, source, target):
    """
    Translates transformation matrix from source context to target context
    :param frame: 4x4 transformation matrix
    :param source: source context Node
    :param target: target context Node
    :return:
    """
    m = np.matrix(np.copy(frame))

    if source is target:
        return m

    node = source
    while node is not None:
        m = node.frame * m
        node = node.object_parent
        if node is target:
            return m

    nodes = []
    node = target
    while node is not None:
        nodes.append(node)
        node = node.object_parent

    nodes = nodes[::-1]
    for node in nodes:
        m = np.linalg.solve(node.frame, m)

    return m


def frame_to_xyz_abc_string(frame):
    x, y, z, a, b, c = frame_to_xyz_euler(frame)

    s = "x={} y={} z={} a={} b={} c={}".format(
        round(x, 3),
        round(y, 3),
        round(z, 3),
        round(a, 3),
        round(b, 3),
        round(c, 3)
    )
    return s


def frame_to_xyz_tas_str(frame:np.matrix):
    x, y, z, tilt, azimuth, spin = frame_to_xyz_tas(frame)
    return "{},{},{} tilt:{} azimuth:{} spin:{}".format(x, y, z, tilt, azimuth, spin)


def get_frame_translation_vector(frame):
    x, y, z = frame_to_xyz(frame)
    return np.matrix([x, y, z])


def set_frame_translation_vector(frame, translation):
    set_frame_xyz(frame, translation.A1[0], translation.A1[1], translation.A1[2])


def get_frame_x_basis_vector(frame):
    return np.array(frame.A[0:3, 0])


def get_frame_y_basis_vector(frame):
    return np.array(frame.A[0:3, 1])


def get_frame_z_basis_vector(frame):
    return np.array(frame.A[0:3, 2])


def set_frame_x_basis_vector(frame, v):
    frame.A[0:3, 0] = v


def set_frame_y_basis_vector(frame, v):
    frame.A[0:3, 1] = v


def set_frame_z_basis_vector(frame, v):
    frame.A[0:3, 2] = v


def transform_position(frame, position):
    """
    Transform position vector by homogeneous transform.
    Given position can be Numpy matrix or array or Python list. Returned vector has the same type.
    If position is Numpy matrix, it is treated as column vector and multiplied as frame * position.
    :param frame: 4x4 Numpy matrix.
    :param position: Position vector.
    :return: Transformed position vector.
    """
    if isinstance(position, np.matrix):
        v = np.matrix([
            [position.A1[0]],
            [position.A1[1]],
            [position.A1[2]],
            [1.0]
        ])
    elif isinstance(position, list) or isinstance(position, np.ndarray):
        v = np.matrix([
            [position[0]],
            [position[1]],
            [position[2]],
            [1.0]
        ])
    else:
        assert False

    v = frame * v

    if isinstance(position, np.matrix):
        return np.matrix([
        [v.A1[0]],
        [v.A1[1]],
        [v.A1[2]]])
    elif isinstance(position, np.ndarray):
        return np.array([v.A1[0], v.A1[1], v.A1[2]])
    elif isinstance(position, list):
        return [v.A1[0], v.A1[1], v.A1[2]]
    else:
        assert False


def line_line_intersection(start1, dir1, start2, dir2):
    """
    Compute line-line intersection.
    Can be used with lines in 2D or 3D space. In 3D the resulting
    line coordinates correspond to closest points between the lines.
    :param start1: Start point of line 1.
    :param dir1: Direction of line 1.
    :param start2: Start point of line 2.
    :param dir2: Direction of line 2.
    :return: Numpy array of line coordinates to intersection point [t1, t2].
    """
    A = np.array([
        [np.dot(dir1, dir1), -np.dot(dir1, dir2)],
        [np.dot(dir1, dir2), -np.dot(dir2, dir2)]
    ])

    b = np.array([
        np.dot(start2 - start1, dir1),
        np.dot(start2 - start1, dir2)
    ])

    x = np.linalg.solve(A, b)

    return x


def point_distance_to_line(start, dir, point):
    """
    Get orthogonal distance of point to infinite line.
    :param start: Start of line (or any point on the line).
    :param dir: Direction of the line. Should be unit vector for the return value to be unscaled distance.
    :param point: Point whose distance to line to measure.
    :return: Orthogonal distance.
    """
    diff = point - start
    proj = np.dot(dir, diff)

    return np.linalg.norm(diff - proj * dir)


def point_distance_to_line_segment(start, end, point):
    """
    Get distance of point to finite line segment.
    :param start: Start point of line segment.
    :param end: End point of line segment.
    :param point: Point whose distance to line to measure.
    :return: Distance.
    """
    segment = end - start
    segment_length = np.linalg.norm(segment)

    if segment_length == 0:
        return np.linalg.norm(start - point)

    segment_dir = segment / segment_length
    line_coordinate = np.dot(point - start, segment_dir)

    if line_coordinate < 0:
        return np.linalg.norm(start - point)

    if line_coordinate > segment_length:
        return np.linalg.norm(end - point)

    return point_distance_to_line(start, segment_dir, point)


def inv_oht(t):
    """
    Compute inverse of a 4x4 orthonormal homogeneous transformation matrix. It is assumed, the upper 3x3 part is a
    rotation matrix.
    :param t: Homogeneous transformation matrix (4x4).
    :return: Inverse of t.
    """
    if isinstance(t, np.matrix):
        t_inv = np.matrix(np.eye(4))
        t_inv[0:3, 0:3] = t[0:3, 0:3].T
        t_inv[0:3, 3] = -t[0:3, 0:3].T * t[0:3, 3]
    else:
        t_inv = np.eye(4)
        t_inv[0:3, 0:3] = t[0:3, 0:3].transpose()
        t_inv[0:3, 3] = -t[0:3, 0:3].transpose() @ t[0:3, 3]

    return t_inv


def quaternion_from_matrix(m):
    """
    Wrapper around transformations.quaternion_from_matrix() to work with
    3x3 and 4x4 matrices.
    :param m: A 3x3 or 4x4 matrix that describes a rotation.
    :return: Rotation quaternion.
    """
    m2 = identity_frame()
    m2[:3, :3] = m[:3, :3]

    return tr.quaternion_from_matrix(m2)
