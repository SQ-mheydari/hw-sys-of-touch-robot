import logging
import uuid
import concurrent.futures
import numpy as np
from .NodeCalibratorOptoStdForce import window_force_data

from tntserver.Nodes.Node import Node, json_out, NodeException

log = logging.getLogger(__name__)


class NodeCalibratorForceVoiceCoil(Node):
    """
    Node for voice coil calibration functionality
    """
    def _init(self, robot, sensor, force_threshold=2.0, max_rel_variation=0.02, max_abs_variation=2.0, **kwargs):
        self.robot = Node.find(robot)
        self._sensor = Node.find(sensor)
        self._async = concurrent.futures.ThreadPoolExecutor()
        self._calibrations = {}
        self._force_threshold = force_threshold
        self._max_rel_variation = max_rel_variation
        self._max_abs_variation = max_abs_variation

    @staticmethod
    def _to_force_calibration(stats):
        """
        Transforms measured calibration data to a TnT configuration compatible dictionary format
        :param stats: Measurement data
        :return: Dictionary with formatted and sorted data
        """
        data = []
        # Filter nans
        for yi, xi in sorted(stats.items()):
            if not np.isnan(xi):
                data.append((yi, xi))
        # Must sort for interpolate to work
        data.sort()
        # Convert to float as numpy integers can't be saved into config
        currents = [float(e[0]) for e in data]
        forces = [float(e[1]) for e in data]

        return {"current": currents, "force": forces}

    def _check_abort(self, calibration_id):
        """
        Check if TnT UI has sent a cancel request
        :param calibration_id: Calibration uuid
        :return:
        """
        calibration = self._calibrations.get(calibration_id, None)
        if calibration is not None and calibration.get("abort", False):
            raise NodeException(title="Aborted calibration due to user request.")

    def _safe_tare(self, timeout=10):
        """
        Tares the used sensor in a safe way
        :param timeout: How long taring waits for the results to stabilize
        :return:
        """
        try:
            self._sensor.tare_sensor(timeout_s=timeout)
        except NodeException:
            log.warning("Sensor did not tare in %d seconds", timeout)

    def _calibrate(self, calibration_id, axis_name, window_size=100):
        """
        The main calibration procedure. Taps the force sensor with a range of torque limits and measures the resulting forces.
        :param calibration_id: Calibration uuid
        :param axis_name: Name of the axis being calibrated
        :param window_size: How many points from the middle of the measurement in either direction are used when averaging results
        :return:
        """
        force_driver = self.robot.force_driver

        # Do calibration from min current to max current in approximately given amount of steps.
        num_forces = int(round((force_driver.max_current - force_driver.min_current) / force_driver.current_step))
        calibration_currents = np.linspace(force_driver.min_current, force_driver.max_current, num_forces)

        # Add previous calibration data to the calibration dictionary for comparison on UI
        measurement_results = {current: float('nan') for current in calibration_currents}
        calibration = self._calibrations[calibration_id]
        calibration['measurements'] = measurement_results
        try:
            calibration['previous_calibration'] = self.robot.force_calibration_table
        except AttributeError:
            log.debug('Previous calibration not found')
            calibration['previous_calibration'] = {}

        calibration['state'] = 'Calibrating'

        # Calibration procedure starts with the tip touching the force sensor plate
        # Move 3 mm up from the plate to achieve correct stroke length for the voice coil
        start_frame = self.robot.effective_frame
        calibration_frame = start_frame
        calibration_frame.A[2, 3] += 2.5
        self.robot.effective_frame = calibration_frame

        for current in calibration_currents:
            self._check_abort(calibration_id)
            self._safe_tare()
            log.info('Pressing with current {} mA'.format(current))
            # Hold the force steady for 2.0 seconds to gather enough data.
            # Target_stroke of 4mm will press 1mm "through" the force sensor surface to ensure proper force application.
            future = self._async.submit(force_driver.tap_with_current, current=current, duration=2.0, target_stroke=4.0,
                                        axis_name=axis_name)

            results = []
            # While the tap is held , collect readings from force sensor
            while not future.done():
                results.append(self._sensor.read_tared_force())

            error = future.exception()
            if error:
                raise NodeException(title='Exception occurred during press gesture: {}'.format(str(error)))
            else:
                windowed_results = window_force_data(results, window_size,
                                                     force_threshold=self._force_threshold,
                                                     max_rel_variation=self._max_rel_variation,
                                                     max_abs_variation=self._max_abs_variation)

                # Calculate the mean from the windowed data to filter out any possible skewing by set point dynamics
                measurement_results[current] = np.nanmean(windowed_results)

                calibration['results'] = self._to_force_calibration(measurement_results)

        calibration['state'] = 'Ready'

    def _validate(self, calibration_id, axis_name, validation_points, window_size=100):
        start_force = int(np.ceil(min(self.robot.force_calibration_table[axis_name]['force'])/10)*10)
        end_force = int(np.floor(max(self.robot.force_calibration_table[axis_name]['force'])/10)*10)

        # Get forces for all validation points
        force_validation_values = np.linspace(start_force, end_force, int(validation_points))

        # Add previous calibration data to the calibration dictionary for comparison on UI
        measurement_results = {force: float('nan') for force in force_validation_values}
        calibration = self._calibrations[calibration_id]
        calibration['measurements'] = measurement_results
        calibration['state'] = 'Validating'

        # Validation procedure starts with the tip touching the force sensor plate
        # Move 3 mm up from the plate to achieve correct stroke length for the voice coil
        start_frame = self.robot.effective_frame
        validation_frame = start_frame
        validation_frame.A[2, 3] += 2.5
        self.robot.effective_frame = validation_frame

        force_driver = self.robot.force_driver

        for force in force_validation_values:
            self._check_abort(calibration_id)
            self._safe_tare()
            log.info('Pressing with force {} g'.format(force))

            # Hold the force steady for 2.0 seconds to gather enough data.
            # Target_stroke of 4mm will press 1mm "through" the force sensor surface to ensure proper force application.
            future = self._async.submit(force_driver.tap_with_force, force=force, duration=2.0, target_stroke=4.0,
                                        axis_name=axis_name)

            results = []
            # While the tap is held , collect readings from force sensor
            while not future.done():
                results.append(self._sensor.read_tared_force())

            error = future.exception()
            if error:
                raise NodeException(title='Exception occurred during press gesture: {}'.format(str(error)))
            else:
                windowed_results = window_force_data(results, window_size, force_threshold=self._force_threshold)
                # Calculate the mean from the windowed data to filter out any possible skewing by set point dynamics
                measurement_results[force] = np.nanmean(windowed_results)

        calibration = self._calibrations[calibration_id]
        calibration['state'] = 'Ready'

    def _add_calibration(self, axis_name):
        """
        Add calibration to calibrations list and initialize the dictionary
        :param axis_name: Name of the axis being calibrated
        :return:
        """
        calibration_id = str(uuid.uuid4())
        self._calibrations[calibration_id] = {'calibration_id': calibration_id,
                                              'axis': axis_name,
                                              'measurements': {},
                                              'previous_calibration': {}}
        return calibration_id

    @json_out
    def put_calibrate(self, axis_name=None):
        """
        Perform force calibration synchronously.
        :param axis_name: Name of axis to calibrate for force. None to use the default.
        :return: Dict which contains finished force calibration.
        """
        if axis_name is None:
            axis_name = self.robot.force_driver.axis

        calibration_id = self._add_calibration(axis_name)
        self._check_calibration(calibration_id, axis_name)
        return self._calibrations[calibration_id]

    @json_out
    def post_calibrate(self, axis_name=None):
        """
        Perform force calibration asynchronously.
        :param axis_name: Name of axis to calibrate for force. None to use the default.
        :return: Dict which contains finished force calibration.
        """
        if axis_name is None:
            axis_name = self.robot.force_driver.axis

        calibration_id = self._add_calibration(axis_name)
        self._calibrations[calibration_id]['state'] = 'Starting calibration'
        self._async.submit(self._check_calibration, calibration_id, axis_name)
        return self._calibrations[calibration_id]

    @json_out
    def post_validate(self, axis_name=None, validation_points=5):
        """
        Perform force calibration asynchronously.
        :param axis_name: Name of axis whose force to validate.
        :param validation_points: Number of validation points to use.
        :return: Dict which contains finished force calibration.
        """
        if axis_name is None:
            axis_name = self.robot.force_driver.axis

        validation_points = int(validation_points)
        calibration_id = self._add_calibration(axis_name)
        self._async.submit(self._do_validation, calibration_id, axis_name, validation_points)
        return self._calibrations[calibration_id]

    def _check_calibration(self, calibration_id, axis_name, **kwargs):
        """
        Performs the calibration and records state changes for the TnT UI in case of exceptions
        :param calibration_id: Calibration uuid
        :param axis_name: Name of the axis being calibrated
        :param kwargs: Possible additional arguments
        :return:
        """
        try:
            self._calibrations[calibration_id]["state"] = "Starting calibration"
            self._calibrate(calibration_id, axis_name, **kwargs)
        except NodeException as e:
            log.warning("Calibration was cancelled: %s, %s", e.title, e.messages)
            self._calibrations[calibration_id]["state"] = "Cancelled"
            self._calibrations[calibration_id]["error"] = e.title
            self._calibrations[calibration_id]["error_messages"] = e.messages
        except Exception as e:
            log.exception('Exception during calibration')
            self._calibrations[calibration_id]['state'] = 'Error'
            self._calibrations[calibration_id]['error'] = str(e)

    def _do_validation(self, calibration_id, axis_name, validation_points, **kwargs):
        """
        Performs the calibration and records state changes for the TnT UI in case of exceptions
        :param calibration_id: Calibration uuid
        :param axis_name: Name of the axis being calibrated
        :param kwargs: Possible additional arguments
        :return:
        """
        try:
            self._calibrations[calibration_id]["state"] = "Starting validation"
            self._validate(calibration_id, axis_name, validation_points, **kwargs)
        except NodeException as e:
            log.warning("Validation was cancelled: %s, %s", e.title, e.messages)
            self._calibrations[calibration_id]["state"] = "Cancelled"
            self._calibrations[calibration_id]["error"] = e.title
            self._calibrations[calibration_id]["error_messages"] = e.messages
        except Exception as e:
            log.exception('Exception during validation')
            self._calibrations[calibration_id]['state'] = 'Error'
            self._calibrations[calibration_id]['error'] = str(e)

    @json_out
    def get_calibration_status(self, calibration_id):
        """
        Returns the calibration dictionary
        :param calibration_id: Calibration uuid
        :return: Dict which contains force calibration information e.g. state, possible error with messages, measurements, previous calibration results
        """
        if calibration_id not in self._calibrations:
            raise NodeException("Unknown calibration id: {}".format(calibration_id), 400,
                                ["Available only ({})".format(", ".join(self._calibrations.keys()))])
        return self._calibrations[calibration_id]

    @json_out
    def put_stop_calibration(self, calibration_id):
        """
        Called from the UI when user wants to cancel the calibration
        :param calibration_id: Calibration uuid
        :return:
        """
        if calibration_id in self._calibrations:
            self._calibrations[calibration_id]["abort"] = True
        return self._calibrations[calibration_id]

    @json_out
    def put_stop_validation(self, calibration_id):
        """
        Called from the UI when user wants to cancel the calibration
        :param calibration_id: Calibration uuid
        :return:
        """
        if calibration_id in self._calibrations:
            self._calibrations[calibration_id]["abort"] = True
        return self._calibrations[calibration_id]

    @json_out
    def put_save_calibration(self, calibration_id):
        """
        Saves the corresponding calibration data to the server configuration file
        :param calibration_id: Calibration uuid
        :return:
        """
        if calibration_id in self._calibrations:
            # Set entire table to make sure the property setter is called.
            calibration_table = self.robot.force_calibration_table
            axis_name = self._calibrations[calibration_id]["axis"]
            calibration_table[axis_name] = self._calibrations[calibration_id]["results"]
            self.robot.force_calibration_table = calibration_table

            self.robot.save()
