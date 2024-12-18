import numpy as np
from typing import List, Dict
from decimal import Decimal


def get_distance_2d(points):
    """Calculate 2d distance between consecutive positions in a list."""
    diff = np.diff(points, axis=0)
    return np.sqrt((diff ** 2).sum(axis=1))


def detect_incomplete_swipes(swipe_points: np.ndarray, max_discontinuity: Decimal = Decimal(5.0)) -> List[Dict]:
    """Detects gaps between swipe points during each swipe. Returns a list of Lines where there is no contact."""

    failure_lines = []
    if len(swipe_points) > 0:
        dist = get_distance_2d(swipe_points)

        gaps_indices = np.where(dist > max_discontinuity)[0]

        for failure_start_point in gaps_indices:
            failed_line = {"start_point": swipe_points[failure_start_point],
                           "end_point": swipe_points[failure_start_point + 1]}

            failure_lines.append(failed_line)

    return failure_lines
