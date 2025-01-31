import logging
import uuid
import concurrent.futures
import numpy as np
from tntserver.Nodes.Node import Node, json_out, NodeException
from tntserver.Nodes.Voicecoil.Gestures import VoicecoilMaxContPeakCurrent

log = logging.getLogger(__name__)


def window_force_data(data, window_size, force_threshold=2.0, max_rel_variation=0.01, max_abs_variation=2.0):
    """
    Get force measurement results from a window where transient values have been removed.
    Window is found within the rising and falling edges of measured force values.
    :param window_size: Number of samples around the mid point of rising/falling edge region to accept.
    :param force_threshold: Threshold for force measurements. Should be higher than force readings after taring.
    :param max_rel_variation: Maximum allowed relative variation of force values.
    :param max_abs_variation: Maximum allowed absolute variation of force values.
    """

    # Get data indices that define a window where data values exceed target force.
    # ix0 is the index of the first value higher than threshold and ix1 is the index of the
    # last value higher than the threshold.
    ix0 = np.argmax(np.greater(data, force_threshold))
    ix1 = len(data) - np.argmax(np.greater(data[::-1], force_threshold))

    if ix0 > ix1:
        raise Exception("Could not correctly determine force data window.")

    results = data[ix0:ix1]

    nresults = len(results)
    middle = nresults // 2

    if nresults < window_size * 2:
        raise Exception("Number of results is less than window size. Increase sample rate or press duration.")

    window_ix0 = middle - window_size

    if window_ix0 < 0:
        raise Exception("Data window touches the low end of the data set.")

    window_ix1 = middle + window_size

    if window_ix1 > nresults:
        raise Exception("Data window touches the high end of the data set.")

    windowed_results = results[window_ix0:window_ix1]

    variation = max(windowed_results) - min(windowed_results)

    if variation > max_rel_variation * np.mean(windowed_results) and variation > max_abs_variation:
        raise Exception("Force data min/max variation {} exceeds absolute limit {} and relative limit {}.".
                        format(variation, max_abs_variation, max_rel_variation))

    log.debug("Windowed force: {} g (min-max: {} g, stdev {} g).".format(
        np.nanmean(windowed_results),
        variation,
        np.std(windowed_results)))

    return windowed_results


