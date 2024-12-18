"""
Scripts for measuring homing offsets for tilt and azimuth joints using Leica.

Install required packages:
- numpy
- matplotlib
- tntclient (usually already installed to delivery PC)
- pylmf (found in optofidelity local pypi)

See the main block at the end of file to set Leica and robot settings.
"""
import logging
log = logging.getLogger(__name__)

try:
    from pylmf.tracker import LaserTracker
except ImportError:
    log.error("pylmf not found!")

import random
import numpy as np
import json

import matplotlib.pyplot as plt

try:
    from tntclient.tnt_client import TnTClient
except ImportError:
    log.error("TnT Client not found!")


# Only show warnings
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Disable all child loggers of urllib3, e.g. urllib3.connectionpool
logging.getLogger("urllib3").propagate = False


def project_direction_to_plane(dir, plane_normal):
    """
    Project direction vector to a plane with given normal vector and normalize result.
    """
    dir = dir - np.dot(dir, plane_normal) * plane_normal

    return dir / np.linalg.norm(dir)


def direction_from_points(points):
    """
    Determine direction vector from point data.
    :param points: Numpy array of 3D points.
    :return: Normalized direction vector.
    """
    mean_point = np.mean(points, axis=0)

    uu, dd, vv = np.linalg.svd(points - mean_point)

    dir = vv[0, :]

    # Point data may not have any order so dir could also be -dir.
    # Assume that points are roughly ordered and assume that the first and last points
    # define a generally correct direction.
    ref_dir = points[-1, :] - points[0, :]

    if np.dot(dir, ref_dir) < 0:
        dir = -dir

    dir = dir / np.linalg.norm(dir)

    return dir


def plane_from_points(points):
    """
    Determine plane from given points.
    Plane is defined by dot(normal, point) + d = 0 where point is any point on the plane.
    """
    mean_point = np.mean(points, axis=0)

    uu, dd, vv = np.linalg.svd(points - mean_point)

    dir1 = vv[0, :]
    dir2 = vv[1, :]

    normal = np.cross(dir1, dir2)
    normal = normal / np.linalg.norm(normal)

    d = -np.dot(mean_point, normal)

    return normal, d


def measure_axis(tracker, client, axis_name, num_points=10, step=1.0, start_position=None):
    """
    Measure axis at fixed steps.
    """
    log.info("Measuring {}-axis.".format(axis_name))

    robot = client.robot("Robot1")

    points = []

    result = robot.get_position()
    start_pos = result["joints"][axis_name]

    if start_position is not None:
        robot.move_joint_position({axis_name: start_position})

    for i in range(num_points):
        while True:
            try:
                point = tracker.measure_stationary_xyz()
                break
            except Exception:
                input("Failed to measure point. Press Enter to retry.")

        points.append(point)

        move_joint_relative(robot, axis_name, step)

    log.info("Moving joint to starting position {:.4f}".format(start_pos))
    robot.move_joint_position({axis_name: start_pos})

    log.info("Done.")

    return points


def measure_axis_direction(tracker, client, axis_name, num_points=10, step=1.0, proj_plane_normal=None):
    """
    Measure axis direction by moving the axis in steps and measuring reflector with Leica.
    :param tracker: Tracket object.
    :param client: TnTClient object.
    :param axis_name: Name of axis e.g. "x".
    :param num_points: Number of points to measure and number of axis steps.
    :param step: Step size in units if the axis e.g. mm or deg.
    :param proj_plane_normal: 3D normal vector of a plane (through origin) where to project the points.
    :return: 3D direction vector.
    """
    log.info("Measuring {}-axis direction.".format(axis_name))

    robot = client.robot("Robot1")

    points = np.zeros((num_points, 3))

    result = robot.get_position()
    start_pos = result["joints"][axis_name]

    for i in range(num_points):
        point = np.array(tracker.measure_stationary_xyz())

        if proj_plane_normal is not None:
            # Project point to plane. Note that this plane goes through the origin.
            point = point - np.dot(point, proj_plane_normal) * proj_plane_normal

        points[i, :] = point

        move_joint_relative(robot, axis_name, step)

    log.info("Moving joint to starting position {:.4f}".format(start_pos))
    robot.move_joint_position({axis_name: start_pos})

    z_dir = direction_from_points(points)

    log.info("Done.")

    return z_dir


