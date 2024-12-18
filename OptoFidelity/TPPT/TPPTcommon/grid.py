import copy
import numpy
import random
import math
import csv

import logging
import os

log = logging.getLogger(__name__)
import TPPTcommon.containers as Containers
from scriptpath import get_script_root_directory


GRID_FILE_DIR = os.path.join(get_script_root_directory() , "TPPTcommon", "GridFiles")


def parse_numbers(numbers_str: str):
    if "," in numbers_str:
        tokens = numbers_str.split(",")

        return [float(token) for token in tokens]
    elif ":" in numbers_str:
        tokens = numbers_str.split(":")

        if len(tokens) != 3:
            raise ValueError("Number range must have the form 'start:end:step'.")

        start, stop, step = float(tokens[0]), float(tokens[1]), float(tokens[2])
        return numpy.arange(start, stop + step / 2, step).tolist()
    else:
        # In this case numbers_str must be just one number.
        # Return it in a list to allow iterating.
        return [float(numbers_str)]


def add_grid_file_controls(test):
    test.controls.usegridfile = False
    test.controls.info['usegridfile'] = {'label': 'Use grid file',
                                         'tooltip': test.context.tooltips['Use grid file']}

    try:
        gridfiles = os.listdir(GRID_FILE_DIR)
        test.controls.gridfile = gridfiles[0]
    except FileNotFoundError:
        gridfiles = []
        test.controls.gridfile = ""

    test.controls.info['gridfile'] = {'label': 'Grid file', 'items': gridfiles,
                                      'visibility_control': 'usegridfile',
                                      'visibility_value': True,
                                  'tooltip': test.context.tooltips['Grid file']}

    test.controls.gridunit = "mm"
    test.controls.info['gridunit'] = {'label': 'Grid unit', 'items': {'mm', '%'},
                                      'visibility_control': 'usegridfile',
                                      'visibility_value': True,
                                      'tooltip': test.context.tooltips['Grid unit']}


def parse_angles(angles_str, dut):
    """
    Parse angle values from string of comma separated values.
    The angles in string can be numeric or contain special value 'diagonal' which is converted to
    diagonal angle within the given DUT.
    :param angles_str: String containing list of angles.
    :param dut: DUT where angles are interpreted.
    :return: List of numeric angles.
    """
    tokens = angles_str.split(",")

    angles = []

    for token in tokens:
        token = token.strip()

        if token.lower() == "diagonal":
            d_angle = -numpy.degrees(numpy.arctan2(dut.height, dut.width))

            angles.append(d_angle)
        else:
            try:
                angle = float(token)
            except ValueError:
                raise Exception("Could not interpret '{}' as angle.".format(token))

            angles.append(angle)

    return angles


def line_coord_of_closest_rectangle_intersection(min_x, max_x, start_x, dir_x):
    """
    Get closest parametric line coordinate of intersection point of the line and
    rectangle along one dimension.
    :param min_x: Rectangle minimum along selected dimension.
    :param max_x: Rectangle maximum along selected dimension.
    :param start_x: Line start point coordinate in selected dimension.
    :param dir_x: Line direction vector coordinate in selected dimension.
    :return: Line parameter at closest intersection.
    """

    # Direction vector determines which of the two possible rectangle edges is hit first.
    if dir_x > 0:
        return (min_x - start_x) / dir_x
    elif dir_x < 0:
        return (max_x - start_x) / dir_x

    # Direction is perpendicular to selected dimension. Return -1 so these planes are not hit.
    return -1


