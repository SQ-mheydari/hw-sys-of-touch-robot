from tntserver.Nodes.NodeTriggerSensor import *
from tntserver.Nodes.Node import Node
from tntserver.drivers.sensors.video import VideoSensor

log = logging.getLogger(__name__)


class NodeVideoSensor(NodeTriggerSensor):
    """
    Node for OptoFidelity Video Multimeter, renamed here to videosensor.
    """

    def __init__(self, name):
        super().__init__(name)

    def _init(self, port, **kwargs):
        self._port = port
        self._driver = None
        self._trigger_threshold = kwargs.get("trigger_threshold", None)
        self._simulation = kwargs.get("simulation", False)
        self._watchdog_enabled = kwargs.get("watchdog_enabled", True)
        self._motherboard_trigger_sensor = kwargs.get('motherboard_trigger_sensor', None)

        # Find motherboard trigger sensor Node instance based on name if given
        if self._motherboard_trigger_sensor is not None:
            self._motherboard_trigger_sensor = Node.find(self._motherboard_trigger_sensor)
        try:
            self._set_driver()
            self._driver.open_backlight_info_app()
            self._driver.open_camera_trigger_app()
            if self._trigger_threshold is not None:
                self.set_encoder_trigger_threshold(self._trigger_threshold)
        except Exception as e:
            log.error("Videosensor init failed: " + str(e))

    def _set_driver(self):
        if self._driver is None:
            try:
                self._driver = VideoSensor(self._port, watchdog_enabled=self._watchdog_enabled,
                                           simulation=self._simulation)
            except Exception as e:
                log.error("Unable to establish connection to videosensor. Please check USB connection and provided "
                          "serial port: {}".format(self._port))
                raise e
        return self._driver

    @json_out
    def get_backlight_period(self):
        """
        Return display backlight period in seconds.
        :return: Backlight period in seconds.
        """
        return self.backlight_period_ms() / 1000.0

    @json_out
    def put_set_trigger_mode_backlight(self):
        """
        Set triggering pulse generation to backlight (no regard to encoder).
        :return: None
        """
        self.set_trigger_mode_backlight()

    def init_auto_trigger(self):
        """
        Initialize sensor for handling automatic trigger.
        """
        self.set_trigger_mode_backlight_encoder()
        self.reset_encoder_value()
        if self._motherboard_trigger_sensor is not None:
            self._motherboard_trigger_sensor.init_auto_trigger()

    # See self._driver docstrings for function comments.
    def backlight_period_ms(self):
        return self._driver.get_backlight_period_us() / 1000.0

    def reset_encoder_value(self):
        if self._motherboard_trigger_sensor is not None:
            self._motherboard_trigger_sensor.reset_encoder_value()

        return self._driver.reset_encoder_value()

    def set_encoder_trigger_threshold(self, value):
        self._driver.set_encoder_trigger_threshold(value)

    def get_encoder_trigger_threshold(self):
        return self._driver.get_encoder_trigger_threshold()

    def set_trigger_backlight_rising(self):
        self._driver.set_trigger_backlight_rising()

    def set_trigger_backlight_falling(self):
        self._driver.set_trigger_backlight_falling()

    def set_trigger_touch_start(self):
        self._driver.set_trigger_touch_start()
        if self._motherboard_trigger_sensor is not None:
            self._motherboard_trigger_sensor.set_trigger_touch_start()

    def set_trigger_touch_end(self):
        self._driver.set_trigger_touch_end()
        if self._motherboard_trigger_sensor is not None:
            self._motherboard_trigger_sensor.set_trigger_touch_end()

    def set_trigger_mode_frames(self):
        self._driver.set_trigger_mode_frames()

    def set_trigger_mode_backlight(self):
        self._driver.set_trigger_mode_backlight()

    def set_trigger_mode_backlight_encoder(self):
        self._driver.set_trigger_mode_backlight_encoder()

    def exit_application(self):
        self._driver.exit_application()

    def open_camera_trigger_app(self):
        self._driver.open_camera_trigger_app()