def move_joint_relative(robot, axis_name: str, step: float):
    """
    Does relative move for a single joint.
    :param robot: Robot client instance.
    :param axis_name: Name of axis.
    :param step: Step size for movement.
    :return:
    """
    current_position = robot.get_position()['joints'][axis_name]
    robot.move_joint_position({axis_name: current_position + step})


def optimize_tool_zero_tilt(tracker, client, point_upper, point_lower, z_dir, tilt_name="tilt_slider", min_tilt=0,
                            max_tilt=45):
    """
    Move robot tilt until it is as parallel to z-axis as possible.
    :param tracker: Tracker object.
    :param client: TnTClient object.
    :param point_upper: 3D position of pen upper reflector.
    :param point_lower: 3D position of pen lower reflector.
    :param z_dir: Direction of the z-axis.
    :param tilt_name: Name of tilt axis e.g. "tilt" or "tilt_slider".
    :param min_tilt: Minimum value for tilt optimization.
    :param max_tilt: Maximum value for tilt optimization.
    :return: Value of tilt axis at optimal position.
    """
    robot = client.robot("Robot1")

    # Get current position to return to.
    result = robot.get_position()
    start_pos = result["effective"]
    start_tilt = (max_tilt - min_tilt) / 2.0

    log.info("Optimizing tool zero tilt.")

    min_interval = 0.25

    result = start_tilt

    # The algorithm measures tilt angle error as a function of tilt joint in an interval that
    # is assumed to contain the zero tilt position. A 2nd degree polynomial is fit to the data and minimum
    # position is calculated analytically. Then the interval is halved around the estimated solution and the
    # process is repeated. Fitting the polynomial makes the algorithm robust against noise in the data when
    # the interval becomes such that inaccuracies in tilt joint start to emerge.
    while max_tilt - min_tilt > min_interval:
        x = []
        y = []

        for tilt in np.linspace(min_tilt, max_tilt, 20):
            # Move tilt joint to target position.
            log.info("Moving tilt joint to position {:.4f}".format(float(tilt)))
            robot.move_joint_position({tilt_name: float(tilt)})

            # Measure tool direction.
            tracker.position_to_xyz(*point_lower)

            log.info("Measuring lower reflector")
            point = tracker.measure_stationary_xyz()

            # Update reflector position.
            point_lower = point

            tracker.position_to_xyz(*point_upper)
            log.info("Measuring upper reflector")
            point = tracker.measure_stationary_xyz()

            # Update reflector position.
            point_upper = point

            tool_dir = np.array(point_upper) - np.array(point_lower)
            tool_dir = tool_dir / np.linalg.norm(tool_dir)

            angle = np.degrees(np.arccos(np.dot(z_dir, tool_dir)))  # both are normalized, so denominator is 1
            log.debug("Angle between Z-axis and stylus: {:.4f}".format(angle))

            x.append(tilt)
            y.append(angle)

        # Fit 2nd degree polynomial to the data.
        coef = np.polyfit(x, y, deg=2)

        # Find minimum of the curve (zero point of derivative).
        c = coef[0]
        b = coef[1]
        x_min = -b / (2 * c)
        result = x_min
        angle = np.polyval(coef, x_min)

        log.debug("Current estimate for zero-tilt value: {:.4f}. Angle: {:.4f}".format(result, angle))

        # Plot the results so that user can estimate if the minimum is within the measurement range.
        plt.plot(x, y)
        plt.plot(x, np.polyval(coef, x))  # Fitted curve
        plt.plot([result, result], [min(y), max(y)])  # Current optimum as vertical line
        plt.show()

        # Decrease the interval to half of current interval around estimated location of the minimum.
        interval = (max_tilt - min_tilt) / 4
        min_tilt = max(result - interval, min_tilt)
        max_tilt = min(result + interval, max_tilt)

    # Return to start position.
    log.info("Moving tilt joint to starting position {:.4f}".format(start_tilt))
    robot.move_joint_position({tilt_name: start_tilt})

    log.info("Moving robot to starting position ({:.4f}, {:.4f}, {:.4f})".format(start_pos["x"], start_pos["y"],
                                                                                 start_pos["z"]))
    robot.move(x=start_pos["x"], y=start_pos["y"], z=start_pos["z"], azimuth=start_pos['azimuth'], tilt=start_pos['tilt'])

    log.info("Done.")

    return result


