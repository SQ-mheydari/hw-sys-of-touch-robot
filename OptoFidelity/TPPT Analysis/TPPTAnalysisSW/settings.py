# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

from decimal import Decimal
from .measurementdb import Setting

settings = {}

precision = Decimal("0.001") # Precision to use in calculations

setting_categories = {'One Finger First Contact Latency Test': ['maxactiveresponselatency', 'maxidleresponselatency'],
                      'One Finger Non Stationary Reporting Rate Test': ['minreportingrate', 'minavgreportingrate'],
                      'One Finger Swipe Test': ['maxoffset', 'maxjitter', 'jittermask', 'maxmissingswipes',
                                                'maxswipediscontinuity', 'maxincompleteswipes', 'maxdiagoffset',
                                                'maxdiagjitter'],
                      'One Finger Tap Test': ['edgelimit', 'maxposerror', 'maxmissing', 'edgepositioningerror',
                                              'maxedgemissing'],
                      'One Finger Tap Repeatability': ['maxrepeaterror'],
                      'One Finger Stationary Jitter': ['maxstationaryjitter'],
                      'One Finger Stationary Reporting Rate Test': ['minreportingrate', 'minavgreportingrate'],
                      'MultiFinger Tap Test': ['edgelimit', 'maxposerror', 'maxmissing', 'edgepositioningerror',
                                               'maxedgemissing'],
                      'MultiFinger Swipe Test': ['maxoffset', 'maxjitter', 'jittermask', 'maxmissingswipes',
                                                 'maxswipediscontinuity', 'maxincompleteswipes', 'maxdiagoffset',
                                                 'maxdiagjitter'],
                      'Separation Test': ['maxseparation', 'maxdiagseparation'],
                      'Pinch Test': ['maxseparation', 'maxdiagseparation', 'maxoffset'],
                      }

csvchars = ".,"


def loadSettings(dbsession):
    global settings
    dbSettings = dbsession.query(Setting).all()

    settings.clear()
    for s in dbSettings:
        settings[(s.name, s.dut)] = Decimal.quantize(Decimal(s.value), precision)


def get_setting(name: str, dut: str = "") -> Decimal:
    """
    Get DUT specific setting. If setting is not found, return default setting.
    :param name: Name of setting.
    :param dut: Name of DUT. If not given, will return default setting.
    """
    if (name, dut) in settings:
        return settings[(name, dut)]
    return settings[(name, "")]


def get_settings_by_dut() -> dict:
    """
    Get all settings saved to database grouped by DUT name.
    :return: Settings as a nested dict.
    """
    dut_settings = {}
    for (name, dut), value in settings.items():
        if dut not in dut_settings:
            dut_settings[dut] = {}
        dut_settings[dut][name] = value

    return dut_settings
