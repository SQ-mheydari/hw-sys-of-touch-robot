import numpy as np
import json
import pytest
import time

from tntserver.Nodes.Node import Node, NodeException
from tntserver.Nodes.NodeCalibratorOptoStdForce import NodeCalibratorOptoStdForce, window_force_data
from tests.test_voicecoil_robot import RobotStub


class SensorStub(Node):
    """
    Helper class that simulates some of Futek force sensor's functions.
    """

    def __init__(self, name, duration=0):
        super().__init__(name)
        self.duration = duration

        # Simulate force values caused by press gesture.
        self._force_values = np.array([0.0] * 50 + [800.0] * 300 + [0.0] * 50) + np.random.rand() * 0.5
        self._current_value_ix = 0

    def tare_sensor(self, timeout_s=0):
        if self.duration > timeout_s:
            raise NodeException("Test sensor timeout")

    def read_tared_force(self):
        if self._current_value_ix >= len(self._force_values):
            return 0.0

        value = self._force_values[self._current_value_ix]
        self._current_value_ix += 1

        return value


class NodeCalibratorWrapper(NodeCalibratorOptoStdForce):

    def __init__(self, name):
        super().__init__(name=name)

    def save(self):
        print("Save called")

def create_node():
    """
    Creates calibrator node with required child nodes in the tree.
    :return: calibrator node.
    """
    calib_node = NodeCalibratorWrapper(name='NodeStdForceCalibrator')

    robot_node = RobotStub(name='Robot1')
    sensor_node = SensorStub(name='Futek')

    root = Node("root")
    # Set global root node to enable find operations.
    Node.root = root

    root.add_child(robot_node)
    root.add_child(sensor_node)
    root.add_child(calib_node)

    calib_node._init(robot='Robot1', sensor='Futek')
    return calib_node


def test_init_node():
    """
    Test node creation.
    """
    create_node()


def test_timeout():
    calibrator = create_node()
    sensor_node = calibrator.find('Futek')
    sensor_node.duration = 10
    calibrator._safe_tare(timeout=1)


def test_put_calibrate():
    """
    Tests call to put_calibration REST API call.
    """
    calibrator = create_node()
    calibration = calibrator.put_calibrate(axis_name='voicecoil1')
    assert calibration is not None

    # Convert to dict and test that calibration is found based on id.
    calibration = json.loads(calibration[1].decode())
    assert calibrator.get_calibration_status(calibration['calibration_id']) is not None

    # Check that calibration contains measurement data and no 'nan' values
    measurements = np.array([meas_val for force_val, meas_val in calibration['measurements'].items()])
    assert not np.isnan(measurements).any()

    assert calibration['state'] == 'Ready'

    # Test that non-existent calibration is not found.
    with pytest.raises(Exception):
        calibrator.get_calibration_status("")


def test_stop_calibrate():
    """
    Tests call to put_calibrate REST API call.
    """
    calibrator = create_node()
    calibration = calibrator.put_calibrate(axis_name='voicecoil1')
    calibration = json.loads(calibration[1].decode())

    calibration = calibrator.put_stop_calibration(calibration['calibration_id'])
    calibration = json.loads(calibration[1].decode())
    assert calibration['abort']

    # make su
    with pytest.raises(NodeException):
        calibrator._check_abort(calibration['calibration_id'])


def test_save_calibration():
    """
    Tests call to save_calibration REST API call.
    """
    calibrator = create_node()
    calibration = calibrator.put_calibrate(axis_name='voicecoil1')
    calibration = json.loads(calibration[1].decode())

    calibration = calibrator.put_save_calibration(calibration_id=calibration['calibration_id'])
    assert calibrator.robot.calibration_saved


def test_post_calibrate():
    """
    Tests call to post_calibrate REST API call.
    """
    calibrator = create_node()
    calibration = calibrator.post_calibrate(axis_name='voicecoil1', press_duration=0.1)
    calibration = json.loads(calibration[1].decode())

    calibration = calibrator.get_calibration_status(calibration['calibration_id'])
    calibration = json.loads(calibration[1].decode())

    start_time = time.time()
    timeout = 5
    while calibration['state'] != 'Ready':
        calibration = calibrator.get_calibration_status(calibration['calibration_id'])
        calibration = json.loads(calibration[1].decode())
        if time.time() - start_time > timeout:
            raise Exception("Test timed out.")


def test_window_force_data():
    # Generate data that rises from zero to 20 and then back to zero.
    data = np.array([0.0] * 3000 + [20.0] * 1000 + [0.0] * 500)

    # Add some noise.
    data += np.random.rand(len(data)) * 1.5

    # Use threshold that is slightly more than noise level.
    result = window_force_data(data, window_size=100, force_threshold=2.0)

    # All result values should be clearly above noise level.
    assert min(result) > 15.0

    # The entire window should be obtained.
    assert len(result) == 200