def clip_line_start_to_rectangle(line, width, height, border_width_x, border_width_y):
    """
    Clip line start to axis aligned rectangle center area (determined by border_width).
    If line is completely outside of the rectangle, the line is collapsed into a point.
    :param line: A line with start and end points.
    :param width: Width of the rectangle.
    :param height: Height of the rectangle.
    :param border_width_x: Border width of the rectangle in x-direction.
    :param border_width_y: Border width of the rectangle in y-direction.
    """

    # Line direction vector components.
    dx = line.end_x - line.start_x
    dy = line.end_y - line.start_y

    # Clip region min and max coordinates.
    min_x = border_width_x
    max_x = width - border_width_x
    min_y = border_width_y
    max_y = height - border_width_y

    # Determine line parameters for two potential closest hit points.
    tx = line_coord_of_closest_rectangle_intersection(min_x, max_x, line.start_x, dx)
    ty = line_coord_of_closest_rectangle_intersection(min_y, max_y, line.start_y, dy)

    # Line start is inside the rectangle
    if tx < 0 and ty < 0:
        return

    # Determine which of the two coordinates corresponds to closest hit point.
    if tx > ty:
        t = tx
        px = line.start_x + dx * t
        py = line.start_y + dy * t

        # Check if the hit point is within the region boundary.
        if min_y <= py <= max_y:
            line.start_x = px
            line.start_y = py
        else:
            line.start_x = line.end_x
            line.start_y = line.end_y
    else:
        t = ty
        px = line.start_x + dx * t
        py = line.start_y + dy * t

        # Check if the hit point is within the region boundary.
        if min_x <= px <= max_x:
            line.start_x = px
            line.start_y = py
        else:
            line.start_x = line.end_x
            line.start_y = line.end_y


def clip_line_to_rectangle(line, width, height, border_width_x, border_width_y):
    """
    Clip line to axis aligned rectangle center area (determined by border_width).
    :param line: A line with start and end points.
    :param width: Width of the rectangle.
    :param height: Height of the rectangle.
    :param border_width_x: Border width of the rectangle in x-direction.
    :param border_width_y: Border width of the rectangle in y-direction.
    :return:
    """

    # Clip line start point to region.
    clip_line_start_to_rectangle(line, width, height, border_width_x, border_width_y)

    # Swap line start and end points and again clip line start point to region. Then swap start and end points back.
    line.start_x, line.start_y, line.end_x, line.end_y = line.end_x, line.end_y, line.start_x, line.start_y
    clip_line_start_to_rectangle(line, width, height, border_width_x, border_width_y)
    line.start_x, line.start_y, line.end_x, line.end_y = line.end_x, line.end_y, line.start_x, line.start_y

def clip_lines_svg(dut, lines_all, border_width):
    """
    Clip lines to be inside the defined dut. If filtering the lines breaks them in
    multiple parts, all parts are saved as individual lines.
    :param dut: tnt_dut object.
    :param lines_all: containers.lines drawn assuming dut is rectangle and with border width 0.
    :param border_width: Width of the border area.
    :return: Clipped containers.lines.
    """
    lines_filtered = []
    line_end_points = []
    # The filtering function needs the endpoints of the lines.
    for line in lines_all:
        line_end_points.append((line.start_x, line.start_y, line.end_x, line.end_y))
    line_end_points_filt = dut.filter_lines(line_end_points, "analysis_region", border_width)
    for i, end_points in enumerate(line_end_points_filt):
        # If the line is discarded due to clipping, it is an empty group.
        if len(end_points) > 0:
            # The line might be clipped in multiple parts (because of notch).
            for points in end_points:
                # Copy the line from which the endpoints are and modify the copy with new endpoints and save.
                filt_line = copy.copy(lines_all[i])
                filt_line.start_x, filt_line.start_y = points[0], points[1]
                filt_line.end_x, filt_line.end_y = points[2], points[3]
                lines_filtered.append(filt_line)
    return lines_filtered

def filter_points(dut, points_all, border_width):
    """
    Filter out points that are outside given area defined by dut's SVG shape and border width.
    :param dut: tnt_dut object.
    :param points_all: containers.points drawn assuming that dut is rectangle and border width=0.
    :param border_width: Border width.
    :return: List of containers.points objects that are inside given area.
    """
    all_coordinates = []
    points_filtered = []
    for point in points_all:
        all_coordinates.append((point.x, point.y))
    filtered_coordinates = dut.filter_points(all_coordinates, 'analysis_region', margin=border_width)
    # We use the first point as reference to get metadata from point objects.
    point_zero = points_all[0]
    for coordinates in filtered_coordinates:
        point_mod = copy.copy(point_zero)
        point_mod.x, point_mod.y = coordinates[0], coordinates[1]
        points_filtered.append(point_mod)

    return points_filtered

def dut_has_svg(dut):
    """
    Check if DUT has an SVG shape defined.
    :param dut: tnt_dut object.
    :return: True if there is SVG False if not.
    """
    if len(dut.svg_data()) > 0:
        return True
    else:
        return False


