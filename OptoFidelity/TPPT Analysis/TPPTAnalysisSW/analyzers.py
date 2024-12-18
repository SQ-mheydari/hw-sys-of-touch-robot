# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

#Analysis functions for analyzing measurements
import numpy as np
from .settings import get_setting, precision
import math
from collections import deque
from decimal import Decimal
import TPPTAnalysisSW.transform2d as transform2d
from .plotinfo import *

#
# Rounding
#

def round_dec(number):

    if number is None:
        return None
    else:
        return Decimal.quantize(Decimal(number), precision)

#
# Edge analysis for tap and multifinger tap (and others?)
#

def is_edge_point(point, dutinfo):
    ''' Checks if given target point is in the edge area of DUT '''
    # Check if we are in the edge area
    edge = False
    if point[0] <= get_setting('edgelimit', dutinfo.sample_id):
        edge = True
    elif point[1] <= get_setting('edgelimit', dutinfo.sample_id):
        edge = True
    elif point[0] >= dutinfo.dimensions[0] - float(get_setting('edgelimit', dutinfo.sample_id)):
        edge = True
    elif point[1] >= dutinfo.dimensions[1] - float(get_setting('edgelimit', dutinfo.sample_id)):
        edge = True

    return edge


def mean(values) -> float:
    """
    Calculates mean of values after filterin out float(nan) and None items
    :param values: List or array of values
    :return: Mean of given values
    """

    ret = []
    for value in values:
        if value is None:
            continue
        elif np.isnan(float(value)):
            continue
        else:
            ret.append(value)
    return float(np.mean(ret))

def get_max_error(point, dutinfo):
    ''' Returns the maximum error for given target point (tests edge area) '''
    max_error = float('nan')
    edge = False
    # Check if we should do edge analysis
    if get_setting('edgelimit', dutinfo.sample_id) >= 0:
        edge = is_edge_point(point,dutinfo)
    if edge:
        # edge area
        max_error = get_setting('edgepositioningerror', dutinfo.sample_id)
    else:
        # Normal point
        max_error = get_setting('maxposerror', dutinfo.sample_id)

    return max_error

#
# Coordinate transform functions
#

def panel_to_target(points, dutinfo):
    """ Maps panel pixel coordinates - (x,y) tuple or list of tuples - to target coordinates. """
    return panel_to_target_transform(dutinfo).transform(points)

def panel_to_target_angle(angle):
    """ Maps panel angles (radians) to degrees. """
    return round_dec(np.degrees(angle))

def panel_to_target_transform(dutinfo):
    """ Returns the Transform2D object that does the transform from panel to target coordinate system """
    dimensions = dutinfo.dimensions             # Size of target (in mm)
    resolution = dutinfo.digitizer_resolution   # Resolution of target (in pixels)
    offset = dutinfo.offset                     # Offset of panel->target conversion (in mm)

    # First: possible switches
    tinit = transform2d.Transform2D.identity()

    if dutinfo.switchxy:
        tinit = tinit + transform2d.Transform2D([[0, 1, 0], [1, 0, 0]])
    if dutinfo.flipx:
        # Make a mirroring transform along x-axis
        tinit = tinit + transform2d.Transform2D([[-1, 0, resolution[0]], [0, 1, 0]])
    if dutinfo.flipy:
        tinit = tinit + transform2d.Transform2D([[1, 0, 0], [0, -1, resolution[1]]])

    # Pixels per mm values
    sx = float(dimensions[0])/float(resolution[0])
    sy = float(dimensions[1])/float(resolution[1])

    scale = transform2d.Transform2D.scale(sx,sy)
    toffset = transform2d.Transform2D.offset(offset[0],offset[1])

    transition = tinit + scale + toffset

    return transition

def robot_to_target(points, dutinfo):
    """Maps robot pixel coordinates - (x,y) tuple or list of tuples - to target coordinates."""

    # Currently does nothing
    return points

def robot_to_target_angle(angle, dutinfo):
    """Maps robot angles (degrees) to radians. """
    # Currently does nothing
    return angle

def robot_to_target_transform(dutinfo):
    """ Returns the Transform2D object that does the transform from robot to target coordinate system """
    # Currently does nothing
    return transform2d.Transform2D.offset(0,0) # Identity

