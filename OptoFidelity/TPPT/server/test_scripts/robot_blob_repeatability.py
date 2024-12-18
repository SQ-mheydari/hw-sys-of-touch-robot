"""
Script for measuring robot homing and movement repeatability using camera as absolute position reference.
Requires:
- Stationary camera located so that robot effector can be moved within camera view.
- Robot effector has a blob target i.e. white paper with black disk on it.
- TnT Client.
Test parameters must be defined so that blob detection is successful in given conditions.
"""
import time
import cv2
import numpy as np
import logging
import json
import random

log = logging.getLogger(__name__)

try:
    from tntclient.tnt_client import TnTClient
except ImportError:
    log.error("TnT Client not found!")


def filter_contours(contours, img_width, img_height, min_size, max_size):
    best_cont = None
    min_center_dist_sq = float('inf')

    filtered = []

    # Find contour whose size meets given size criteria and is closest to image center.
    for cont in contours:
        x, y, w, h = cv2.boundingRect(cont)

        # Compute squared distance.
        dist_sq = (x + w / 2 - img_width / 2) ** 2 + (y + w / 2 - img_height / 2) ** 2

        if dist_sq < min_center_dist_sq and w > min_size and h > min_size and w < max_size and h < max_size:
            min_center_dist_sq = dist_sq
            best_cont = cont

    filtered.append(best_cont)

    return filtered


