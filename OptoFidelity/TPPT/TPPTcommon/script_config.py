import json
from scriptpath import join_script_root_directory


def get_config_value(key, default_value=None):
    try:
        f = open(join_script_root_directory('config.json'), 'r')
        conf = json.loads(f.read())
        f.close()
        return conf[key]
    except:
        return default_value


def get_spacing_and_offset(controls):
    """
    Get grid spacing and edge offset settings based on config.json
    """
    if get_config_value("grid_offsets") and get_config_value("separate_xy_parameters"):
        edge_offset_x = controls.edge_offset_x
        edge_offset_y = controls.edge_offset_y
    elif get_config_value("grid_offsets"):
        edge_offset_x = edge_offset_y = controls.edge_offset
    else:
        edge_offset_x = edge_offset_y = 0.0

    if get_config_value("separate_xy_parameters"):
        try:
            grid_spacing_x = controls.grid_spacing_x
            grid_spacing_y = controls.grid_spacing_y
        except:
            # Swipe test has only one parameter
            grid_spacing_x = grid_spacing_y = controls.grid_spacing
    else:
        grid_spacing_x = grid_spacing_y = controls.grid_spacing

    return grid_spacing_x, grid_spacing_y, edge_offset_x, edge_offset_y


def get_min_swipe_radius():
    return float(get_config_value("min_swipe_radius", 4.0))


def get_max_swipe_radius():
    return float(get_config_value("max_swipe_radius", 20.0))


def get_min_swipe_clearance():
    return float(get_config_value("min_swipe_clearance", -1.0))


def get_max_swipe_clearance():
    return float(get_config_value("max_swipe_clearance", 1.0))


def check_swipe_parameters(clearance, swipe_radius):
    min_swipe_clearance = get_min_swipe_clearance()
    max_swipe_clearance = get_max_swipe_clearance()

    min_swipe_radius = get_min_swipe_radius()
    max_swipe_radius = get_max_swipe_radius()

    if clearance < min_swipe_clearance or clearance > max_swipe_clearance:
        raise Exception(
            "Clearance must be within range {} mm to {} mm.".format(min_swipe_clearance, max_swipe_clearance))

    if swipe_radius < min_swipe_radius or swipe_radius > max_swipe_radius:
        raise Exception("Swipe radius must be within range {} mm to {} mm.".format(min_swipe_radius, max_swipe_radius))


def get_tap_measurement_timeout():
    """
    Tap measurement timeout is calculated after tap motion has completed.
    Some devices require rather long timeout to get the first event.
    This value has only effect to test duration in case the first touch event takes exceptionally long to arrive or
    touch is not detected at all. Test continues immediately after first event is obtained.
    :return: Timeout in seconds.
    """

    return float(get_config_value("tap_measurement_timeout", 6.0))

def get_continuous_measurement_timeout():
    """
    Continuous measurement timeout is calculated after test motion (e.g. swipe) has completed.
    Usually short timeout is sufficient.
    Test waits for this timeout each time to make sure all touch events have been obtained in case there is latency.
    Hence this timeout increases total test duration even if touch events arrive quickly.
    :return: Timeout in seconds.
    """
    return float(get_config_value("continuous_measurement_timeout", 0.5))
