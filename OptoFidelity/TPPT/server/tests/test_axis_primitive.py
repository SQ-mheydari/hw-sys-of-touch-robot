from tntserver.drivers.robots.golden_program import *
import pytest
from tests.test_golden_program import StubProgram
import os

axis_positions = (0.00012, 0.0012, 0.12, 1.2)
reference_file = os.path.abspath(os.path.join(os.getcwd(), 'tests', 'data', 'axis_primitive_points.txt'))


class RobotPosition(RobotKinematics.RobotPositionBase):
    """
    Used as input for test AxisPrimitive
    """
    __slots__ = ["frame", "d", "t", 'x']
    pass


def test_duration():
    """
    Test duration property
    Returns: none
    -------

    """
    p = KeyFrameAxisPrimitive('x')
    p._axis_positions = axis_positions
    result = p.duration
    assert result == pytest.approx(len(axis_positions) * TIME_STEP)


def test_append_to_path():
    """
    Test append_to_path()
    Returns: none
    -------

    """

    def check_result(axis_primitive, path_appended: list, length: int, is_join = False):
        """
        Verify the result after call append_to_path().
        :param axis_primitive: AxisPrimitive or KeyFrameAxisPrimitive instance.
        :param path_appended: Path after call append_to_path().
        :param length: Difference between current position and target position.
        :param is_join: If it is to join path or to create a new path.
        """
        # check if new path is created correctly or not
        track = create_track(axis_primitive._speed, axis_primitive._acceleration,
                             length)

        positions = []
        # skip the first position from path, because the difference between the length of path and length of reference is just 1,
        # roughly looking at these values, the first point is irrelevant and rest points are matchable.
        # And also because the first position is set before calling append_to_path(), we only need to verify these positions
        # which are added by append_to_path()
        for robotpos in path_appended[1:]:
            positions.append((robotpos.d, robotpos.t))

        pos_first = path_appended[0]
        assert np.allclose(pos_first.frame, robotmath.xyz_to_frame(10, 20, 30))
        assert pos_first.d == 0
        assert pos_first.t == 0
        assert len(path_appended) == len(track) + 1

        assert np.allclose(positions, track)

        # check if new path joins existing path correctly or not
        if isinstance(axis_primitive, KeyFrameAxisPrimitive):
            k_positions = axis_primitive._key_positions
            k_times = axis_primitive._key_times
            l = len(path_appended)
            if is_join:
                if k_positions is not None and k_times is None:
                    for pp in k_positions:
                        for i in range(l):
                            if path_appended[i].d >= pp:

                                n = len(k_positions)
                                if i + n >= l:
                                    n = l - i

                                for j in range(n):
                                    assert path_appended[i + j].x == pytest.approx(axis_positions[j])
                                break

                if k_times is not None:
                    for tt in k_times:
                        for i in range(l):
                            if path_appended[i].t >= tt:
                                n = len(k_times)
                                if i + n >= l:
                                    n = l - i

                                for j in range(n):
                                    assert path_appended[i + j].x == pytest.approx(axis_positions[j])
                                break

    # test starts
    RobotKinematics.RobotPosition = RobotPosition
    position = RobotPosition()
    position.frame = robotmath.xyz_to_frame(10, 20, 30)
    position.d = 0.0
    position.t = 0.0

    speed = 100
    acceleration = 111

    p = AxisPrimitive('x')
    p.set_speed_acceleration(speed=speed, acceleration=acceleration)
    p.target_value = 200

    ###########################################
    # create a new path, current value is known
    ###########################################
    # set current position into path
    position.x = 10
    path = [position]
    p.append_to_path(path=path)

    check_result(p, path, p.target_value - position.x)

    ###########################################
    # create a new path, current value is None, get from driver
    ###########################################
    # current value in path is None
    position.x = None

    # set current position into driver
    position_prgm = RobotPosition()
    position_prgm.frame = robotmath.xyz_to_frame(15, 25, 35)
    position_prgm.d = 0.0
    position_prgm.t = 0.0
    position_prgm.x = 15

    program = StubProgram(arc_r=0.0, position=position_prgm)
    p.program = program

    path = [position]
    p.append_to_path(path=path)

    check_result(p, path, p.target_value - position_prgm.x)

    ###########################################
    # join an existing path, current value is known
    # _key_positions is not None, _key_times is None
    ###########################################
    # 1) generate a path (from 15 to 200)
    p1 = AxisPrimitive('x')
    p1.program = program
    p1.set_speed_acceleration(speed=speed, acceleration=acceleration)
    p1.target_value = 200
    position.x = 15
    path = [position]
    p1.append_to_path(path=path)

    # 2) join another path (from 250 to 300)
    key_positions = [0.02, 0.05, 0.1]
    p2 = KeyFrameAxisPrimitive('x', key_positions=key_positions)
    p2.program = program
    p2.set_speed_acceleration(speed=speed, acceleration=acceleration)

    # now try to join another path (from 250 to 300) to the existing path (from 15 to 200)
    # set current position into path
    path[0].x = 250
    # set target value for a new path, new path from 250 to 300
    p2.target_value = 300
    p2._axis_positions = axis_positions

    p2.append_to_path(path=path)

    check_result(axis_primitive=p2, path_appended=path, length=200 - 15, is_join=True)

    ###########################################
    # join an existing path, current value is known
    # _key_positions is None, _key_times is not None
    ###########################################
    # 1) generate a path (from 15 to 200)
    p1 = AxisPrimitive('x')
    p1.program = program
    p1.set_speed_acceleration(speed=speed, acceleration=acceleration)
    p1.target_value = 200
    position.x = 15
    path = [position]
    p1.append_to_path(path=path)

    # 2) join another path (from 250 to 300)
    key_positions = [0.02, 0.05, 0.1]
    key_times = [0.025, 0.055, 0.15]
    p2 = KeyFrameAxisPrimitive('x', key_positions=key_positions, key_times=key_times)
    p2.program = program
    p2.set_speed_acceleration(speed=speed, acceleration=acceleration)

    # now try to join another path (from 250 to 300) to the existing path (from 15 to 200)
    # set current position into path
    path[0].x = 250
    # set target value for a new path, new path from 250 to 300
    p2.target_value = 300
    p2._axis_positions = axis_positions

    p2.append_to_path(path=path)

    check_result(axis_primitive=p2, path_appended=path, length=200 - 15, is_join=True)

    ###########################################
    # join an existing path, current value is known
    # _key_positions is not None, _key_times is not None
    ###########################################
    # 1) generate a path (from 15 to 200)
    p1 = AxisPrimitive('x')
    p1.program = program
    p1.set_speed_acceleration(speed=speed, acceleration=acceleration)
    p1.target_value = 200
    position.x = 15
    path = [position]
    p1.append_to_path(path=path)

    # 2) join another path (from 250 to 300)
    key_times = [0.025, 0.055, 0.15]
    p2 = KeyFrameAxisPrimitive('x', key_times=key_times)
    p2.program = program
    p2.set_speed_acceleration(speed=speed, acceleration=acceleration)

    # now try to join another path (from 250 to 300) to the existing path (from 15 to 200)
    # set current position into path
    path[0].x = 250
    # set target value for a new path, new path from 250 to 300
    p2.target_value = 300
    p2._axis_positions = axis_positions

    p2.append_to_path(path=path)

    check_result(axis_primitive=p2, path_appended=path, length=200 - 15, is_join=True)


