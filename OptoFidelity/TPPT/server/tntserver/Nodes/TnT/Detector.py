import logging
import importlib

from tntserver.Nodes.Node import Node, json_out, NotFound, private

log = logging.getLogger(__name__)


class Detection(Node):
    # This node will not be persisted to configuration
    transient = True

    def __init__(self):
        super().__init__("detection")

    @json_out
    def handle_path(self, method, path, **kwargs):
        log.info("HTTP %s /%s", method, path)
        if method not in ('post', 'put'):
            raise NotFound()
        image_id = int(path)
        return self.parent.detect(image_id=image_id, **kwargs)


class Detector(Node):
    """
    TnT compatible detector resource
    """
    def __init__(self, name):
        super().__init__(name)

        # piggyback detection path for compatibility
        detection = Detection()
        self.add_child(detection)
        detection._init()

        self._driver = None

    def _init(self, driver: str, **kwargs):
        # Dynamically import the module for the analyzer and initialize a class instance as the driver
        # Assumes that the class is the module name capitalized, i.e. abbyy - Abbyy
        driver_module = importlib.import_module('tntserver.drivers.detectors.' + driver)
        driver_class = getattr(driver_module, driver)
        self._driver = driver_class(**kwargs)

    def detect(self, **kwargs):
        return self._driver.detect(**kwargs)

    @json_out
    def handle_path(self, method, path, **kwargs):
        log.info("HTTP %s /%s", method, path)

        if self._driver is None:
            raise Exception(
                "{} driver is not initialized. This could be due to insufficient license.".format(self.name))

        function = getattr(self._driver, path)

        if method in ['get']:
            return function()
        else:
            return function(**kwargs)

    @property
    @private
    def driver(self):
        return self._driver