def target_to_swipe(points, swipe_start, swipe_end):
    """Maps swipe (target) coordinates - (x,y) tuple or list of tuples - to swipe (length, offset) coordinates."""
    return target_to_swipe_transform(swipe_start, swipe_end).transform(points)

def target_to_swipe_transform(swipe_start, swipe_end):
    """ Returns the Transform2D object that does the transform from swipe (target) coordinates to swipe (length, offset) coordinates """
    direction = (swipe_end[0] - swipe_start[0], swipe_end[1] - swipe_start[1]) # vector swipe start->end
    angle = math.atan2(direction[1], direction[0]) # Angle of the swipe (start->end)
    transform = transform2d.Transform2D.offset(-swipe_start[0], -swipe_start[1]) + transform2d.Transform2D.rotate_radians(-angle)
    return transform

#
# Test session information functions
#

def panel_mm_per_pixel(dutinfo):
    """ Returns the pixels per mm value of the target panel in a tuple (x_resolution, y_resolution) """
    dimensions = dutinfo.dimensions
    resolution = dutinfo.digitizer_resolution

    sx = float(dimensions[0])/float(resolution[0])
    sy = float(dimensions[1])/float(resolution[1])

    return (sx, sy)

#
# Analysis functions
#

def analyze_swipe_jitter(points, window_length=10.0):
    """ Analyzes jitter for swipe points that have been transformed to coordinate system
        (swipe-direction, perpendicular-to-swipe) with origo at swipe begin and positive x-axle to
        swipe direction. Jitter is calculated with sliding window of length window_length

        Returns dictionary {'jitters' (list), 'max_jitter', 'backwards_points' (count), 'repeated_points' (count)}

        First point jitter is always None, and in case of
        backwards movement or repeated measurements jitter is float('nan') to signal failed point """

    assert(window_length > 0.0)

    jitters = []
    previous_x = None
    previous_y = None
    backwards_points = 0
    repeated_points = 0
    window = deque()
    max_jitter = None

    for point in points:
        if previous_x is None:
            previous_x = point[0]
            previous_y = point[1]
            jitters.append(None)
            window.append(point)
        elif point[0] < previous_x:
            # Backwards movement
            backwards_points += 1
            jitters.append(float('nan'))
        elif point[0] == previous_x and point[1] == previous_y:
            # Repeated measurement
            repeated_points += 1
            jitters.append(float('nan'))
        else:
            # Moving forward or at least not backwards...
            window.append(point)
            while window[0][0] < (point[0] - window_length):
                window.popleft() # Can never remove the point itself

            # Find out the minimum and maximum offsets in window
            offsets = [p[1] for p in window]
            window_min = min(offsets)
            window_max = max(offsets)
            jitter = window_max - window_min        # Peak-to-peak
            jitters.append(jitter)
            if max_jitter is None or jitter > max_jitter:
                max_jitter = jitter

    average_jitter = None
    if len(jitters) > 0:
        average_jitter = mean(jitters[1:])

    results = {'jitters': jitters,
               'max_jitter': max_jitter,
               'backwards_points': backwards_points,
               'repeated_points': repeated_points,
               'average_jitter': average_jitter}

    return results

def analyze_swipe_linearity(points):
    """
    Calculates linear fit for a single swipe line
    Determine max, avg and rms errors from linear fit
    """
    if len(points) == 0:
        results = {'linear_error': [],
                   'lin_error_max': float('nan'),
                   'lin_error_avg': float('nan'),
                   'lin_error_rms': float('nan'),
                   'linear_fit': []}
        return results

    x = []
    y = []
    for point in points:
        x.append(point[0])
        y.append(point[1])

    # Linearfit to fit the data 
    # Linearcoef has slope (1) and intercept (2)
    linearcoef = np.polyfit(x, y, 1)
    linearfit = np.polyval(linearcoef, x)

    # Starndard form of linear equation
    # ax + by + c = 0
    a = linearcoef[0]
    b = -1
    c = linearcoef[1]

    # Max deviation calc: orthogonal distance 
    # from fit line to data set
    lin_error = np.absolute(a * np.array(x) + b * np.array(y) + c) / math.sqrt(a**2 + b**2)

    lin_error_max = max(lin_error)
    lin_error_avg = np.mean(lin_error)
    lin_error_rms = np.sqrt(np.mean(np.power(lin_error, 2)))

    results = {'linear_error': lin_error.tolist(),
               'lin_error_max': lin_error_max,
               'lin_error_avg': lin_error_avg,
               'lin_error_rms': lin_error_rms,
               'linear_fit': linearfit}

    return results