def measure_tilt_zero(tracker, parameters):
    """
    Measure tilt joint value where pen tool is aligned with the z-axis.
    At the end of the procedure, tilt axis is in position where it is parallel to z-axis.
    Then it should be easy to open Granity and set the homing offset to current setpoint.
    :param parameters: Dict of parameters.
    """
    client = TnTClient(host=parameters["server_host"])

    robot = client.robot("Robot1")

    robot.set_speed(parameters["speed"], parameters["acceleration"])

    input("Move robot to a position where z-axis can move up 10 mm and pen tilt can be changed. Then press Enter.")

    if parameters["show_camera_dialog"]:
        tracker.open_camera_dialog()

    input("Lock Leica to the upper reflector and then press Enter.")
    log.info("Measuring upper reflector")
    point_upper = tracker.measure_stationary_xyz()

    input("Lock Leica to the lower reflector and then press Enter.")
    log.info("Measuring lower reflector")
    point_lower = tracker.measure_stationary_xyz()

    z_dir = measure_axis_direction(tracker, client, "z", num_points=parameters["num_points"], step=parameters["z_step"])

    zero_tilt_value = optimize_tool_zero_tilt(tracker, client, point_upper, point_lower, z_dir,
                                              tilt_name=parameters["tilt_name"], min_tilt=parameters["min_tilt"],
                                              max_tilt=parameters["max_tilt"])

    log.info("Zero-tilt value: {}".format(zero_tilt_value))

    if parameters["show_camera_dialog"]:
        tracker.close_camera_dialog()


def measure_tilt(tracker, parameters):
    """
    Measure current tilt angle of pen with respect to the z axis.
    Pen axis and z axis are projected to plane perpendicular to y axis before
    the angle is measured.
    """
    client = TnTClient(host=parameters["server_host"])

    robot = client.robot("Robot1")

    robot.set_speed(parameters["speed"], parameters["acceleration"])

    input("Move robot to a position where z-axis can move up 10 mm and pen tilt can be changed. Then press Enter.")

    if parameters["show_camera_dialog"]:
        tracker.open_camera_dialog()

    result = robot.get_position()
    pos = result["effective"]
    robot.move(x=pos["x"], y=pos["y"], z=pos["z"], azimuth=0, tilt=0)

    x_dir = measure_axis_direction(tracker, client, "x", num_points=parameters["num_points"], step=1.0)
    y_dir = measure_axis_direction(tracker, client, "y", num_points=parameters["num_points"], step=1.0)

    #z_dir = measure_axis_direction(tracker, client, "z", num_points=parameters["num_points"], step=-1.0)

    input("Lock Leica to the upper reflector and then press Enter.")
    log.info("Measuring upper reflector")
    point_upper = tracker.measure_stationary_xyz()

    input("Lock Leica to the lower reflector and then press Enter.")
    log.info("Measuring lower reflector")
    point_lower = tracker.measure_stationary_xyz()
    tracker.position_to_xyz(*point_upper)

    # Direction from lower point to upper point projected to plane perpendicular to y-axis.
    dir_1 = project_direction_to_plane(np.array(point_upper) - np.array(point_lower), y_dir)

    log.info("Angle between pen and x: {} deg.".format(np.degrees(np.arccos(np.dot(dir_1, x_dir)))))

    # Direction from lower point to upper point projected to plane perpendicular to x-axis.
    dir_1 = project_direction_to_plane(np.array(point_upper) - np.array(point_lower), x_dir)

    log.info("Angle between pen and y: {} deg.".format(np.degrees(np.arccos(np.dot(dir_1, y_dir)))))