def azimuth_direction(azimuth_angle):
    '''
    Calculates unit vector for given azimuth angle.
    ----------------------------------------
    Why is this needed:

    In our robots, we use left hand convention for x-y-z-axis and right hand convention for azimuth angles.
    With other words, the z-axis points up from DUT, x-axis from top left corner to top right corner, and
    y-axis from top left corner to bottom left corner. However, the angle grows anti-clockwise.
    ----------------------------------------
    :param azimuth_angle: the angle for which we want the unit vector (radians)
    :return: unit vector as a list [x,y] for given azimuth angle
    '''

    x_comp = numpy.cos(-azimuth_angle)
    y_comp = numpy.sin(-azimuth_angle)

    return [x_comp, y_comp]


def create_random_points(dut, num_points, edge_offset=0):
    """
    Create random measurement points inside DUT area.
    :param dut: The DUT to be measured.
    :param num_points: Number of required random points.
    :param edge_offset: Edge offset.
    :return: List of points.
    """

    if edge_offset < 0:
        log.warning("Edge offset should have a positive value")
        return []

    if dut_has_svg(dut):
        return create_random_points_svg(dut, num_points, edge_offset)
    else:
        return create_random_points_rectangular(dut, num_points, edge_offset)


def create_random_points_svg(dut, num_points, edge_offset=0):
    """
   Create random measurement points inside DUT area.
   This is for DUT that has SVG shape defined.
   :param dut: The DUT to be measured.
   :param num_points: Number of required random points.
   :param edge_offset: Edge offset.
   :return: List of points.
   """
    accepted_points = []
    while len(accepted_points) < num_points:
        # We create one point at a time and filter it. If it goes through
        # filtering we add to points list.
        point_list = create_random_points_rectangular(dut, 1, 0)
        if len(filter_points(dut, point_list, edge_offset)) > 0:
            accepted_points.append(point_list[0])
    return accepted_points


def create_random_points_rectangular(dut, num_points, edge_offset=0):
    """
   Create random measurement points inside DUT area.
   This is for rectangular DUT.
   :param dut: The DUT to be measured.
   :param num_points: Number of required random points.
   :param edge_offset: Edge offset.
   :return: List of points.
   """
    retval = []

    w_ = dut.width
    h_ = dut.height

    for point in range(num_points):
        retval.append(Containers.Point(random.uniform(edge_offset, w_-edge_offset),
                                       random.uniform(edge_offset, h_-edge_offset), 0))

    return retval

def create_non_stationary_reporting_rate_lines(dut, edge_offset):
    """
    Create measurement lines for non stationary reporting rate test.
    :param dut: The DUT to be measured.
    :param edge_offset: Edge offset.
    :return: List of measurement lines.
    """
    if dut_has_svg(dut):
        return create_non_stationary_reporting_rate_lines_svg(dut, edge_offset)
    else:
        return create_non_stationary_reporting_rate_lines_rectangular(dut, edge_offset)


def create_non_stationary_reporting_rate_lines_svg(dut, edge_offset):
    """
    Create measurement lines for non stationary reporting rate test for a dut that has svg shape defined.
    :param dut: The DUT to be measured.
    :param edge_offset: Edge offset.
    :return: List of measurement lines.
    """
    lines_all = create_non_stationary_reporting_rate_lines_rectangular(dut, 0)
    return clip_lines_svg(dut, lines_all, edge_offset)


def create_non_stationary_reporting_rate_lines_rectangular(dut, edge_offset):
    """
    Create measurement lines for non stationary reporting rate test for a rectangular dut.
    :param dut: The DUT to be measured.
    :param edge_offset: Edge offset.
    :return: List of measurement lines.
    """
    retval = []
    w_ = dut.width
    h_ = dut.height

    retval.append(Containers.Line(edge_offset, edge_offset, 0.0, w_-edge_offset, h_-edge_offset, 0.0))
    retval.append(Containers.Line(w_ / 2.0, edge_offset, 0.0, w_ / 2, h_-edge_offset, 0.0))
    retval.append(Containers.Line(edge_offset, h_ / 2.0, 0, w_-edge_offset, h_ / 2.0, 0.0))

    return retval

