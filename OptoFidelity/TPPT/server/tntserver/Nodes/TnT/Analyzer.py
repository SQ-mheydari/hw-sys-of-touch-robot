import logging
import importlib
from tntserver.Nodes.Node import Node, json_out, NotFound
from tntserver.license import LicenseError

log = logging.getLogger(__name__)


class Analysis(Node):
    # This node will not be persisted to configuration
    transient = True

    def __init__(self):
        super().__init__("analysis")

    @json_out
    def handle_path(self, method, path, **kwargs):
        log.info("HTTP %s /%s", method, path)
        if method not in ('post', 'put'):
            raise NotFound()
        image_id = int(path)
        return self.parent.analyze(image_id=image_id, **kwargs)


class Analyzer(Node):
    """
    TnT compatible analyzer resource
    """
    def __init__(self, name):
        super().__init__(name)

        # piggyback detection path for compatibility
        analysis = Analysis()
        self.add_child(analysis)
        analysis._init()

        self._driver = None

    def _init(self, driver: str, **kwargs):
        # Dynamically import the module for the analyzer and initialize a class instance as the driver
        # Assumes that the class name is the same as the module name, i.e. Abbyy - Abbyy
        driver_module = importlib.import_module('tntserver.drivers.analyzers.' + driver)
        driver_class = getattr(driver_module, driver)

        try:
            self._driver = driver_class(**kwargs)
        except LicenseError as e:
            log.error(str(e))

    def analyze(self, **kwargs):
        """
            :param kwargs: analyzer specific arguments, e.g. "language"
            :return: Analyzed results
        """
        result = self._driver.analyze(**kwargs)
        return result

    @json_out
    def handle_path(self, method, path, **kwargs):
        log.info("HTTP %s /%s", method, path)

        if self._driver is None:
            raise Exception("{} driver is not initialized. This could be due to insufficient license.".format(self.name))

        function = getattr(self._driver, path)

        if function.__name__.startswith('_'):
            raise Exception("Attempting to access private functions of {}".format(self.name))
        return function(**kwargs)
