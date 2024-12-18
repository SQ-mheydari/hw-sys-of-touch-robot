from tntserver.drivers.robots.goldenmov.kinematics.kinematic_hbot import *
import numpy as np


class Robot:
    """
    Stub robot class to enable testing
    """

    def _init_(self):
        pass

    @property
    def calibration_data(self):
        return {}


toolframe = np.matrix([[1, 0, 0, 10],
                       [0, 1, 0, 20],
                       [0, 0, 1, 30],
                       [0, 0, 0, 1]])


class SmCommStub:
    def __init__(self):
        self.axis_parameters = {}

    def get_axis_parameter(self, axis, param):
        return self.axis_parameters[axis][param]

    def set_axis_parameter(self, axis, param, value):
        if axis not in self.axis_parameters:
            self.axis_parameters[axis] = {}

        self.axis_parameters[axis][param] = value


class SmCommHardstopSimulator:
    def __init__(self, start_position, min_limit, max_limit):
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.start_position = start_position

        self.axis_parameters = {"x": {
            sm_regs.SMP_ACTUAL_POSITION_FB: self.start_position,
            sm_regs.SMP_ABSOLUTE_SETPOINT: self.start_position,
            sm_regs.SMP_SYSTEM_CONTROL: 0
        }}

    def get_axis_parameter(self, axis, param):
        return self.axis_parameters[axis][param]

    def set_axis_parameter(self, axis, param, value):
        if axis not in self.axis_parameters:
            self.axis_parameters[axis] = {}

        self.axis_parameters[axis][param] = value

        # Simulate robot moving to given setpoint.
        if param == sm_regs.SMP_ABSOLUTE_SETPOINT:
            # Simulate hard stop at some position
            value = max(value, self.min_limit)
            value = min(value, self.max_limit)

            self.set_axis_parameter(axis, sm_regs.SMP_ACTUAL_POSITION_FB, value)


def test_robot_fk_ik():
    """
    Test robot forward and inverse kinematics together by checking if going
    back and forth the whole chain returns the given input value
    """
    robot = Robot()
    k = Kinematic_hbot(robot)

    def test(x, y, z):
        joints = {"x": x, "y": y, "z": z}
        position_fk = k.joints_to_position(joints, tool=toolframe)
        joints_ik = k.positions_to_joints(positions=[position_fk], tool_inv=toolframe.I)[0]

        for key, value in joints.items():
            assert np.isclose(value, joints_ik[key])

    test(10, 20, 30)
    test(30, 30, 30)
    test(30, 100, 30)
    test(34.5, 30, 80.7)
    test(0, 70.2, 60)
    test(200, 30, 78)
    test(53.8, 123, 54)


def test_robot_fk():
    """
    Test robot forward kinematics with precalculated joint and frame values
    """
    robot = Robot()
    k = Kinematic_hbot(robot)
    joints = {"x": 20, "y": 20, "z": 20}
    position_fk = k.joints_to_position(joints, tool=toolframe)
    fk_frame = np.matrix([[-1, 0, 0, -10],
                          [0, 1, 0, -20],
                          [0, 0, -1, -50],
                          [0, 0, 0, 1]])
    assert np.allclose(position_fk.frame, fk_frame)


def test_robot_ik():
    """
    Test robot inverse kinematics with precalculated joint and frame values
    """
    robot = Robot()
    k = Kinematic_hbot(robot)
    joints = {"x": -15, "y": 15, "z": -10}
    fk_frame = np.matrix([[-1, 0, 0, 20],
                          [0, 1, 0, 20],
                          [0, 0, -1, -20],
                          [0, 0, 0, 1]])
    fk_position = k.create_robot_position(frame=fk_frame)
    joints_ik = k.positions_to_joints(positions=[fk_position], tool_inv=toolframe.I)[0]

    for key, value in joints.items():
        assert np.isclose(value, joints_ik[key])


def test_override_axis_settings():
    sm = SmCommStub()

    sm.set_axis_parameter("x", "speed", 30)
    sm.set_axis_parameter("x", "accel", 50)

    sm.set_axis_parameter("y", "speed", 60)
    sm.set_axis_parameter("y", "accel", 70)

    assert sm.get_axis_parameter("x", "speed") == 30
    assert sm.get_axis_parameter("x", "accel") == 50
    assert sm.get_axis_parameter("y", "speed") == 60
    assert sm.get_axis_parameter("y", "accel") == 70

    with OverrideAxisSettings(sm, {"x": {"speed": 130, "accel": 150}, "y": {"speed": 160, "accel": 170}}):
        assert sm.get_axis_parameter("x", "speed") == 130
        assert sm.get_axis_parameter("x", "accel") == 150
        assert sm.get_axis_parameter("y", "speed") == 160
        assert sm.get_axis_parameter("y", "accel") == 170

    assert sm.get_axis_parameter("x", "speed") == 30
    assert sm.get_axis_parameter("x", "accel") == 50
    assert sm.get_axis_parameter("y", "speed") == 60
    assert sm.get_axis_parameter("y", "accel") == 70


def test_software_hardstop():
    # Test hardstop to negative direction.
    axis_increments = {"x": -100}
    axis_tracking_error_limits = {"x": 10}

    min_limit = 30
    max_limit = 560
    start_position = 400

    sm = SmCommHardstopSimulator(start_position, min_limit, max_limit)

    software_hardstop(sm, axis_increments, axis_tracking_error_limits)

    position = sm.get_axis_parameter("x", sm_regs.SMP_ACTUAL_POSITION_FB)

    # Final position should be 2 increments away from hardstop position.
    assert np.isclose(position, min_limit - 2 * axis_increments["x"])

    # Test hardstop to positive direction.
    axis_increments = {"x": 100}
    axis_tracking_error_limits = {"x": 10}

    sm = SmCommHardstopSimulator(start_position, min_limit, max_limit)

    software_hardstop(sm, axis_increments, axis_tracking_error_limits)

    position = sm.get_axis_parameter("x", sm_regs.SMP_ACTUAL_POSITION_FB)

    # Final position should be 2 increments away from hardstop position.
    assert np.isclose(position, max_limit - 2 * axis_increments["x"])


def test_get_homing_parameters_from_spec():
    spec = {
        1: {
            "alias": "x",
            "homing_parameters": {
                "speed": 100
            }
        },
        2: {
            "alias": "y",
            "homing_parameters": {
                "speed": 200
            }
        }
    }

    parameters = get_homing_parameters_from_spec(spec, "speed")

    assert parameters["x"] == 100 and parameters["y"] == 200

def test_hbot_methods():
    robot = Robot()
    k = Kinematic_hbot(robot)

    specs = k.specs()

    aliases = [axis['alias'] for axis in specs.values()]

    assert 'x' in aliases and 'y' in aliases and 'z' in aliases

    assert k.arc_r() == 0.0