def create_vertical_horizontal_line_grid(dut, grid_spacing, edge_offset_x=0.0, edge_offset_y=0.0):
    """
    Create measurement lines for vertical/horizontal swipe test.
    :param dut: The DUT to be measured.
    :param grid_spacing: The distance between parallel lines.
    :param edge_offset_x: Edge offset in x-direction.
    (Different values for Edge offsets only supported for rectangular DUTs.)
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement lines.
    """
    if dut_has_svg(dut):
        return create_vertical_horizontal_line_grid_svg(dut, grid_spacing, edge_offset_x, edge_offset_y)
    else:
        return create_vertical_horizontal_line_grid_rectangular(dut, grid_spacing, edge_offset_x, edge_offset_y)

def create_vertical_horizontal_line_grid_svg(dut, grid_spacing, edge_offset_x, edge_offset_y):
    """
    Create measurement lines for vertical/horizontal swipe test for a dut that has svg shape defined.
    :param dut: The DUT to be measured.
    :param grid_spacing: The distance between parallel lines.
    :param edge_offset_x: Edge offset in x-direction.
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement lines.
    """
    if edge_offset_x != edge_offset_y:
        log.warning("DUTs with SVG shapes can only have uniform edge offsets, using edge offset x")
    border_width = edge_offset_x
    lines_all = create_vertical_horizontal_line_grid_rectangular(dut, grid_spacing, edge_offset_x=0, edge_offset_y=0)
    return clip_lines_svg(dut, lines_all, border_width)

def create_vertical_horizontal_line_grid_rectangular(dut, grid_spacing, edge_offset_x=0.0, edge_offset_y=0.0):
    """
    Create measurement lines for vertical/horizontal swipe test for a rectangular dut.
    :param dut: The DUT to be measured.
    :param grid_spacing: The distance between parallel lines.
    :param edge_offset_x: Edge offset in x-direction.
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement lines.
    """
    retval = []
    z = 0.0

    w_ = dut.width - 2 * edge_offset_x
    h_ = dut.height - 2 * edge_offset_y

    # Sanity checking the offset value.
    if edge_offset_x > w_ / 2 or edge_offset_y > h_ / 2:
        log.warning("Edge offset value is too large, not able to create line grid")
        return retval

    w_points = int(numpy.round(w_ / grid_spacing))
    if w_points == 0: w_points = 1

    h_points = int(numpy.round(h_ / grid_spacing))
    if h_points == 0: h_points = 1

    w_real_step = (w_) / w_points
    h_real_step = (h_) / h_points

    # Horizontal lines.
    for y_ in range(h_points + 1):
        start_y = y_ * h_real_step + edge_offset_y
        end_y = start_y
        # If the line is in the offset region, it needs to be discarded.
        if start_y < edge_offset_y or start_y > h_ + edge_offset_y:
            continue
        # The start and end x-values are limited by the offset.
        start_x = edge_offset_x
        end_x = w_ + edge_offset_x

        retval.append(Containers.Line(start_x, start_y, z, end_x, end_y, z))

    # Vertical lines.
    for x_ in range(w_points + 1):
        start_x = x_ * w_real_step + edge_offset_x
        end_x = start_x
        # If the line is in the offset region, it needs to be discarded.
        if start_x < edge_offset_x or start_x > w_ + edge_offset_x:
            continue
        # The start and end x-values are limited by the offset.
        start_y = edge_offset_y
        end_y = h_ + edge_offset_y

        retval.append(Containers.Line(start_x, start_y, z, end_x, end_y, z))

    return retval

def create_diagonal_line_grid(dut, grid_spacing, edge_offset_x=0.0, edge_offset_y=0.0):
    """
    Create measurement lines for diagonal swipe test.
    :param dut: The DUT to be measured.
    :param grid_spacing: The distance between parallel lines.
    :param edge_offset_x: Edge offset in x-direction.
    (different values for Edge offsets only supported for rectangular DUTs).
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement lines.
    """
    if dut_has_svg(dut):
        return create_diagonal_line_grid_svg(dut, grid_spacing, edge_offset_x, edge_offset_y)
    else:
        return create_diagonal_line_grid_rectangular(dut, grid_spacing, edge_offset_x, edge_offset_y)