def measure_tilt_movement(tracker, parameters, tilt=30):
    """
    Measure how much tilt actually moves when commanded to given angle.
    """

    client = TnTClient(host=parameters["server_host"])

    robot = client.robot("Robot1")

    robot.set_speed(parameters["speed"], parameters["acceleration"])

    input("Move robot to a position where z-axis can move up 10 mm and pen tilt can be changed. Then press Enter.")

    if parameters["show_camera_dialog"]:
        tracker.open_camera_dialog()

    result = robot.get_position()
    pos = result["effective"]
    robot.move(x=pos["x"], y=pos["y"], z=pos["z"], azimuth=0, tilt=0)

    y_dir = measure_axis_direction(tracker, client, "y", num_points=parameters["num_points"], step=1.0)

    input("Lock Leica to the upper reflector and then press Enter.")
    log.info("Measuring upper reflector")
    point_upper = tracker.measure_stationary_xyz()

    input("Lock Leica to the lower reflector and then press Enter.")
    log.info("Measuring lower reflector")
    point_lower = tracker.measure_stationary_xyz()
    tracker.position_to_xyz(*point_upper)

    dir_1 = np.array(point_upper) - np.array(point_lower)
    dir_1 = dir_1 - np.dot(dir_1, y_dir) * y_dir
    dir_1 = dir_1 / np.linalg.norm(dir_1)

    robot.move(x=pos["x"], y=pos["y"], z=pos["z"], azimuth=0, tilt=tilt)

    point_upper = tracker.measure_stationary_xyz()
    tracker.position_to_xyz(*point_lower)
    point_lower = tracker.measure_stationary_xyz()
    tracker.position_to_xyz(*point_upper)

    dir_2 = np.array(point_upper) - np.array(point_lower)
    dir_2 = dir_2 - np.dot(dir_2, y_dir) * y_dir
    dir_2 = dir_2 / np.linalg.norm(dir_2)

    angle = np.arccos(np.dot(dir_1, dir_2))

    log.info("Tilt angle: {} deg.".format(np.degrees(angle)))


def measure_azimuth_movement(tracker, parameters, azimuth=10.0):
    """
    Measure how much azimuth actually changes when commanded to given angle.
    """
    client = TnTClient(host=parameters["server_host"])

    robot = client.robot("Robot1")

    robot.set_speed(parameters["speed"], parameters["acceleration"])

    input("Lock Leica to the reflector and press enter to move azimuth to zero.")

    robot.move_joint_position({"azimuth": 0.0})

    z_dir = measure_axis_direction(tracker, client, "z", num_points=parameters["num_points"], step=parameters["z_step"])

    tool_x_dir_1 = measure_axis_direction(tracker, client, parameters["tool_axis_name"],
                                        num_points=parameters["num_points"], step=parameters["tool_axis_step"],
                                        proj_plane_normal=z_dir)

    robot.move_joint_position({"azimuth": azimuth})

    tool_x_dir_2 = measure_axis_direction(tracker, client, parameters["tool_axis_name"],
                                          num_points=parameters["num_points"], step=parameters["tool_axis_step"],
                                          proj_plane_normal=z_dir)

    angle = np.arccos(np.dot(tool_x_dir_1, tool_x_dir_2))

    log.info("Azimuth angle: {} deg.".format(np.degrees(angle)))


def measure_azimuth_offset(tracker, parameters):
    """
    Measure azimuth axis offset to determine homing offset where the robot tool x-axis is aligned with robot x-axis.
    :param parameters: Dict of parameters.
    """
    client = TnTClient(host=parameters["server_host"])

    robot = client.robot("Robot1")

    robot.set_speed(parameters["speed"], parameters["acceleration"])

    if parameters["show_camera_dialog"]:
        tracker.open_camera_dialog()

    input("Lock Leica to the reflector and press enter to move azimuth to zero.")

    robot.move_joint_position({"azimuth": 0.0})

    input("Move robot to a position where z-axis can move up 10 mm and x-axis can move 10 mm right. Then press Enter.")

    z_dir = measure_axis_direction(tracker, client, "z", num_points=parameters["num_points"], step=parameters["z_step"])

    # Measure x-direction and project on a plane orthogonal to z_dir.
    x_dir = measure_axis_direction(tracker, client, "x", num_points=parameters["num_points"], step=parameters["x_step"],
                                   proj_plane_normal=z_dir)

    # Measure tool x-direction and project on a plane orthogonal to z_dir.
    # For synchro robot this is separation. For stylus robot this is tilt or tilt_slider.
    tool_x_dir = measure_axis_direction(tracker, client, parameters["tool_axis_name"],
                                        num_points=parameters["num_points"], step=parameters["tool_axis_step"],
                                        proj_plane_normal=z_dir)

    angle = np.arccos(np.dot(x_dir, tool_x_dir))

    # Determine sign of angle so that positive angle is a rotation
    # from workspace +x to -y as is the convention in TnT.
    sign = np.sign(np.dot(z_dir, np.cross(x_dir, tool_x_dir)))
    angle = angle * sign

    log.info("Azimuth angle: {} deg. Subtract this from current homing offset.".format(np.degrees(angle)))

    if parameters["show_camera_dialog"]:
        tracker.close_camera_dialog()