#
# Multifinger functions
#


def find_closest_id_match(normsdict):
    """ Finds the closest match for set of ids to an array. Used in the
        multifinger tap and multifinger swipe. The normsdict is a dictionary,
        whose keys are the finger_ids from database, and each dictionary element
        contains array of distances to the points (lines) to which the ids are to be mapped.
        The function tries to find the closest match from id to a point and returns
        an array, where each index holds the closest point (line) """

    numids = len(normsdict.keys())

    # Attempt #1: closest point
    fingerids = None
    for id, norms in normsdict.items():
        if fingerids is None:
            # Only in the first round
            numpoints = len(norms)
            fingerids = [None] * numpoints

        mindist = np.argmin(norms)
        if fingerids[mindist] is None:
            fingerids[mindist] = [id]
        else:
            fingerids[mindist].append(id)

    if fingerids.count(None) == 0 or fingerids.count(None) == numpoints - numids:
        # We have a match
        #print "Match from round #1: " + str(fingerids)
        pass
    else:
        # Attempt #2: find the closest match using brute force search. As a norm use minimum of sum of squares
        # WARNING: This is slow algorithm if number fo finger_ids grows too large...
        fids = find_smallest_error(normsdict)

        # Found match
        #print "Match from round #2: " + str(fids)
        fingerids = fids

    return fingerids

def find_smallest_error(normsdict):
    """ Finds a best match for least-square matching problem, where each point is
        referenced only one, or every point has just one id or less """

    # Recursive algorithm using brute force search
    # Current best norm is used as a threshold - if the norm would be larger, search is not continued
    ids = list(normsdict.keys())
    norm, smallest_fids = find_smallest_remaining(normsdict, ids, [None] * len(normsdict[ids[0]]), 0.0, float('inf'))

    return smallest_fids

def find_smallest_remaining(normsdict, unset_ids, fixed_ids, current_norm, threshold_norm):
    ''' Recursive algorithm: unset_ids are the ids not yet set, fixed ids is the array,
        to which the ids are set/collected, threshold norm is the norm, after which the calculation is cut off '''

    # Recursion round: take the first id
    current_id = unset_ids[0]
    remaining_ids = unset_ids[1:]
    min_norm = threshold_norm
    min_ids = None

    for i, dist in enumerate(normsdict[current_id]):
        if current_norm + dist >= min_norm:
            # Do not continue calculation -> the result would be larger
            # than current minimum
            continue

        # Fix the current id at position i (attempt)
        new_fixed = list(fixed_ids) # Have to make a copy - lists are mutable
        if new_fixed[i] is None:
            new_fixed[i] = [current_id]
        else:
            # Check if this attempt would be legal
            if new_fixed.count(None) > len(remaining_ids):
                # Not enough ids left to fill the remaining empty places
                continue
            new_fixed[i] = list(new_fixed[i]) # Ditto
            new_fixed[i].append(current_id)

        # Calculate the new norm with this assumption
        if len(remaining_ids) > 0:
            new_norm, new_ids = find_smallest_remaining(normsdict, remaining_ids, new_fixed, current_norm + dist**2, min_norm)
        else:
            # This was last id
            new_norm = current_norm + dist**2
            new_ids = new_fixed

        if new_ids is not None:
            max_length = max([0 if l is None else len(l) for l in new_ids])
            if None in new_ids and max_length > 1:
                # Illegal solution: empty spaces combined with arrays with length > 1
                pass
            elif new_norm < min_norm:
                min_norm = new_norm
                min_ids = new_ids

    return (min_norm, min_ids)

def bounding_box(vector):
    """ Returns bounding box for an array of points [[x,y], [x,y], ...] """
    min_x, min_y = np.min(vector, axis=0)
    max_x, max_y = np.max(vector, axis=0)
    return np.array([(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)])