def test_length():
    """
    Test length()
    Returns
    -------

    """
    p = AxisPrimitive('x')
    result = p.length()
    assert pytest.approx(result) == 0


def test_plan_tap():
    """
    Test plan_tap()
    Returns: none
    -------

    """
    current_pos = 10
    target_pos = 200
    speed = 100
    acceleration = 111

    p = KeyFrameAxisPrimitive('x')

    p.set_speed_acceleration(speed=speed, acceleration=acceleration)
    p.plan_tap(length=target_pos-current_pos, speed=speed, acceleration=acceleration)

    RobotKinematics.RobotPosition = RobotPosition
    position = RobotPosition()
    position.frame = robotmath.xyz_to_frame(10, 20, 30)
    position.d = 0.0
    position.t = 0.0
    position.x = current_pos
    p.target_value = target_pos
    path = [position]
    p.append_to_path(path=path)

    # verify the results with reference points in file (cwd)/tests/data/axis_primitive_points.txt
    # get a list of points from results
    points_result = []
    for pos in path:
        points_result.append(pos.d)

    # get a list of points from reference file
    points_reference = []
    with open(reference_file, 'r') as f:
        for ref in f:
            points_reference.append(float(ref))
    f.close()

    # compare two lists
    assert pytest.approx(points_result, points_reference)


def test_set_positions():
    """
    Test class Primitive set_position()
    Returns: none
    -------

    """
    RobotKinematics.RobotPosition = RobotPosition
    position = RobotPosition()
    position.frame = robotmath.xyz_to_frame(10, 20, 30)
    position.d = 0.0
    position.t = 0.0

    p = AxisPrimitive('x')
    p.set_positions(position)

    assert isinstance(p._positions, RobotPosition)
    assert p._positions.d == pytest.approx(position.d)
    assert p._positions.t == pytest.approx(position.t)
    assert p._positions.frame == pytest.approx(position.frame)


def test_set_speed_acceleration():
    """
    Test class Primitive set_speed_acceleration()
    Returns: none
    -------

    """
    speed = 100
    acceleration = 111

    p = AxisPrimitive('x')
    p.set_speed_acceleration(speed=speed, acceleration=acceleration)

    assert pytest.approx(p._speed) == speed
    assert pytest.approx(p._acceleration) == acceleration


############################################
# Following codes are NOT used in testing,
# Only used to generate reference points to test plan_tap()
############################################
def generate_reference_points():
    current_pos = 10
    target_pos = 200
    speed = 100
    acceleration = 111

    # generate reference path
    RobotKinematics.RobotPosition = RobotPosition
    position = RobotPosition()
    position.frame = robotmath.xyz_to_frame(10, 20, 30)
    position.d = 0.0
    position.t = 0.0

    p_reference = AxisPrimitive('x')
    p_reference.set_speed_acceleration(speed=speed, acceleration=acceleration)
    p_reference.target_value = target_pos

    position.x = current_pos
    path = [position]
    p_reference.append_to_path(path=path)

    # store reference points to a file
    with open(reference_file, 'w') as f:
        for pos in path:
            f.write(str(pos.d) + '\n')

    f.close()