def verify_detect_blob(exposure, gain, blob_threshold, min_blob_scale, max_blob_scale):
    client = TnTClient()
    camera = client.camera("Camera1")

    # It is assumed that this image has black blob on white background (printed target).
    image = camera.take_still(filetype="jpg", undistorted=True, exposure=exposure, gain=gain)
    image = np.frombuffer(image, dtype='uint8')
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)

    if len(image.shape) > 2:
        # Color image received, convert to grayscale
        img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        img = image

    #img = cv2.imread("blob.png", 0)

    # Invert colors to get white blob on black background.
    img = cv2.bitwise_not(img)

    # Threshold image to remove excess background shapes.
    image = cv2.threshold(img, blob_threshold, 255, cv2.THRESH_BINARY)[1]
    h, w = image.shape[:2]

    _, contours, _ = cv2.findContours(image, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    contours = filter_contours(contours, w, h, w * min_blob_scale, w * max_blob_scale)

    image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    cv2.drawContours(image, contours, -1, (0, 255, 0), 3)

    log.info(w)
    image = cv2.resize(image, (int(w / 6), int(h / 6)))

    cv2.imshow('image', image)
    cv2.waitKey(0)


def detect_blob(image, blob_threshold=150, min_blob_scale=1/20, max_blob_scale=1/4):
    """
    Detect dark blob on white background from the image.
    """

    if len(image.shape) > 2:
        # Color image received, convert to grayscale
        img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        img = image

    # Write image to file to tune contour filtering.
    #cv2.imwrite("blob.png", img)

    # Invert image as opencv detects white blobs on black background.
    img = cv2.bitwise_not(img)

    # Binary threshold for specific lighting conditions.
    image = cv2.threshold(img, blob_threshold, 255, cv2.THRESH_BINARY)[1]
    img_height, img_width = image.shape

    _, contours, _ = cv2.findContours(image, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    if contours is None or len(contours) == 0:
        log.debug("No contours in image, cannot detect blob")
        return None

    contours = filter_contours(contours, img_width, img_height, img_width * min_blob_scale, img_width * max_blob_scale)

    # Use blob bounding rectangle center as reference position.
    x, y, w, h = cv2.boundingRect(contours[0])

    cx = x + w / 2 + 0.5
    cy = y + h / 2 + 0.5

    # Compute difference to image center.
    diff_x = cx - float(img_width) / 2.0
    diff_y = cy - float(img_height) / 2.0

    log.debug("detect_blob: cx={}, cy={}, diff_x={}, diff_y={}".format(cx, cy, diff_x, diff_y))

    return diff_x, diff_y


def center_blob(robot, camera, ppmm, max_delta=0.01, max_iterations=20, wait_duration=1.0, move_range=20.0,
                exposure=0.1, gain=1, blob_threshold=150, min_blob_scale=1/20, max_blob_scale=1/4):
    """
    Move the robot so that dark blob near camera center is centered.
    """

    start_x, start_y = get_robot_xy(robot, "tnt")

    for i in range(max_iterations):
        image = camera.take_still(filetype="jpg", undistorted=True, exposure=exposure, gain=gain)
        image = np.frombuffer(image, dtype='uint8')
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)

        result = detect_blob(image, blob_threshold, min_blob_scale, max_blob_scale)

        if result is None:
            raise Exception("Cannot find blob.")

        x_px, y_px = result

        x_mm = -x_px / ppmm
        y_mm = -y_px / ppmm

        # Check if we are done
        if (abs(x_mm) <= max_delta) and (abs(y_mm) <= max_delta):
            return

        current_x, current_y = get_robot_xy(robot, "tnt")

        # Limit move range in case blob is incorrectly detected far away.
        if abs(current_x + x_mm - start_x) > move_range or abs(current_y + y_mm - start_y) > move_range:
            raise Exception("Attempt to move beyond moving range")

        log.info("Step {} / {}: moving x: {} mm, y: {} mm".format(i, max_iterations, x_mm, y_mm))

        robot.move_relative(x=x_mm, y=y_mm)

        # Sleep for a while to make sure the camera image is updated to new camera position.
        # The required time depends on camera refresh rate.
        time.sleep(wait_duration)

    log.warning("Exceeded max iterations")


def get_robot_xy(robot, context):
    position = robot.get_position(context)["position"]

    x, y = position["x"], position["y"]

    return x, y


def create_grid(x1, x2, y1, y2, z, nx, ny):
    positions = []

    for j in range(ny):
        y = y1 + (y2 - y1) * j / (ny - 1)

        for i in range(nx):
            x = x1 + (x2 - x1) * i / (nx - 1)

            positions.append((x, y, z))

    return positions


def measure_homing_repeatability(parameters, output_filename):
    """
    Loop following sequence:
    - Home robot from a predefined start position
    - Move at predefined position where blob is visible near camera center
    - Move robot until blob is detected at camera center
    - Record robot position

    Compute standard deviation of recorded robot x and y positions.
    """

    client = TnTClient()
    robot = client.robot("Robot1")
    camera = client.camera("Camera1")

    ppmm = camera.get_property("ppmm")

    start_positions = create_grid(10, 70, 20, 130, 0, 5, 5)
    #start_positions = [(40, 150, 0)]

    # Set some robot speed.
    robot.set_speed(parameters["speed"], parameters["acceleration"])

    data = {
        "parameters": parameters,
        "data": []
    }

    start_time = time.time()

    for j, start_position in enumerate(start_positions):
        log.info("Executing position {} / {}".format(j + 1, len(start_positions)))

        x_positions = []
        y_positions = []
        x_stdev = 0
        y_stdev = 0
        result = "ok"

        i = 0

        while i < parameters["repeat_count"]:
            log.info("Executing homing repeatability step {} / {}".format(i + 1, parameters["repeat_count"]))

            try:
                robot.move(*start_position)
                time.sleep(parameters["wait_duration"])

                robot.go_home()
                time.sleep(parameters["wait_duration"])

                # Move to predetermined position where blob is near camera center.
                robot.move(*parameters["imaging_position"])

                # Move robot until blob is at camera center.
                center_blob(robot,
                            camera,
                            ppmm,
                            max_delta=parameters["max_delta"],
                            max_iterations=parameters["max_iterations"],
                            wait_duration=parameters["wait_duration"],
                            move_range=parameters["move_range"],
                            exposure=parameters["exposure"],
                            gain=parameters["gain"],
                            blob_threshold=parameters["blob_threshold"],
                            min_blob_scale=parameters["min_blob_scale"],
                            max_blob_scale=parameters["max_blob_scale"])

                # Get robot (x, y) position.
                x, y = get_robot_xy(robot, "tnt")
                x_positions.append(x)
                y_positions.append(y)

                # Compute standard deviations from points obtained thus far.
                x_stdev = np.std(x_positions)
                y_stdev = np.std(y_positions)

                log.info("x stdev: {} mm".format(x_stdev))
                log.info("y stdev: {} mm".format(y_stdev))

                log.info("x 3-sigma: {} mm".format(x_stdev * 3))
                log.info("y 3-sigma: {} mm".format(y_stdev * 3))

                i += 1
            except Exception as e:
                result = "error: " + str(e)
                log.error(str(e))


        data["data"].append({
            "start_position": start_position,
            "x_stdev": x_stdev,
            "y_stdev": y_stdev,
            "result": result,
            "x_positions": x_positions,
            "y_positions": y_positions
        })

        if output_filename is not None:
            with open(output_filename, "w") as file:
                json.dump(data, file, sort_keys=True, indent=4, separators=(',', ': '))

        current_time = time.time()
        elapsed_time = current_time - start_time

        log.info("Elapsed time: {} min".format(elapsed_time / 60))


def measure_movement_repeatability(parameters, output_filename):
    """
    Measure how much robot position drifts after series of movements.
    """

    client = TnTClient()
    robot = client.robot("Robot1")
    camera = client.camera("Camera1")

    ppmm = camera.get_property("ppmm")

    grid = create_grid(10, 70, 10, 130, 0, 5, 5)

    # List of tuples (speed, acceleration).
    robot_speeds = parameters["speed_acceleration"]

    data = {
        "parameters": parameters,
        "data": []
    }

    start_time = time.time()

    robot.go_home()

    for j, (speed, acceleration) in enumerate(robot_speeds):
        log.info("Executing position {} / {}".format(j + 1, len(robot_speeds)))

        x_positions = []
        y_positions = []
        x_stdev = 0
        y_stdev = 0
        result = ""

        i = 0

        while i < parameters["repeat_count"]:
            log.info("Executing movement repeatability step {} / {}".format(i + 1, parameters["repeat_count"]))

            try:
                robot.set_speed(speed, acceleration)

                # Do random movements in workspace.
                for _ in range(parameters["num_movements"]):
                    ix = random.randint(0, len(grid) - 1)
                    pos = grid[ix]

                    robot.move(pos[0], pos[1], pos[2])

                log.info("Determining robot position")

                # Use fixed speed for blob centering.
                robot.set_speed(parameters["blob_centering_speed"], parameters["blob_centering_acceleration"])

                # Move to predetermined position where blob is near camera center.
                robot.move(*parameters["imaging_position"])

                # Move robot until blob is at camera center.
                center_blob(robot,
                            camera,
                            ppmm,
                            max_delta=parameters["max_delta"],
                            max_iterations=parameters["max_iterations"],
                            wait_duration=parameters["wait_duration"],
                            move_range=parameters["move_range"],
                            exposure=parameters["exposure"],
                            gain=parameters["gain"],
                            blob_threshold=parameters["blob_threshold"],
                            min_blob_scale=parameters["min_blob_scale"],
                            max_blob_scale=parameters["max_blob_scale"])

                # Get robot (x, y) position.
                x, y = get_robot_xy(robot, "tnt")
                x_positions.append(x)
                y_positions.append(y)

                # Compute standard deviations from points obtained thus far.
                x_stdev = np.std(x_positions)
                y_stdev = np.std(y_positions)

                log.info("x stdev: {} mm".format(x_stdev))
                log.info("y stdev: {} mm".format(y_stdev))

                log.info("x 3-sigma: {} mm".format(x_stdev * 3))
                log.info("y 3-sigma: {} mm".format(y_stdev * 3))

                i += 1
            except Exception as e:
                result += "error: {}, ".format(str(e))
                log.error(str(e))

        if len(result) == 0:
            result = "ok"

        data["data"].append({
            "speed": speed,
            "acceleration": acceleration,
            "x_stdev": x_stdev,
            "y_stdev": y_stdev,
            "result": result,
            "x_positions": x_positions,
            "y_positions": y_positions
             })

        if output_filename is not None:
            with open(output_filename, "w") as file:
                json.dump(data, file, sort_keys=True, indent=4, separators=(',', ': '))

        current_time = time.time()
        elapsed_time = current_time - start_time

        log.info("Elapsed time: {} min".format(elapsed_time / 60))


def analyze_homing_repeatability(filename):
    """
    Load homing repeatability data from file and print results.
    :param filename: Name of JSON file.
    """

    with open(filename, "r") as file:
        data = json.load(file)

    max_stdev_x = 0
    max_stdev_x_start_position = None
    max_stdev_y = 0
    max_stdev_y_start_position = None

    for item in data["data"]:
        result = item["result"]
        start_position = item["start_position"]

        if result != "ok":
            log.error("There was error: " + result + " at location ({}, {})".format(start_position[0], start_position[1]))

    for item in data["data"]:
        result = item["result"]

        if result != "ok":
            continue

        start_position = item["start_position"]
        x_stdev = item["x_stdev"]
        y_stdev = item["y_stdev"]

        log.info("({}, {}) stdev x {} stdev y {}".format(start_position[0], start_position[1], x_stdev, y_stdev))

        if x_stdev > max_stdev_x:
            max_stdev_x_start_position = start_position

        if y_stdev > max_stdev_y:
            max_stdev_y_start_position = start_position

        max_stdev_x = max(max_stdev_x, x_stdev)
        max_stdev_y = max(max_stdev_y, y_stdev)

    log.info("Maximum stdev x {} at start position ({}, {})".format(max_stdev_x, max_stdev_x_start_position[0],
                                                                 max_stdev_x_start_position[1]))
    log.info("Maximum stdev y {} at start position ({}, {})".format(max_stdev_y, max_stdev_y_start_position[0],
                                                                 max_stdev_y_start_position[1]))


def analyze_movement_repeatability(filename):
    """
    Load movement repeatability data from file and print results.
    :param filename: Name of JSON file.
    """

    with open(filename, "r") as file:
        data = json.load(file)

    max_stdev_x = 0
    max_stdev_x_speed_accel = None
    max_stdev_y = 0
    max_stdev_y_speed_accel = None

    for item in data["data"]:
        result = item["result"]
        speed = item["speed"]
        acceleration = item["acceleration"]

        if result != "ok":
            log.error("There was error: " + result + " at speed {} and acceleration {}.".format(speed, acceleration))

    for item in data["data"]:
        result = item["result"]

        if result != "ok":
            continue

        speed = item["speed"]
        acceleration = item["acceleration"]
        x_stdev = item["x_stdev"]
        y_stdev = item["y_stdev"]

        log.info("{} mm/s {} mm/s^2: stdev x {} stdev y {}".format(speed, acceleration, x_stdev, y_stdev))

        if x_stdev > max_stdev_x:
            max_stdev_x_speed_accel = (speed, acceleration)

        if y_stdev > max_stdev_y:
            max_stdev_y_speed_accel = (speed, acceleration)

        max_stdev_x = max(max_stdev_x, x_stdev)
        max_stdev_y = max(max_stdev_y, y_stdev)

    log.info(
        "Maximum stdev x {} at speed {} mm/s and acceleration {} mm/s^2".format(max_stdev_x, max_stdev_x_speed_accel[0],
                                                                                max_stdev_x_speed_accel[1]))
    log.info(
        "Maximum stdev y {} at speed {} mm/s and acceleration {} mm/s^2".format(max_stdev_y, max_stdev_y_speed_accel[0],
                                                                                max_stdev_y_speed_accel[1]))

if __name__ == "__main__":
    # Use this function to determine proper base parameters.
    # verify_detect_blob(exposure=0.12, gain=1, blob_threshold=150, min_blob_scale=1/20, max_blob_scale=1/4)

    base_parameters = {
        # Camera exposure in seconds.
        "exposure": 0.12,
        # Camera gain.
        "gain": 1,
        # How much position error in mm is allowed when centering blob to camera.
        "max_delta": 0.02,
        # How long to wait in seconds after robot movements so that movement and camera image are stabilized.
        "wait_duration": 1.0,
        # Maximum range robot can be moved when centering blob to camera.
        "move_range": 20.0,
        # Robot effector position in workspace where blob is close the camera center.
        "imaging_position": (39, 69, 0),
        # Blob threshold factor in range [0, 255]. Values below are clamped to black and values above clamped to white.
        "blob_threshold": 150,
        # Minimum blob diameter in relation to camera image size.
        "min_blob_scale": 1 / 20,
        # Maximum blob diameter in relation to camera image size.
        "max_blob_scale": 1 / 4,
        # Robot speed when centering blob.
        "blob_centering_speed": 50,
        # Robot acceleration when centering blob.
        "blob_centering_acceleration": 100,
        # Maximum number of iterations when centering blob.
        "max_iterations": 20
    }

    homing_parameters = {
        "description": "Homing repeatability",
        "repeat_count": 2,
        "speed": 50,
        "acceleration": 100
    }
    homing_parameters.update(base_parameters)

    measure_homing_repeatability(homing_parameters, "hrep.json")

    movement_parameters = {
        "description": "Movement repeatability",
        "num_movements": 5,
        "repeat_count": 30,
        "speed_acceleration": [(50, 100), (100, 400), (250, 800)]
    }
    movement_parameters.update(base_parameters)

    measure_movement_repeatability(movement_parameters, "mrep.json")