def create_diagonal_line_grid_svg(dut, grid_spacing, edge_offset_x=0.0, edge_offset_y=0.0):
    """
    Create measurement lines for diagonal swipe test for a dut that has svg shape defined.
    :param dut: The DUT to be measured.
    :param grid_spacing: The distance between parallel lines.
    :param edge_offset_x: Edge offset in x-direction.
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement lines.
    """
    if edge_offset_x != edge_offset_y:
        log.warning("DUTs with SVG shapes can only have uniform edge offsets, using edge offset x")
    border_width = edge_offset_x
    lines_all = create_diagonal_line_grid_rectangular(dut, grid_spacing, edge_offset_x=0, edge_offset_y=0)
    return clip_lines_svg(dut, lines_all, border_width)

def create_diagonal_line_grid_rectangular(dut, dist, edge_offset_x=0.0, edge_offset_y=0.0):
    """
   Create measurement lines for diagonal swipe test for a rectangular dut.
   :param dut: The DUT to be measured.
   :param grid_spacing: The distance between parallel lines.
   :param edge_offset_x: Edge offset in x-direction.
   :param edge_offset_y: Edge offset in y-direction.
   :return: List of measurement lines.
   """
    retval = []

    w_ = dut.width
    h_ = dut.height

    # Sanity checking the offset value.
    if edge_offset_x > w_ / 2 or edge_offset_y > h_ / 2:
        log.warning("Edge offset value is too large, not able to create line grid")
        return retval

    delta_x = dist / (math.sin(math.atan(h_ / w_)))
    delta_y = delta_x * (h_ / w_)

    # Horizontal lines.
    start_point = [0.0, 0.0]
    end_point = [w_, h_]
    i = 1
    while True:
        if start_point[0] + delta_x * i > w_ or start_point[0] + delta_x * i < 0.0 or \
                end_point[1] - delta_y * i < 0.0:
            break

        line = Containers.Line(delta_x * i, 0.0, 0.0, end_point[0], end_point[1] - delta_y * i, 0.0)
        clip_line_to_rectangle(line, w_, h_, edge_offset_x, edge_offset_y)

        if line.length() > 0:
            retval.append(line)
        i += 1
    i = 0
    while True:
        if start_point[0] + delta_x * i > w_ or start_point[0] + delta_x * i < 0.0 or \
                end_point[1] - delta_y * i < 0.0:
            break
        line = Containers.Line(0.0, delta_y * i, 0.0, end_point[0] - delta_x * i, end_point[1], 0.0)

        clip_line_to_rectangle(line, w_, h_, edge_offset_x, edge_offset_y)

        if line.length() > 0:
            retval.append(line)
        i += 1
    i = 1
    while True:
        if start_point[0] + delta_x * i > w_ or start_point[0] + delta_x * i < 0.0 or \
                end_point[1] - delta_y * i < 0.0:
            break

        line = Containers.Line(w_ - delta_x * i, 0.0, 0.0, 0.0, h_ - delta_y * i, 0.0)

        clip_line_to_rectangle(line, w_, h_, edge_offset_x, edge_offset_y)

        if line.length() > 0:
            retval.append(line)
        i += 1
    i = 0
    while True:
        if start_point[0] + delta_x * i > w_ or start_point[0] + delta_x * i < 0.0 or \
                end_point[1] - delta_y * i < 0.0:
            break

        line = Containers.Line(w_, delta_y * i, 0.0, delta_x * i, h_, 0.0)

        clip_line_to_rectangle(line, w_, h_, edge_offset_x, edge_offset_y)

        if line.length() > 0:
            retval.append(line)
        i += 1
    return retval

def create_worst_case_lines(dut, edge_offset_x=0.0, edge_offset_y=0.0):
    """
    Create measurement lines for worst case swipe test.
    :param dut: The DUT to be measured.
    :param edge_offset_x: Edge offset in x-direction.
    (Different values for edge offsets only supported for rectangular DUTs.)
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement lines.
    """
    if dut_has_svg(dut):
        return create_worst_case_lines_svg(dut, edge_offset_x, edge_offset_y)
    else:
        return create_worst_case_lines_rectangular(dut, edge_offset_x, edge_offset_y)

def create_worst_case_lines_svg(dut, edge_offset_x=0.0, edge_offset_y=0.0):
    """
    Create measurement lines for worst case swipe test for a dut that has svg shape defined.
    :param dut: The DUT to be measured.
    :param edge_offset_x: Edge offset in x-direction.
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement lines.
    """
    if edge_offset_x != edge_offset_y:
        log.warning("DUTs with SVG shapes can only have uniform edge offsets, using edge offset x")
    border_width = edge_offset_x
    lines_all = create_worst_case_lines_rectangular(dut, edge_offset_x=0, edge_offset_y=0)
    return clip_lines_svg(dut, lines_all, border_width)

