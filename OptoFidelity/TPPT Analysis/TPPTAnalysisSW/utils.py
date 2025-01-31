# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.
import collections
import glob
import json
from decimal import Decimal
from datetime import datetime
from typing import Optional, Union

import numpy as np

import TPPTAnalysisSW.settings as settings
import TPPTAnalysisSW.measurementdb as db


class Timer(object):
    """ Timer object that can be used for performance timing """

    do_timing = False

    def __init__(self, level=1, *args, **kwargs):
        """ Initialize timer and start timing. """
        result = super(Timer, self).__init__(*args, **kwargs)
        if self.do_timing:
            self.start = datetime.now()
            self.level = level
        return result

    def Time(self, string):
        """ Print out string and elapsed time """
        if self.do_timing:
            print(">>>" + str(self.level) + " " + str(string) + " " + str(datetime.now() - self.start))

def exportcsv(query, initialstring = None, subtable=None):
    ''' exports query to a csv format as a table 
        If optional initialstring is given, the results are appended
        to it. Initialstring should end with '\n' 
        A single subtable can be put to output by giving the subtable
        reference in parent class (as string) '''
    if initialstring is None:
        csvstring = ""
    else:
        csvstring = initialstring

    # Add headers
    headers = ""
    columns = []
    colheaders = [('"' + c.name + '"') for c in query.column_descriptions[0]['type'].__table__.columns]
    headers += settings.csvchars[1].join(colheaders)
    if subtable is not None:
        subtableclass = getattr(query.column_descriptions[0]['type'], subtable).mapper.class_
        subheaders = [('"' + c.name + '"') for c in subtableclass.__table__.columns]
        headers += settings.csvchars[1] + settings.csvchars[1].join(subheaders)
        csvstring += query.column_descriptions[0]['type'].__tablename__ + (settings.csvchars[1] * len(colheaders)) + subtableclass.__tablename__ + '\n'
    csvstring += headers + '\n'

    for line in query:
        linestr = ""

        # Not iterable - only one result
        tablecolumns = line.__table__.columns
        values = [getattr(line, tc.name) for tc in tablecolumns]
        csvvalues = []
        for v in values:
            if isinstance(v, str):
                csvvalues.append('"' + v + '"')
            elif isinstance(v, float):
                csvvalues.append(str(v).replace('.', settings.csvchars[0]))
            else:
                csvvalues.append(str(v))
        linestr += settings.csvchars[1].join(csvvalues)

        if subtable is not None:
            subtablecolumns = subtableclass.__table__.columns
            for subline in getattr(line, subtable):
                subvalues = [getattr(subline, tc.name) for tc in subtablecolumns]
                if len(linestr) == 0:
                    linestr += '\n' + (settings.csvchars[1] * len(tablecolumns))
                else:
                    linestr += settings.csvchars[1]
                csvvalues = []
                for v in subvalues:
                    if isinstance(v, str):
                        csvvalues.append('"' + v + '"')
                    elif isinstance(v, float):
                        csvvalues.append(str(v).replace('.', settings.csvchars[0]))
                    else:
                        csvvalues.append(str(v))
                linestr += settings.csvchars[1].join(csvvalues)
                csvstring += linestr
                linestr = ''

        csvstring += linestr + '\n'

    return csvstring


class JSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that turns non-JSON-serializable types into serializable ones.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, np.int32):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def dict_to_json_string(data: dict) -> bytes:
    """
    Get JSON string from dict. Following type conversions are made to make the data JSON-serializable:
        Decimal -> float
        set -> list
        np.int32 -> int
        np.ndarray -> list
    If there is a nested dictionary with non-serializable keys, the conversion must be made beforehand.
    The result is UTF-8 encoded to allow sending over HTTP.
    :param data: Dict containing data from database.
    :return: UTF-8 encoded JSON string.
    """
    return json.dumps(data, indent=4, cls=JSONEncoder).encode('utf8')


def str_to_float(string: Optional[str]) -> Optional[float]:
    """
    Try to convert string to float. Otherwise return None.
    :param string: Number represented as a string or None.
    :return: Number as float or None.
    """
    if string is None:
        return None
    try:
        return float(string)
    except ValueError:
        return None


def verdict_to_str(verdict: Union[str, bool, None]) -> str:
    """
    Return verdict formatted as a string.
    :param: Verdict as boolean/string or None.
    :return: "Pass", "Fail" or "N/A".
    """
    if verdict is None:
        return "N/A"
    if isinstance(verdict, bool):
        return "Pass" if verdict else "Fail"
    else:
        return verdict


def is_swipe_diagonal(start: tuple, end: tuple) -> bool:
    """
    Swipe is diagonal if both components of end - start are nonzero.
    :param start: Swipe start point.
    :param end: Swipe end point.
    :return: True if swipe is diagonal.
    """
    return abs(end[0] - start[0]) > 1e-6 and abs(end[1] - start[1]) > 1e-6


def swipe_direction(start: tuple, end: tuple) -> str:
    """
    Get rough swipe direction. Used in analysis to differentiate between swipe types since one test can have swipes in
    multiple directions.
    :param start: Swipe start point.
    :param end: Swipe end point.
    :return: "horizontal", "vertical" or "diagonal".
    """
    dx = abs(end[0] - start[0])
    dy = abs(end[1] - start[1])

    if dx > 1e-6:
        if dy > 1e-6:
            return "diagonal"
        else:
            return "horizontal"
    else:
        return "vertical"


def max_not_none(a, b):
    """
    Get maximum of two values. If one of the values is None, return the other one.
    :return: Maximum value or None.
    """
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


def get_total_verdict(*verdicts: str) -> str:
    """
    Return total verdict from individual verdicts.
    - If all verdicts are "Pass", total verdict is "Pass".
    - If any verdict is "N/A", total verdict is "N/A".
    - Otherwise, total verdict is "Fail".
    :param verdicts: Either "Pass", "Fail" or "N/A".
    :return: Either "Pass", "Fail" or "N/A".
    """
    total_verdict = "Pass"
    for verdict in verdicts:
        if verdict == "Fail":
            total_verdict = "Fail"
        elif verdict == "N/A":
            return "N/A"
    return total_verdict


def get_limit_verdict(value: Union[float, None], limit: Decimal, lower_bound: bool = False) -> str:
    """
    Check that value is at most equal to limit. If value is None, verdict is "N/A".
    :param value: Measurement results.
    :param limit: Upper bound for quantity.
    :param lower_bound: If True, use limit as lower bound.
    :return: Either "Pass", "Fail" or "N/A".
    """
    if value is None:
        return "N/A"
    if lower_bound:
        return verdict_to_str(limit <= value)
    return verdict_to_str(value <= limit)


def database_files(dirpath: str = "C:/OptoFidelity/TPPT") -> collections.OrderedDict:
    """
    Get all database files in directory.
    :param dirpath: Directory where the .sqlite database files are located.
    :return: Ordered dict with filename as key in alphabetical order. The value will be 'selected' if it is the
        currently loaded database, otherwise None.
    """

    files = glob.glob(dirpath + "/*.sqlite")
    current = db.get_database().dbpath.replace("\\", "/")

    paths = {}

    for f in files:
        if current == f.replace("\\", "/"):
            paths[f] = "selected"
        else:
            paths[f] = None

    files = collections.OrderedDict(sorted(paths.items(), key=lambda t: t[0].lower()))

    return files
