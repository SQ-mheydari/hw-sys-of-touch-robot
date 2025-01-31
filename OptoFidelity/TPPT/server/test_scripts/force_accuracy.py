"""
Script for measuring and analyzing force accuracy and repeatability over time period
by performing press gestures against Futek. Taps and swipes against DUT can be done
between force measurements to see if they affect the results. Force can be calibrated
periodically to see how it affects the results.

The top left corner of Futek DUT is used as measurement location. This should be precisely at the center
of the Futek sensor.

Requirements:
- Robot with force support.
- Futek sensor.
- TnT Client with Futek and force calibration clients.
"""
import time
import os
import json
import random

import matplotlib.pyplot as plt

from tntclient.tnt_client import TnTClient
from tntclient.tnt_force_calibrator_client import TnTForceCalibratorClient
from tntclient.tnt_futek_client import TnTFutekClient
import numpy as np
from random import randrange
import threading

class TnTDutClientSimulator:
    """
    Dummy client class for DUT.
    """
    def __init__(self, name):
        self.name = name
        self.width = 10
        self.height = 10

    def jump(self, x, y, z):
        pass

    def press(self, x, y, force, duration=1.0):
        pass

    def tap(self, x, y, clearance=0):
        pass

    def watchdog_tap(self, x, y, clearance=0):
        pass

    def swipe(self, x1, y, x2, y2, clearance=0):
        pass

    def drag(self, x1, y, x2, y2, clearance=0):
        pass


class TnTRobotClientSimulator:
    """
    Dummy client class for robot.
    """
    def __init__(self, name):
        self.name = name

    def set_speed(self, speed, acceleration):
        pass


class TnTClientSimulator:
    """
    Dummy client class for TnT.
    """
    def __init__(self):
        pass

    def dut(self, name):
        return TnTDutClientSimulator(name)

    def robot(self, name):
        return TnTRobotClientSimulator(name)


def window_force_data(data, target_force, force_margin_factor=0.1, window_factor=0.5):
    """
    Get force measurement results from a window where transient values have been removed.
    Window is found within the rising and falling edges of expected force values.
    :param target_force: Known target force estimate where the measurement values should be located.
    :param force_margin_factor: Margin of the target force. This defines where the edges are detected.
    :param window_factor: Factor of window within the rising and falling edges.
    """

    # Get data indices that define a window where data values exceed target force.
    ix0 = np.argmax(np.greater(data, target_force * (1 - force_margin_factor)))
    ix1 = len(data) - np.argmax(np.greater(data[::-1], target_force * (1 - force_margin_factor)))

    if ix0 > ix1:
        raise Exception("Could not correctly determine force data window.")

    results = data[ix0:ix1]

    window_size = int(round(len(results) * window_factor)) // 2

    nresults = len(results)
    middle = nresults // 2

    window_ix0 = max(0, middle - window_size)
    window_ix1 = min(nresults, middle + window_size)

    windowed_results = results[window_ix0:window_ix1]

    if len(windowed_results) < 100:
        print("Warning: number of force measurements {} is less than 100.".format(len(windowed_results)))

    return [value for value in windowed_results if not np.isnan(value)]


class ForceReader:
    """
    Read Futek force values in a thread.
    """
    def __init__(self, client, simulator=False):
        self._simulator = simulator
        self.simulated_force = 0.0

        self.futek = client.futek("futek") if not simulator else None

        self._reading = False
        self._thread = None
        self._results = []

    def _read_values(self):
        while self._reading:
            if self.futek is not None:
                value = self.futek.forcevalue()
                #print(value)
            else:
                value = random.uniform(self.simulated_force * 0.9, self.simulated_force * 1.1)

            if value is not None:
                self._results.append(value)

    def start_reading(self):
        print("Taring Futek.")

        if self.futek is not None:
            self.futek.tare()
            #self.futek.tare(window_size=200, gram_diff=1)

        print("Starting force measurement.")

        self._reading = True
        self._results = []
        self._thread = threading.Thread(target=self._read_values)
        self._thread.start()

    def stop_reading(self):
        self._reading = False
        self._thread.join()

        print("Finished force measurement.")

    def get_results(self):
        return self._results

    def get_windowed_results(self, target_force, force_margin_factor=0.1, window_factor=0.5):
        """
        Get force measurement results from a window where transient values have been removed.
        Window is found within the rising and falling edges of expected force values.
        :param target_force: Known target force estimate where the measurement values should be located.
        :param force_margin_factor: Margin of the target force. This defines where the edges are detected.
        :param window_factor: Factor of window within the rising and falling edges.
        """

        return window_force_data(self._results, target_force, force_margin_factor, window_factor)