def create_worst_case_lines_rectangular(dut, edge_offset_x=0.0, edge_offset_y=0.0):
    """
    Create measurement lines for worst case swipe test for rectangular dut.
    :param dut: The DUT to be measured.
    :param edge_offset_x: Edge offset in x-direction.
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement lines.
    """
    retval = []

    z = 0.0
    w_ = dut.width
    h_ = dut.height

    # Sanity checking the offset value.
    if edge_offset_x > w_ / 2 or edge_offset_y > h_ / 2:
        log.warning("Edge offset value is too large, not able to create line grid")
        return retval

    retval.append(Containers.Line(edge_offset_x, edge_offset_y, z, w_ - edge_offset_x, h_ - edge_offset_y, z))
    retval.append(Containers.Line(edge_offset_x, h_ - edge_offset_y, z, w_ - edge_offset_x, edge_offset_y, z))
    retval.append(Containers.Line(w_ / 2.0, edge_offset_y, z, w_ / 2.0, h_ - edge_offset_y, z))
    retval.append(Containers.Line(edge_offset_x, h_ / 2.0, z, w_ - edge_offset_x, h_ / 2.0, z))
    retval.append(Containers.Line(edge_offset_x, edge_offset_y, z, edge_offset_x, h_ - edge_offset_y, z))
    retval.append(Containers.Line(edge_offset_x, h_ - edge_offset_y, z, w_ - edge_offset_x, h_ - edge_offset_y, z))
    retval.append(Containers.Line(w_ - edge_offset_x, h_ - edge_offset_y, z, w_ - edge_offset_x, edge_offset_y, z))
    retval.append(Containers.Line(w_ - edge_offset_x, edge_offset_y, z, edge_offset_x, edge_offset_y, z))

    return retval


def create_point_grid(dut, grid_spacing_x, grid_spacing_y, edge_offset_x=0.0, edge_offset_y=0.0):
    """
    Create grid of measurement points for tap test.
    :param dut: The DUT to be measured.
    :param grid_spacing_x: The distance between grid points in x-direction.
    :param grid_spacing_y: The distance between grid points in y-direction.
    :param edge_offset_x: Edge offset in x-direction.
    (Different values for edge offsets only supported for rectangular DUTs.)
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement points.
    """
    if dut_has_svg(dut):
        return create_point_grid_svg(dut, grid_spacing_x, grid_spacing_y, edge_offset_x, edge_offset_y)
    else:
        return create_point_grid_rectangular(dut, grid_spacing_x, grid_spacing_y, edge_offset_x, edge_offset_y)


def create_point_grid_svg(dut, grid_spacing_x, grid_spacing_y, edge_offset_x, edge_offset_y):
    """
    Create grid of measurement points for tap test for a dut that has SVG shape defined.
    :param dut: The DUT to be measured.
    :param grid_spacing_x: The distance between grid points in x-direction.
    :param grid_spacing_y: The distance between grid points in y-direction.
    :param edge_offset_x: Edge offset in x-direction.
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement points.
    """
    if edge_offset_x != edge_offset_y:
        log.warning("DUTs with SVG shapes can only have uniform edge offsets, using edge offset x")
    border_width = edge_offset_x
    points_all = create_point_grid_rectangular(dut, grid_spacing_x, grid_spacing_y, edge_offset_x, edge_offset_y)
    return filter_points(dut, points_all, border_width)


def create_point_grid_rectangular(dut, grid_spacing_x, grid_spacing_y, edge_offset_x, edge_offset_y):
    """
    Create grid of measurement points for tap test for a rectangular DUT.
    :param dut: The DUT to be measured.
    :param grid_spacing_x: The distance between grid points in x-direction.
    :param grid_spacing_y: The distance between grid points in y-direction.
    :param edge_offset_x: Edge offset in x-direction.
    :param edge_offset_y: Edge offset in y-direction.
    :return: List of measurement points.
    """
    retval = []

    w_ = dut.width - 2 * edge_offset_x
    h_ = dut.height - 2 * edge_offset_y

    w_points = int(numpy.round(w_ / grid_spacing_x))
    if w_points == 0:
        w_points = 1

    h_points = int(numpy.round(h_ / grid_spacing_y))
    if h_points == 0:
        h_points = 1

    w_real_step = w_ / w_points
    h_real_step = h_ / h_points

    for x_ in range(w_points + 1):
        for y_ in range(h_points + 1):
            retval.append(Containers.Point(edge_offset_x + x_ * w_real_step, edge_offset_y + y_ * h_real_step, 0.0))

    return retval


