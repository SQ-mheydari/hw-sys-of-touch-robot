"""
Test scripts for measuring force accuracy, repeatability, overshoot etc.
"""
import time
import os
import json
import csv
from tqdm import tqdm

from client.tntclient.tnt_client import TnTClient
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt


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


def write_json(path, data):
    """
    Write dictionary to JSON file with some formatting.
    :param path: Path to file.
    :param data: Dictionary of data.
    """
    with open(path, "w") as file:
        json.dump(data, file, sort_keys=True, indent=1, separators=(',', ': '))


def measure_press_force(parameters):
    print("Measuring forces.")

    client = TnTClient()
    futek_dut = client.dut(parameters["futek_dut_name"])
    futek = client.futek("futek")

    parameters["tnt_version"] = client.version()

    now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    dir = os.path.join(parameters["output_directory"], now)

    os.mkdir(dir)
    output_filename = os.path.join(dir, "results.json")

    data = []

    futek_dut.jump(0, 0, 10)

    # Loop through list of forces.
    for ix_force in tqdm(range(len(parameters["forces"]))):
        force = parameters["forces"][ix_force]
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
                    futek.tare(timeout_s=10)
                    futek.start_buffering(duration=100.0)

                    futek_dut.press(0, 0, force, duration=parameters["press_duration"])

                    futek.stop_buffering()

                    #plt.plot(futek.buffer())
                    #plt.show()

                    measurement_filename = os.path.join(dir, f"force{ix_force}_press{ix_press}_meas.csv")
                    measured_forces.append(measurement_filename)

                    with open(measurement_filename, "w") as file:
                        for f in futek.buffer():
                            file.write(str(f) + "\n")

                    break
                except Exception as e:
                    #raise e
                    print("Error: {}. Retrying.".format(str(e)))

        data.append(result)

        write_json(output_filename, {
            "parameters": parameters,
            "data": data
        })


def print_row(header, values, tab_size=20):
    print(header.ljust(tab_size), end='')

    for value in values:
        if isinstance(value, float):
            print("{:.2f}".format(value).ljust(tab_size), end='')
        else:
            print("{}".format(str(value).ljust(tab_size)), end='')

    print("")


def analyze_results(path):
    with open(path, "r") as file:
        results = json.load(file)

    data = results["data"]
    parameters = results["parameters"]

    analysis_results = []

    for force_results in data:
        press_force = force_results["press_force"]

        measured_press_forces = []
        max_force = 0

        for press_ix, measurement_filename in enumerate(force_results["measured_forces"]):

            with open(measurement_filename, "r") as file:
                reader = csv.reader(file)

                measured_forces = [float(row[0]) for row in reader]

            #plt.plot(measured_forces)
            #plt.show()

            windowed_forces = window_force_data(measured_forces, press_force)

            # Compute mean of the windowed force measurements to determine the force measurement
            # corresponding to press_force.
            mean_force = np.mean(windowed_forces)
            measured_press_forces.append(mean_force)
            max_force = max(max_force, max(measured_forces))

        # Compute the accuracy as the absolute difference of press_force and
        # the mean of measured presses (e.g. 30 repetitions).
        measured_press_forces = np.array(measured_press_forces)
        accuracy = abs(np.mean(measured_press_forces) - press_force)

        repeatability = 3 * np.std(measured_press_forces)

        # Compute overshoot as difference of maximum measured force and the target press force.
        # Note that sometimes overshoot is defined in relation to steady state force.
        overshoot = max_force - press_force

        analysis_results.append({
            "Force (g)": press_force,
            "Accuracy (g)": accuracy,
            "Accuracy (%)": accuracy / press_force * 100,
            "Repeatability (g)": repeatability,
            "Repeatability (%)": repeatability / press_force * 100,
            "Overshoot (g)": overshoot,
            "Overshoot (%)": overshoot / press_force * 100
        })

    for key in analysis_results[0].keys():
        print_row(key, [x[key] for x in analysis_results])


if __name__ == "__main__":
    parameters = {
        "speed": 100,
        "acceleration": 400,
        "futek_dut_name": "force",
        "output_directory": "C:\\OptoFidelity\\force_results",
        "forces": [25, 50, 100, 150, 200, 250, 300, 400, 500, 600],
        "num_presses": 30,
        "press_duration": 2
    }

    #measure_press_force(parameters)
    analyze_results(os.path.join("C:\\OptoFidelity\\force_results", "2021-09-07-12-34-42", "results.json"))