def generate_random_swipe(dut):
    """
    Generate random start and end points for swipes and drags.
    """
    # Swipe is valid when start and end points are different
    while True:
        start_point = (randrange(0, int(dut.width)), randrange(0, int(dut.height)))
        end_point = (randrange(0, int(dut.width)), randrange(0, int(dut.height)))

        if start_point[0] != end_point[0] and start_point[1] != end_point[1]:
            return start_point, end_point


def measure_press_force(parameters, force_reader, futek_dut):
    """
    Measure force during press gestures.
    :param parameters: Dictionary of parameters for the test.
    :param force_reader: ForceReader object that has been initialized.
    :param futek_dut: DUT client for Futek device. Top left corner must be the sensor center.
    :return: Press forces and corresponding measured force mean, median and stdev.
    """
    print("Measuring forces.")

    data = []

    futek_dut.jump(0, 0, 10)

    # Loop through list of forces.
    for ix_force, force in enumerate(parameters["forces"]):
        print("Using force {}.".format(force))

        measured_forces = []
        feedback_forces = []

        result = {
            "press_force": force,
            "measured_forces": measured_forces,
            "feedback_forces": feedback_forces
        }

        # Perform repeated press gestures and record force.
        for ix_press in range(parameters["num_presses"]):
            print("Press {} / {}.".format(ix_press + 1, parameters["num_presses"]))

            # Try indefinitely until measurement is successful.
            while True:
                try:
                    force_reader.simulated_force = force
                    force_reader.start_reading()

                    press_feedback = futek_dut.press(0, 0, force, duration=parameters["press_duration"])
                    press_feedback = press_feedback.get("force_feedback_calibrated", None)

                    force_reader.stop_reading()

                    results = force_reader.get_windowed_results(force, force_margin_factor=0.5, window_factor=0.5)

                    # Store mean force.
                    measured_forces.append({"mean": np.mean(results), "median": np.median(results), "stdev": np.std(results), "span": np.max(results)-np.min(results)})

                    print("Futek Mean: {}, Median: {}, Stdev: {}, Span: {}".format(np.mean(results), np.median(results), np.std(results), np.max(results)-np.min(results)))

                    if press_feedback is not None:
                        num_samples = len(press_feedback)

                        # Feedback samples are quite strictly from the duration of the press.
                        # Leave 1/4 out from start and end to avoid possible transients.
                        press_feedback = press_feedback[num_samples//4:3*num_samples//4]

                        feedback_forces.append({"mean": np.mean(press_feedback), "median": np.median(press_feedback),
                                                "stdev": np.std(press_feedback), "span": np.max(press_feedback)-np.min(press_feedback)})

                        print("Feedback Mean: {}, Median: {}, Stdev: {}, Span: {}".format(np.mean(press_feedback), np.median(press_feedback), np.std(press_feedback), np.max(press_feedback)-np.min(press_feedback)))

                    break
                except Exception as e:
                    print("Error: {}. Retrying.".format(str(e)))

        data.append(result)

    return data


def perform_gestures(dut):
    """
    Perform gestures against DUT. This is used to test the effect of gestures on force accuracy
    in the long run.
    :param dut: DUT client object.
    """
    print("Tapping dut.")

    dut.jump(0, 0, 10)

    clearances = [-1, -0.5, 0, 0.5, 1]
    repeat_count = 100

    for clearance in clearances:
        for _ in range(repeat_count):
            dut.tap(dut.width / 2, dut.height / 2, clearance=clearance)

    for clearance in clearances:
        for _ in range(repeat_count):
            dut.watchdog_tap(dut.width / 2, dut.height / 2, clearance=clearance)

    print("Swiping dut.")

    for clearance in clearances:
        for _ in range(repeat_count):
            start, end = generate_random_swipe(dut)

            dut.swipe(start[0], start[1], end[0], end[1], clearance=clearance)

    for clearance in clearances:
        for _ in range(repeat_count):
            start, end = generate_random_swipe(dut)

            dut.drag(start[0], start[1], end[0], end[1], clearance=clearance)


def write_json(path, data):
    """
    Write dictionary to JSON file with some formatting.
    :param path: Path to file.
    :param data: Dictionary of data.
    """
    with open(path, "w") as file:
        json.dump(data, file, sort_keys=True, indent=1, separators=(',', ': '))


def calibrate_force(client, futek_dut):
    """
    Calibrate force with Futek.
    :param client: TnT Client object.
    :param futek_dut: Futek DUT client.
    """
    while True:
        try:
            # Must start approximately 1 mm above Futek.
            futek_dut.jump(0, 0, 1)

            calibrator = TnTForceCalibratorClient("forcecalibrator")

            results = calibrator.calibrate("voicecoil1")

            calibrator.save_calibration(results["calibration_id"], results["axis"])

            break
        except Exception as e:
            print("Error: {}. Retrying".format(str(e)))


def run_force_tests(parameters, simulator=False):
    """
    Run force tests as specified by given parameters.
    :param parameters: Dict of parameters that define the test sequence.
    :param simulator: If True, use dummy TnT Client to run through the test. Useful to test for code errors.
    """
    if simulator:
        client = TnTClientSimulator()
    else:
        client = TnTClient()

    force_reader = ForceReader(client, simulator=simulator)

    robot = client.robot("Robot1")
    robot.set_speed(parameters["speed"], parameters["acceleration"])

    futek_dut = client.dut(parameters["futek_dut_name"])
    dut = client.dut(parameters["dut_name"])

    data_filename = os.path.join(parameters["output_directory"], parameters["output_name"] + "_{}.json".format(time.strftime("%Y%m%d-%H%M%S")))

    data = []

    results = {
        "parameters": parameters,
        "data": data
    }

    # Calibrate before first sequence.
    sequences_since_calibration = parameters["calibration_interval"]

    do_calibrations = parameters["calibration_interval"] >= 0

    sequence_count = 0

    start_time = time.time()

    # Run sequences until time is up.
    while time.time() - start_time < parameters["test_duration"] * 3600:
        sequence_start_time = time.time() - start_time

        print("Testing time {} / {} hours.".format(sequence_start_time / 3600, parameters["test_duration"]))

        if do_calibrations and sequences_since_calibration >= parameters["calibration_interval"]:
            sequences_since_calibration = 0

            print("Calibrating force.")
            calibrate_force(client, futek_dut)
            print("Calibration done.")

        press_results = measure_press_force(parameters, force_reader, futek_dut)

        # Perform gestures to see if they have an effect on force repeatability
        if parameters["gestures"]:
            perform_gestures(dut)

        data.append({
            "results": press_results,
            "sequence_start_time": sequence_start_time
        })

        print("Saving results.")

        write_json(data_filename, results)

        if sequence_count == 0:
            print("Sequence duration: {} s".format(time.time() - start_time))

        sequences_since_calibration += 1
        sequence_count += 1


def analyze_force_tests(path, mode="averaged_error", units="relative"):
    """
    Load data from given path and analyze the results.
    :param path: Path to result file.
    :param mode: Analze mode. One of None, "averaged_error", "error" or "3sigma".
    :param units: Units for showing results. "relative" or "grams".
    """

    with open(path, "r") as file:
        results = json.load(file)

    data = results["data"]

    print("Analyzing measurements.")
    print("Measurement parameters:")

    for key, value in results["parameters"].items():
        print("{}: {}".format(key, value))

    # Dict of lists for each applied force.
    force_mean_abs_errors = {}
    force_std = {}
    force_deviations = {}
    force_abs_errors = {}

    feedback_force_std = {}
    feedback_force_mean_abs_errors = {}

    times = []

    for sequence_data in data:
        results = sequence_data["results"]
        start_time = sequence_data["sequence_start_time"]

        times.append(start_time / 3600)

        # Loop through each press performed in a sequence.
        # results has entries for each varying press force and press is performed N timer for each force value.
        for measurement_data in results:
            press_force = measurement_data["press_force"]

            # Measured forces when press was performed N times with press_force.
            measured_forces = measurement_data["measured_forces"]
            feedback_forces = measurement_data.get("feedback_forces", None)

            # Force value for each press. Note that "mean" here refers to mean of the Futek sensoe
            # values obtained for a single press.
            mean_measured_forces = np.array([f["mean"] for f in measured_forces])

            # Deviation of measured force from the given press force.
            deviations = mean_measured_forces - np.ones((len(mean_measured_forces))) * press_force

            if press_force not in force_mean_abs_errors:
                force_mean_abs_errors[press_force] = []

            scaling = 1.0

            if units == "relative":
                # Convert to percents.
                scaling = 100.0 / press_force

            # Calculate mean of absolute deviations and append to list.
            force_mean_abs_errors[press_force].append(np.mean(np.abs(deviations)) * scaling)

            if press_force not in force_abs_errors:
                force_abs_errors[press_force] = []

            # Calculate abs deviations without averaging over the N presses and append to list.
            force_abs_errors[press_force] += (np.abs(deviations) * scaling).tolist()

            if press_force not in force_std:
                force_std[press_force] = []

            # Calculate force standard deviation of N presses with press_force and append to list.
            force_std[press_force].append(np.std(mean_measured_forces))

            if press_force not in force_deviations:
                force_deviations[press_force] = []

            force_deviations[press_force] += deviations.tolist()

            if feedback_forces is not None:
                mean_feedback_forces = np.array([f["mean"] for f in feedback_forces])
                deviations = mean_feedback_forces - np.ones((len(mean_feedback_forces))) * press_force

                if press_force not in feedback_force_std:
                    feedback_force_std[press_force] = []

                feedback_force_std[press_force].append(np.std(mean_feedback_forces))

                if press_force not in feedback_force_mean_abs_errors:
                    feedback_force_mean_abs_errors[press_force] = []

                feedback_force_mean_abs_errors[press_force].append(np.mean(np.abs(deviations)) * scaling)

    forces = sorted(force_mean_abs_errors.keys())

    if mode is not None:
        for key in forces:
            if mode == "averaged_error":
                # Plot relative error where the deviations are averaged over the N repeated presses.
                value = force_mean_abs_errors[key]

                plt.plot(times, value)
                plt.title("Applied force {} g".format(key))

                if key in feedback_force_mean_abs_errors:
                    plt.plot(times, feedback_force_mean_abs_errors[key], 'r')

                plt.xlabel("Time (h)")

                if units == "relative":
                    plt.ylabel("Relative force mean absolute error")
                else:
                    plt.ylabel("Force mean absolute error (g)")
                plt.show()
            elif mode == "error":
                # Plot relative errors without averaging.
                value = force_abs_errors[key]

                plt.plot(value)

                plt.title("Applied force {} g".format(key))
                plt.xlabel("Press count")

                if units == "relative":
                    plt.ylabel("Relative force absolute error")
                else:
                    plt.ylabel("Force absolute error (g)")
                plt.show()
            elif mode == "3sigma":
                # Plot 3-sigma deviations of N repeated presses.
                value = force_std[key] * 3

                plt.plot(value)

                if key in feedback_force_std:
                    plt.plot(feedback_force_std[key] * 3, 'r')

                plt.title("Applied force {} g".format(key))
                plt.xlabel("Press count")
                plt.ylabel("3-sigma deviation (g)")
                plt.show()

    if units == "relative":
        print("Force errors in percents:")
    else:
        print("Force errors in grams:")

    print_row("force", forces)

    print_row("mean", [np.mean(force_abs_errors[force]) for force in forces])
    print_row("median", [np.median(force_abs_errors[force]) for force in forces])
    print_row("max", [np.max(force_abs_errors[force]) for force in forces])

    if units != "relative":
        print_row("3-sigma", [3 * np.sqrt(np.mean(np.array(force_deviations[force])**2)) for force in forces])


def print_row(header, values, tab_size=12):
    print(header.ljust(tab_size), end='')

    for value in values:
        if isinstance(value, float):
            print("{:.2f}".format(value).ljust(tab_size), end='')
        else:
            print("{}".format(str(value).ljust(tab_size)), end='')

    print("")

def inspect_force(duration):
    client = TnTClient()
    force_reader = ForceReader(client)

    force_reader.start_reading()
    time.sleep(duration)
    force_reader.stop_reading()

    results = force_reader.get_results()
    plt.plot(results)
    plt.show()


def inspect_press_force(futek_dut_name, force, duration):
    """
    Utility function to inspect force readings given byt Futek when robot performs press gesture.
    This can be useful to determine if the windowing for force data collection works correctly.
    :param futek_dut_name: Futek DUT client. Top left must be the sensor center.
    :param force: Force in grams to apply with press.
    :param duration: Press duration in seconds.
    """
    client = TnTClient()
    force_reader = ForceReader(client)

    futek_dut = client.dut(futek_dut_name)

    #futek_dut.jump(0, 0, 10)

    force_reader.start_reading()

    press_feedback = futek_dut.press(0, 0, force, duration=duration)
    press_feedback = press_feedback["force_feedback_calibrated"]

    force_reader.stop_reading()

    #results = force_reader.get_windowed_results(force, force_margin_factor=0.5, window_factor=0.5)
    results = force_reader.get_results()

    print(len(results))

    #results = force_reader.get_results()
    plt.plot(results)
    plt.show()

    if press_feedback is not None:
        num_samples = len(press_feedback)
        press_feedback = press_feedback[num_samples//4:3*num_samples//4]
        plt.plot(press_feedback)
        plt.show()


def inspect_tap_force(futek_dut_name, clearance, duration):
    client = TnTClient()
    force_reader = ForceReader(client)

    futek_dut = client.dut(futek_dut_name)

    #futek_dut.jump(0, 0, 10)

    results = []

    for _ in range(10):
        force_reader.start_reading()
        futek_dut.tap(0, 0, clearance=clearance, duration=duration)
        force_reader.stop_reading()
        results += force_reader.get_results()

    #results = force_reader.get_windowed_results(force, force_margin_factor=0.5, window_factor=0.5)

    print(len(results))

    #results = force_reader.get_results()
    plt.plot(results)
    plt.show()


if __name__ == "__main__":
    parameters = {
        "speed": 80,
        "acceleration": 400,
        "dut_name": "dut1",
        "futek_dut_name": "force",
        "output_directory": "C:\\OptoFidelity\\force_results",
        "output_name": "force_test",
        "forces": [10, 25, 50, 100, 150, 200, 300, 400, 500, 600, 700, 800],
        "num_presses": 10,
        "press_duration": 2,
        "test_duration": 2.0,
        "gestures": False,
        "calibration_interval": -1  # In number of sequences. -1 to not calibrate.
    }

    #inspect_force(duration=30)
    #inspect_tap_force("force", clearance=-2, duration=15)
    #inspect_press_force("force", 50, 2)
    #run_force_tests(parameters, simulator=False)
    analyze_force_tests("E:\\force_test_20210201-145326.json", None, "relative")