# TODO nodecalibrators could be inherited
class NodeCalibratorOptoStdForce(Node):
    """
    Node for voice coil calibration functionality
    """
    def _init(self, robot, sensor, press_duration=4.0, force_threshold=2.0,
              max_rel_variation=0.02, max_abs_variation=2.0, **kwargs):
        self.robot = Node.find(robot)
        self._sensor = Node.find(sensor)
        self._async = concurrent.futures.ThreadPoolExecutor()
        self._calibrations = {}
        self._force_threshold = force_threshold
        self._max_rel_variation = max_rel_variation
        self._max_abs_variation = max_abs_variation

        # Default press duration in calibration and validation.
        self._press_duration = press_duration

    @staticmethod
    def _to_force_calibration(stats):
        """
        Transforms measured calibration data to a TnT configuration compatible 
        dictionary format
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
        setpoint_values = [float(e[0]) for e in data]
        actual_values = [float(e[1]) for e in data]

        return {"actual_values": actual_values, "setpoint_values": setpoint_values}

    def _check_abort(self, calibration_id):
        """
        Check if TnT UI has sent a cancel request
        :param calibration_id: Calibration uuid
        :return: None
        """
        calibration = self._calibrations.get(calibration_id, None)
        if calibration is not None and calibration.get("abort", False):
            raise NodeException(title="Aborted calibration due to user request.")

    def _safe_tare(self, timeout=10):
        """
        Tares the used sensor in a safe way
        :param timeout: How long taring waits for the results to stabilize
        :return: None
        """
        try:
            self._sensor.tare_sensor(timeout_s=timeout)
        except NodeException:
            log.warning("Sensor did not tare in %d seconds", timeout)

    def _add_calibration(self, axis_name):
        """
        Add calibration to calibrations list and initialize the dictionary
        :param axis_name: Name of the axis being calibrated
        :return: None
        """
        calibration_id = str(uuid.uuid4())
        self._calibrations[calibration_id] = {'calibration_id': calibration_id,
                                              'axis': axis_name,
                                              'measurements': {},
                                              'previous_calibration': {}}
        return calibration_id

    def _force_sequence(self, calibration_id: str, measurement_points: int,
                        is_calibration: bool, window_size=None, press_duration=4.0, **kwargs):
        """
        Performs force sequence to calibrate or validate. Record state changes for the TnT UI
        in case of exceptions
        :param calibration_id: Calibration uuid
        :param measurement_points: The amount of measurement points
        :param is_calibration: Boolean value to define if the sequence is to be a calibration or a 
        validation
        :param window_size: Number of samples to use around middle of force press. Negative window size selects given
        index from a list of recorded sample values, i.e. -1 selects last one, -2 second to last one etc.
        :param kwargs: Possible additional arguments
        :return: None
        """
        try:
            if is_calibration:
                self._calibrations[calibration_id]["state"] = "Starting calibration"
            else:
                self._calibrations[calibration_id]["state"] = "Starting validation"

            force_driver = self.robot.force_driver

            measurement_forces = np.linspace(force_driver.min_force, force_driver.max_force,
                                             measurement_points)
            # Add previous calibration data to the calibration dictionary for comparison on UI
            measurement_results = {force: float('nan') for force in measurement_forces}
            calibration = self._calibrations[calibration_id]
            calibration['measurements'] = measurement_results
            
            if is_calibration:
                try:
                    calibration['previous_calibration'] = self.robot.force_calibration_table
                except AttributeError:
                    log.debug('Previous calibration not found')
                    calibration['previous_calibration'] = {}
                calibration['state'] = 'Calibrating'

            for force in measurement_forces:
                self._check_abort(calibration_id)
                log.info('Pressing with force {} g'.format(force))

                self._safe_tare()

                future = self._async.submit(force_driver.force_press, force=force, duration=press_duration,
                                            use_calib=(not is_calibration))

                results = []
                # While the tap is held , collect readings from force sensor
                while not future.done():
                    results.append(self._sensor.read_tared_force())

                error = future.exception()
                if error:
                    raise NodeException(title='Exception occurred during press gesture: {}'.format(str(error)))
                else:
                    sample_window = window_size if window_size is not None else \
                        force_driver.force_calibration_window_size
                    if sample_window < 0:
                        # Select single sample from given list index
                        windowed_results = results[sample_window]
                    else:
                        windowed_results = window_force_data(results, sample_window,
                                                             force_threshold=self._force_threshold,
                                                             max_rel_variation=self._max_rel_variation,
                                                             max_abs_variation=self._max_abs_variation)

                    # Calculate the mean from the windowed data to filter out any possible skewing by set point
                    # dynamics
                    measurement_results[force] = np.nanmean(windowed_results)

            if is_calibration:
                self._calibrations[calibration_id]["results"] = self._to_force_calibration(measurement_results)

            calibration['state'] = 'Ready'
                
        except NodeException as e:
            log.warning("Calibration / validation was cancelled: %s, %s", e.title, e.messages)
            self._calibrations[calibration_id]["state"] = "Cancelled"
            self._calibrations[calibration_id]["error"] = e.title
            self._calibrations[calibration_id]["error_messages"] = e.messages
        except Exception as e:
            log.exception('Exception during calibration / validation')
            self._calibrations[calibration_id]['state'] = 'Error'
            self._calibrations[calibration_id]['error'] = str(e)

    @json_out
    def put_calibrate(self, axis_name=None, press_duration=None):
        """
        Perform force calibration synchronously.
        :param axis_name: Name of axis to calibrate for force. None to use the default.
        :param press_duration: Press duration during calibration. If None, then default configured value is used.
        :return: Dict which contains finished force calibration.
        """
        if axis_name is None:
            axis_name = self.robot.force_driver.axis

        if press_duration is None:
            press_duration = self._press_duration

        calibration_id = self._add_calibration(axis_name)
        self.sequence = self._force_sequence(calibration_id, measurement_points=5, is_calibration=True,
                                             press_duration=press_duration)
        return self._calibrations[calibration_id]

    @json_out
    def post_calibrate(self, axis_name=None, press_duration=None):
        """
        Perform force calibration asynchronously.
        :param axis_name: Name of axis to calibrate for force. None to use the default.
        :param press_duration: Press duration during calibration. If None, then default configured value is used.
        :return: Dict which contains finished force calibration.
        """
        if axis_name is None:
            axis_name = self.robot.force_driver.axis

        if press_duration is None:
            press_duration = self._press_duration

        calibration_id = self._add_calibration(axis_name)
        self._calibrations[calibration_id]['state'] = 'Starting calibration'
        self._async.submit(self._force_sequence, calibration_id,
                           measurement_points=5, is_calibration=True, press_duration=press_duration)
        return self._calibrations[calibration_id]

    @json_out
    def post_validate(self, axis_name=None, validation_points=5, press_duration=None):
        """
        Perform force calibration asynchronously.
        :param axis_name: Name of axis whose force to validate. None to use the default.
        :param validation_points: Number of validation points to use.
        :param press_duration: Press duration during validation. If None, then default configured value is used.
        :return: Dict which contains finished force calibration.
        """
        if axis_name is None:
            axis_name = self.robot.force_driver.axis

        if press_duration is None:
            press_duration = self._press_duration

        validation_points = int(validation_points)
        calibration_id = self._add_calibration(axis_name)
        self._async.submit(self._force_sequence, calibration_id,
                           validation_points, is_calibration=False, press_duration=press_duration)
        return self._calibrations[calibration_id]

    @json_out
    def get_calibration_status(self, calibration_id):
        """
        Returns the calibration dictionary
        :param calibration_id: Calibration uuid
        :return: Dict which contains force calibration information e.g. state, possible error with messages,
        measurements, previous calibration results
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
        :return: Dict which contains the stopped force calibration.
        """
        if calibration_id in self._calibrations:
            self._calibrations[calibration_id]["abort"] = True
        return self._calibrations[calibration_id]

    @json_out
    def put_stop_validation(self, calibration_id):
        """
        Called from the UI when user wants to cancel the calibration
        :param calibration_id: Calibration uuid
        :return: Dict which contains the stopped force validation.
        """
        if calibration_id in self._calibrations:
            self._calibrations[calibration_id]["abort"] = True
        return self._calibrations[calibration_id]

    @json_out
    def put_save_calibration(self, calibration_id):
        """
        Saves the corresponding calibration data to the server configuration file
        :param calibration_id: Calibration uuid
        :return: None
        """
        if calibration_id in self._calibrations:
            # Set entire table to make sure the property setter is called.
            calibration_table = self.robot.force_calibration_table
            axis_name = self._calibrations[calibration_id]["axis"]
            calibration_table[axis_name] = self._calibrations[calibration_id]["results"]
            self.robot.force_calibration_table = calibration_table
            self.robot.save()
