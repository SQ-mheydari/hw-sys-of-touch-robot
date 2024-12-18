import logging
import time

from tntserver.Nodes.Node import *
from tntserver.drivers.sensors.pykern import KernScaleDriver

log = logging.getLogger(__name__)


'''
Example configuration for NodeKern.
Please check that COM port is correct one!

- name: scale
  path: scale
  cls: Nodes.NodeKern
  parent: ws
  connection: ws
  properties: {}
  frame:
  - [0, 1, 0, 378]
  - [-1, 0, 0, 131]
  - [0, 0, 1, 25]
  - [0, 0, 0, 1]
  arguments:
    sample_rate: 10
    port: COM4
    
For force calibration to use scale, change sensor argument to "scale".

This file requires pyserial, install it into virtualenv with
`pip install pyserial`
'''


class NodeKern(Node):

    @json_out
    def get_forcevalue(self):
        """
        Returns force sensor reading in grams
        """
        return self._get_value()

    @json_out
    def put_tare(self, timeout_s: float = 5):
        """
        Zeroes the scale reading

        :param timeout_s: How many seconds to try before giving up
        """
        return self.tare_sensor(timeout_s)

    def tare_sensor(self, timeout_s):
        success = self._get_driver().tare_sensor(timeout=timeout_s)
        if not success:
            raise NodeException("Unable to tare", 500, ["Scale value does not stabilize in {} seconds".
                                format(timeout_s)])

    def pump_values(self):
        """
        Pump tared values.

        :return: Generator that yields tared values
        """
        return self._pump_values(self._get_value)

    def _pump_values(self, supplier):
        while True:
            gram = supplier()
            if gram is not None:
                yield gram
                time.sleep(1.0/self._sample_rate)

    def _get_value(self):
        return self._get_driver().get_instant_value()

    def read_tared_force(self):
        return self._get_value()

    def _get_driver(self):
        if self._driver is None:
            try:
                self._driver = KernScaleDriver(self._port, self._sample_rate)
            except Exception:
                log.error("Kern scale not available. Please check serial connection and provided serial port: %s.",
                          self._port)
        return self._driver

    def _init(self, port, sample_rate, **kwargs):
        self._port = port
        self._sample_rate = sample_rate
        self._driver = None
        self._get_driver()