def test_direction_from_points():
    """
    Test that direction_from_points() gives sensible direction vector from generated set of points.
    """
    num_points = 100
    points = np.zeros((num_points, 3))

    for i in range(num_points):
        points[i, :] = (random.uniform(-1, 1), i + random.uniform(-1, 1), random.uniform(-1, 1))

    dir = direction_from_points(points)
    print(dir)


def measure_distance(laser_tracker):
    """
    Helper function to measure distance between two points.
    """
    input("Lock Leica to first reflector and press Enter.")
    p1 = np.array(laser_tracker.measure_stationary_xyz())

    input("Lock Leica to second reflector and press Enter.")
    p2 = np.array(laser_tracker.measure_stationary_xyz())

    print(np.linalg.norm(p2-p1))


def measure_axis_accuracy(laser_tracker, parameters, num_points=30):
    """
    Measure how much axis position deviates from commanded position
    when moves back and forth in random steps.
    """
    client = TnTClient(host=parameters["server_host"])

    robot = client.robot("Robot1")

    robot.set_speed(parameters["speed"], parameters["acceleration"])

    deviations = []

    tilt_slider0 = 0.0
    robot.move_joint_position({"tilt_slider": tilt_slider0})
    p0 = np.array(laser_tracker.measure_stationary_xyz())

    for i in range(num_points):
        tilt_slider = random.uniform(0, 50)

        robot.move_joint_position({"tilt_slider": tilt_slider})
        p = np.array(laser_tracker.measure_stationary_xyz())

        deviation = np.linalg.norm(p - p0) - abs(tilt_slider - tilt_slider0)
        print(deviation)
        deviations.append(deviation)
        tilt_slider0 = tilt_slider
        p0 = p

    print("Mean: {}".format(np.mean(np.abs(deviations))))
    print("Max: {}".format(np.max(np.abs(deviations))))
    print("Stdev: {}".format(np.std(deviations)))

    plt.hist(deviations, bins=10)
    plt.show()


def measure_and_save_axes(tracker, parameters, path="axis_data.json"):
    """
    Measure several axis directions by moving them a short distance.
    Results are saved to a file for later analysis.
    """
    client = TnTClient(host=parameters["server_host"])

    robot = client.robot("Robot1")

    robot.set_speed(parameters["speed"], parameters["acceleration"])

    input("Lock Leica to a reflector attached to tilt slider and press Enter.")

    robot.move_joint_position({"azimuth": 0.0})
    robot.move_joint_position({"tilt_slider": 0.0})

    x = measure_axis(tracker, client, "x", num_points=10, step=1.0)
    y = measure_axis(tracker, client, "y", num_points=10, step=1.0)
    z = measure_axis(tracker, client, "z", num_points=10, step=-1.0)
    vc = measure_axis(tracker, client, "voicecoil1", num_points=12, step=-1.0, start_position=6)

    robot.move_joint_position({"tilt_slider": 50.0})
    azimuth = measure_axis(tracker, client, "azimuth", num_points=30, step=1.0, start_position=-20)
    robot.move_joint_position({"tilt_slider": 0.0})

    robot.move_joint_position({"azimuth": 0.0})
    tilt_slider = measure_axis(tracker, client, "tilt_slider", num_points=20, step=2.0)

    data = {
        "x": x,
        "y": y,
        "z": z,
        "azimuth": azimuth,
        "vc": vc,
        "tilt_slider": tilt_slider
    }

    with open(path, "w") as file:
        json.dump(data, file, sort_keys=True, indent=1, separators=(',', ': '))


def vector_angle_deg(a, b):
    return np.degrees(np.arccos(np.dot(a, b)))