def augment_grid_orientation(points, azimuth_angles, tilt_angles):
    """
    From given list of points, create a new list where given orientations are used for each xyz location.
    """
    result = []

    for point in points:
        for azimuth in azimuth_angles:
            for tilt in tilt_angles:
                new_point = copy.copy(point)

                new_point.tilt = tilt
                new_point.azimuth = azimuth

                result.append(new_point)

    return result


def create_grid_from_file(dut, grid_file_path, grid_unit):
    retval = []

    w_ = dut.width
    h_ = dut.height

    with open(grid_file_path, 'r') as csvfile:
        gridreader = csv.reader(csvfile, delimiter=';', quotechar='|')

        for coord in gridreader:
            if grid_unit == "%":
                point_x = float(coord[0]) / 100 * w_
                point_y = float(coord[1]) / 100 * h_
            else:
                point_x = float(coord[0])
                point_y = float(coord[1])

            if point_x <= w_ and point_y <= h_:
                retval.append(Containers.Point(point_x, point_y, 0.0))

    return retval


def create_multifinger_tap(dut, nf, distance):
    retval = []

    w = dut.width
    h = dut.height
    d = (w ** 2 + h ** 2) ** 0.5

    # Azimuth angle to place first finger near top left corner of DUT.
    d_angle = -numpy.arctan2(h, w)

    tool_size = (float(nf) - 1.0) * distance

    if tool_size <= w:
        retval.append(Containers.Point(w / 2.0 - tool_size / 2.0, h / 2, 0.0, nf, distance, 0.0))

    if tool_size <= h:
        retval.append(Containers.Point(w / 2.0, h / 2.0 - tool_size / 2.0, 0, nf, distance, -90.0))

    if tool_size <= d:
        dir = azimuth_direction(d_angle)
        x_offset = dir[0] * tool_size / 2.0
        y_offset = dir[1] * tool_size / 2.0
        retval.append(
            Containers.Point((w / 2.0) - x_offset, (h / 2.0) - y_offset, 0.0, nf, distance, numpy.degrees(d_angle)))

    if len(retval) == 0:
        raise Exception("DUT is too small compared to multifinger to perform multifinger tap.")

    return retval


