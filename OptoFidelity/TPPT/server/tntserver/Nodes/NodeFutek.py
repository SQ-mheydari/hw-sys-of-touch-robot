import logging
import statistics
import threading
import time

from tntserver.Nodes.Node import *
from tntserver.drivers.sensors.pyfutek import ForceSensor, ForceSensorStub
from tntserver.itertools import window

log = logging.getLogger(__name__)


class NodeFutek(Node):
    def __init__(self, name):
        super().__init__(name)

        self._force_buffer = []
        self._buffer_thread = None
        self._buffer_event = threading.Event()

    @json_out
    def put_start_buffering(self, duration=10.0):
        """
        Start buffering force values.
        :param duration: Time limit for buffering.
        """
        if self._buffer_thread is not None:
            self._buffer_thread.join()

        def worker():
            start_time = time.time()

            while time.time() - start_time < duration and not self._buffer_event.is_set():
                self._force_buffer.append(self.read_tared_force())

        self._buffer_event.clear()
        self._force_buffer = []

        self._buffer_thread = threading.Thread(target=worker)
        self._buffer_thread.start()

    @json_out
    def put_stop_buffering(self):
        """
        Stop buffering force values.
        """
        if self._buffer_thread is None:
            return

        self._buffer_event.set()
        self._buffer_thread.join()
        self._buffer_thread = None

    @json_out
    def get_buffer(self):
        """
        Get force buffer.
        :return: Force values as list.
        """
        return self._force_buffer

    @json_out
    def get_forcevalue(self):
        """
        Returns force sensor reading in grams
        """
        return self.read_tared_force()

    @json_out
    def put_tare(self, window_size: float = 50, gram_diff: float = 0.1, timeout_s: float = 5):
        """
        Tare sensor based on given parameters.
        :param window_size: How many samples to take when accounting if force is stabilized
        :param gram_diff: How many gram difference is allowed for samples
        :param timeout_s: How many seconds to try before giving up
        """
        self.tare_sensor(window_size=window_size, gram_diff=gram_diff, timeout_s=timeout_s)

    def tare_sensor(self, window_size: float = 50, gram_diff: float = 0.1, timeout_s: float = 5):
        """
                Zeroes the force sensor reading

                :param window_size: How many samples to take when accounting if force is stabilized
                :param gram_diff: How many gram difference is allowed for samples
                :param timeout_s: How many seconds to try before giving up
                """
        start_time = time.perf_counter()
        for values in window(self._pump_values(self._get_gramforce), window_size):
            if max(values) - min(values) < gram_diff:
                self._tarevalue = statistics.mean(values)
                return self._tarevalue
            if time.perf_counter() - timeout_s > start_time:
                raise NodeException("Unable to tare", 500, [
                    "Calibration sensor force value does not stabilize in {} seconds".format(timeout_s)])

    def pump_values(self):
        """
        Pump tared values.

        :return: Generator that yields tared values
        """
        return self._pump_values(self.read_tared_force)

    def _pump_values(self, supplier):
        while True:
            gram = supplier()
            if gram is not None:
                yield gram
                time.sleep(1.0/self._sample_rate)

    def _get_gramforce(self, retries=3):
        for i in range(retries):
            grams = self._driver.get_gramforce()
            if grams is not None:
                return grams

    def read_tared_force(self):
        try:
            untared = self._get_gramforce()
        except ValueError:
            untared = None

        return untared - self._tarevalue if untared is not None else float("NaN")

    def _init(self, serial_number, number_of_averages, sample_rate, invert_polarity, **kwargs):
        try:
            self._driver = ForceSensor(serial_number, number_of_averages, sample_rate, invert_polarity)
        except:
            log.error("Real force sensor not available. Please check serial number and USB connection.")
            self._driver = ForceSensorStub()

        self._sample_rate = sample_rate
        self._tarevalue = 0.0

        # Start Futek sensor data stream initialization in the background (takes about 10 s). It is however possible
        # that server start-up finishes while the Futek sensor initialization is still in progress. Data readout from
        # the sensor before initialization is complete will throw an exception.
        self._init_thread = threading.Thread(target=self._driver.initialize_datastream, daemon=True).start()