def analyze_axes(path="axis_data.json"):
    """
    Analyze axis data in given file. Computes angles between various axes.
    """
    with open(path) as f:
        data = f.read()

    data = json.loads(data)

    x = np.array(data["x"])
    y = np.array(data["y"])
    z = np.array(data["z"])
    azimuth = np.array(data["azimuth"])
    vc = np.array(data["vc"])
    tilt_slider = np.array(data["tilt_slider"])

    x_dir = direction_from_points(x)
    y_dir = direction_from_points(y)
    z_dir = direction_from_points(z)
    vc_dir = direction_from_points(vc)
    tilt_slider_dir = direction_from_points(tilt_slider)

    azimuth_dir, _ = plane_from_points(azimuth)

    xy_normal = np.cross(y_dir, x_dir)
    xy_normal = xy_normal / np.linalg.norm(xy_normal)

    print("Angle between z and xy normal: {} deg.".format(vector_angle_deg(z_dir, xy_normal)))
    print("Angle between z and VC: {} deg.".format(vector_angle_deg(z_dir, vc_dir)))
    print("Angle between z and tilt slider: {} deg.".format(vector_angle_deg(z_dir, tilt_slider_dir)))
    print("Angle between x and azimuth: {} deg.".format(vector_angle_deg(x_dir, azimuth_dir)))
    print("Angle between y and azimuth: {} deg.".format(vector_angle_deg(y_dir, azimuth_dir)))
    print("Angle between z and azimuth: {} deg.".format(vector_angle_deg(z_dir, azimuth_dir)))
    print("Angle between azimuth and tilt slider: {} deg.".format(vector_angle_deg(tilt_slider_dir, azimuth_dir)))
    print("Angle between azimuth and VC: {} deg.".format(vector_angle_deg(vc_dir, azimuth_dir)))


def measure_xyz_persistently(tracker):
    while True:
        try:
            return tracker.measure_stationary_xyz()
        except Exception:
            input("Failed to measure point. Press Enter to retry.")


def position_to_xyz_persistently(tracker, pos):
    while True:
        try:
            tracker.position_to_xyz(*pos)
            return
        except Exception:
            input("Failed to position to point. Press Enter to retry.")


def measure_tilt_function(tracker, parameters, min_tilt_slider=-1.0, max_tilt_slider=40, num_points=30, path="tilt_function.json"):
    """
    Measures two reflectors of a pen as a function of tilt slider joint.
    This can be used to construct a black-box model of the Scott-Russell tilt kinematics.
    """
    log.info("Measuring stylus tilt function.")

    client = TnTClient(host=parameters["server_host"])

    robot = client.robot("Robot1")

    robot.set_speed(parameters["speed"], parameters["acceleration"])

    robot.move_joint_position({"azimuth": 0})
    robot.move_joint_position({"tilt_slider": 0})

    input("Lock Leica to the upper reflector and then press Enter.")
    log.info("Measuring upper reflector")
    point_upper_start = tracker.measure_stationary_xyz()

    input("Lock Leica to the lower reflector and then press Enter.")
    log.info("Measuring lower reflector")
    point_lower_start = tracker.measure_stationary_xyz()

    point_upper = point_upper_start
    point_lower = point_lower_start

    x = measure_axis(tracker, client, "x", num_points=10, step=1.0)
    y = measure_axis(tracker, client, "y", num_points=10, step=1.0)
    z = measure_axis(tracker, client, "z", num_points=10, step=-1.0)

    tilt_data = []

    tilt_zero_data = []

    log.info("Measuring upper reflector")
    position_to_xyz_persistently(tracker, point_upper)
    point_upper = measure_xyz_persistently(tracker)

    log.info("Measuring lower reflector")
    position_to_xyz_persistently(tracker, point_lower)
    point_lower = measure_xyz_persistently(tracker)

    tilt_zero_data.append({"tilt_slider": 0.0, "upper": point_upper, "lower": point_lower})

    for tilt_slider in np.linspace(min_tilt_slider, max_tilt_slider, num_points):
        robot.move_joint_position({"tilt_slider": tilt_slider})

        log.info("Measuring upper reflector")
        position_to_xyz_persistently(tracker, point_upper)
        point_upper = measure_xyz_persistently(tracker)

        log.info("Measuring lower reflector")
        position_to_xyz_persistently(tracker, point_lower)
        point_lower = measure_xyz_persistently(tracker)

        tilt_data.append({"tilt_slider": tilt_slider, "upper": point_upper, "lower": point_lower})

    data = {
        "x": x,
        "y": y,
        "z": z,
        "tilt_slider": tilt_data,
        "tilt_zero_data": tilt_zero_data
    }

    with open(path, "w") as file:
        json.dump(data, file, sort_keys=True, indent=1, separators=(',', ': '))


