from .Node import *
from .script_config import *


class SettingsNode(Node):
    """
    Node that stores general settings for running test cases.
    """
    def __init__(self, context):
        super().__init__('Settings')

        self.context = context

        self.controls.line_drawing_speed = "100.0"
        self.controls.info['line_drawing_speed'] = {'label': 'Line drawing speed [mm/s]', 'min': 1,
                                                    'tooltip': self.context.tooltips['Line drawing speed']}
        self.controls.default_speed = 100.0
        self.controls.info['default_speed'] = {'label': 'Default speed [mm/s]', 'min': 1,
                                               'tooltip': self.context.tooltips['Default speed']}
        self.controls.default_acceleration = 200.0
        self.controls.info['default_acceleration'] = {'label': 'Default acceleration [mm/s^2]', 'min': 1,
                                                      'tooltip': self.context.tooltips['Default acceleration']}

        if get_config_value('enable_force'):
            self.controls.force_application = 'None'
            self.controls.info['force_application'] = {'label': 'Force application method',
                                                       'items': ['None', 'Force gesture']}

            self.controls.default_force = 100.0
            self.controls.info['default_force'] = {'label': 'Force to apply [gF]', 'min': 1.0}
