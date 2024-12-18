from tntserver.Nodes.Node import *

log = logging.getLogger(__name__)


class NodeTriggerSensor(Node):
    """
    Base node for trigger solutions.
    """

    def __init__(self, name):
        super().__init__(name)
        self._driver = None

    def _init(self, **kwargs):
        raise Exception("NodeTriggerSensor is an abstract base class that shouldn't be created")

    def init_auto_trigger(self):
        """
        Initialize sensor for handling automatic trigger. By default, just reset encoder value.
        """
        self.reset_encoder_value()

    def reset_encoder_value(self):
        """
        Reset internal encoder pulse counter value to 0.
        :return: Device response to command.
        """
        return self._driver.reset_encoder_value()

    def set_trigger_touch_start(self):
        """
        Set camera sync pulse triggering to single pulse output. Generate one pulse when finger touches the DUT
        or other surface.
        """
        self._driver.set_trigger_touch_start()

    def set_trigger_touch_end(self):
        """
        Set camera sync pulse triggering to single pulse output. Generate one pulse when finger releases up from the
        DUT or other surface.
        """
        self._driver.set_trigger_touch_end()