def plot_tilt_function(path="tilt_function.json"):
    """
    Plot data obtained with measure_tilt_function().
    """
    with open(path) as f:
        data = f.read()

    data = json.loads(data)

    reflector_radius = 0.5 * 25.4 / 2

    x = np.array(data["x"])
    y = np.array(data["y"])
    z = np.array(data["z"])
    tilt_slider_data = np.array(data["tilt_slider"])

    x_dir = direction_from_points(x)
    y_dir = direction_from_points(y)
    z_dir = direction_from_points(z)

    z_dir_proj = z_dir - np.dot(z_dir, y_dir) * y_dir
    z_dir_proj = z_dir_proj / np.linalg.norm(z_dir_proj)

    tilt_angles = []
    x = []
    y = []
    z = []

    tilt_zero_data = data["tilt_zero_data"][0]

    upper = np.array(tilt_zero_data["upper"])
    lower = np.array(tilt_zero_data["lower"])

    dir = lower - upper

    dir = dir / np.linalg.norm(dir)

    ref_point = lower + dir * reflector_radius

    for entry in tilt_slider_data:
        upper = np.array(entry["upper"])
        lower = np.array(entry["lower"])

        dir = lower - upper

        dir = dir / np.linalg.norm(dir)

        point = lower + dir * reflector_radius

        dir = dir - np.dot(dir, y_dir) * y_dir
        dir = dir / np.linalg.norm(dir)

        tilt_angle = np.degrees(np.arccos(np.dot(-dir, z_dir_proj)))
        tilt_angles.append(tilt_angle)

        x.append(np.dot(x_dir, point - ref_point))
        y.append(np.dot(y_dir, point - ref_point))
        z.append(np.dot(z_dir, point - ref_point))

    tilt_slider = [entry["tilt_slider"] for entry in tilt_slider_data]

    #plt.plot(tilt_slider, z)

    plt.plot(tilt_slider, tilt_angles)
    plt.show()


if __name__ == "__main__":
    # Configure logging.
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('pylmf').setLevel(logging.WARNING)

    fmt = '%(asctime)s %(levelname)7s: %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=fmt)

    # Initialize laser tracker.
    tracker_ip = "192.168.127.253"  # Use 'AT930Simulator' for simulator Leica
    laser_tracker = LaserTracker(ip_address=tracker_ip)
    laser_tracker.select_rrr05_target()
    laser_tracker.set_accuracy_standard()

    # Parameters for tilt zero position calibration.
    tilt_zero_parameters = {
        "server_host": "127.0.0.1",
        "show_camera_dialog": False,
        "speed": 50,
        "acceleration": 10,
        "num_points": 10,
        "z_step": -1.0,
        "y_step": 1.0,
        "min_tilt": -1.0,
        "max_tilt": 1.0,
        "tilt_name": "tilt_slider"  # Can be "tilt" or "tilt_slider"
    }

    # Measure tilt zero offset.
    # measure_tilt_zero(laser_tracker, tilt_zero_parameters)

    # With stylus robot the reflector needs to be in the upper part of the stylus
    # so that it moves along +x when tilt increases.
    # With synchro robot the reflector should be on the right finger (looking from the front).
    azimuth_offset_parameters = {
        "server_host": "127.0.0.1",
        "show_camera_dialog": False,
        "speed": 50,
        "acceleration": 10,
        "num_points": 10,
        "z_step": -2.0,
        "x_step": 2.0,
        "tool_axis_step": 2.0,
        "tool_axis_name": "separation"  # Can be "separation", "tilt" or "tilt_slider"
    }

    # measure_azimuth_offset(laser_tracker, azimuth_offset_parameters)