def create_fingermulti_swipe_diagonal(dut, num_of_fingers, finger_distance, border_width, start_points):
    """
    In diagonal multifinger swipe we want to do two swipes along both of the
    diagonals in the middle of the screen
    :param dut: the target dut
    :param num_of_fingers: number of fingers in the multifinger tool
    :param finger_distance: distance between fingers in the multifinger tool
    :param border_width: width of the border area
    :param start_points: List of start points of swipe ('top_left' or 'top_right').
    :return: List of Container.Line object(s)
    """
    dut_width = dut.width
    dut_height = dut.height
    tool_width = (num_of_fingers - 1) * finger_distance
    lines = []
    # If swipe is shorter than this an error will be raised <- the tool is too wide for the DUT
    MIN_SWIPE_LENGTH = 2  # mm

    for start_point in start_points:
        if start_point == 'top_left':
            start_corner = [0, 0]
            end_corner = [dut_width, dut_height]
            # The swipe is done diagonally. This is the angle between swipe and dut in width (x) direction
            # x-axis is the zero axis and anti-clockwise is positive direction
            azimuth = -numpy.degrees(numpy.arctan2(dut_height, dut_width))
            # We need to rotate the tool to make it perpendicular to the swipe angle
            azimuth -= 90
        elif start_point == 'top_right':
            start_corner = [dut_width, 0]
            end_corner = [0, dut_height]
            # The swipe is done diagonally. This is the angle between swipe and dut in width (x) direction
            # x-axis is the zero axis and anti-clockwise is positive direction
            azimuth = numpy.degrees(numpy.arctan2(dut_height, dut_width)) - 180
            # We need to rotate the tool to make it perpendicular to the swipe angle
            azimuth += 90
        else:
            assert False

        # The unit components of the swipe normal vector
        unit_vec = azimuth_direction(numpy.radians(azimuth))

        # Next we calculate the line the first finger has when the tool mid point
        # travels across the diagonal. This is done by moving the end and start points
        # by the amount and direction of half of the tool.
        start_x = start_corner[0] - (tool_width / 2) * unit_vec[0]
        start_y = start_corner[1] - (tool_width / 2) * unit_vec[1]
        start_z = 0
        end_x = end_corner[0] - (tool_width / 2) * unit_vec[0]
        end_y = end_corner[1] - (tool_width / 2) * unit_vec[1]
        end_z = 0

        # then the line needs to be clipped to take border width into account
        line_first = Containers.Line(start_x, start_y, start_z, end_x, end_y, end_z,
                                     num_of_fingers, finger_distance, azimuth)

        clip_line_to_rectangle(line_first, dut_width, dut_height, border_width, border_width)

        # Then we do the same for the for the last finger. The only difference from the first finger is
        # that the "half-tool-vector" is in opposite direction:
        start_x = start_corner[0] + (tool_width / 2) * unit_vec[0]
        start_y = start_corner[1] + (tool_width / 2) * unit_vec[1]
        start_z = 0
        end_x = end_corner[0] + (tool_width / 2) * unit_vec[0]
        end_y = end_corner[1] + (tool_width / 2) * unit_vec[1]
        end_z = 0

        # then the line needs to be clipped to take border width into account
        line_last = Containers.Line(start_x, start_y, start_z, end_x, end_y, end_z,
                                    num_of_fingers, finger_distance, azimuth)

        clip_line_to_rectangle(line_last, dut_width, dut_height, border_width, border_width)

        # Depending on the dut shape we need to either limit the start or end of the
        # first finger line by the last finger line
        if dut_width > dut_height:
            line_first.end_x = line_last.end_x - tool_width * unit_vec[0]
            line_first.end_y = line_last.end_y - tool_width * unit_vec[1]
        else:  # dut_width <= dut_height
            line_first.start_x = line_last.start_x - tool_width * unit_vec[0]
            line_first.start_y = line_last.start_y - tool_width * unit_vec[1]

        # Checking if the resulting line is long enough
        line_length = line_first.length()
        if line_length > MIN_SWIPE_LENGTH:
            lines.append(line_first)

    return lines


def create_multifinger_swipe(dut, nf, distance):
    retval = []

    w = dut.width
    h = dut.height

    tool_size = (float(nf) - 1.0) * distance

    if tool_size < w:
        sx = w / 2.0 - tool_size / 2.0
        ex = sx
        sy = h
        ey = 0

        retval.append(Containers.Line(sx, sy, 0, ex, ey, 0, nf, distance, 0.0))

    if tool_size < h:
        sx = 0
        ex = w
        sy = h / 2.0 - tool_size / 2.0
        ey = sy

        retval.append(Containers.Line(sx, sy, 0, ex, ey, 0, nf, distance, -90.0))

    retval += create_fingermulti_swipe_diagonal(dut, nf, distance, 0, ['top_left'])

    if len(retval) == 0:
        raise Exception("DUT is too small compared to multifinger to perform multifinger swipe.")

    return retval


def create_separation(dut, start_separation, num_steps, step_size, angles):
    """
    Create robot points for separation test.
    :param dut: DUT to create points for.
    :param start_separation: Start separation in mm.
    :param num_steps: Number of separation steps.
    :param step_size: Separation step size in mm.
    :param angles: List of azimuth angles in deg.
    :return: List of points.
    """
    retval = []

    w = dut.width
    h = dut.height
    nf = 2

    for angle in angles:
        for i in range(num_steps):
            separation = start_separation + i * step_size

            # Validate separation angle by ensuring the second finger is also inside the DUT screen area.
            # Note that first finger is at DUT center so the second finger is separation away from DUT center

            pos = azimuth_direction(angle)

            if abs(pos[0] * separation) > dut.width / 2 or abs(pos[1] * separation) > dut.height / 2:
                raise Exception(
                    "Separation {} at angle {} causes robot to exceed DUT limits.".format(separation, angle))

            retval.append(Containers.Point(w / 2.0, h / 2.0, 0.0, nf, separation, angle, 0))

    return retval
