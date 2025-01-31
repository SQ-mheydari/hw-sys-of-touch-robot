import serial
import re
import time

_N_message = 18


class KernScaleDriver(object):

    def __init__(self, port, sample_rate=10, baudrate=19200, timeout=30):
        self.ser = serial.Serial(port=port, baudrate=baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE, timeout=timeout)
        self.loop_sleep = 1.0/sample_rate

    def get_stable_value(self):
        self.ser.write('w'.encode())
        retstr = self._read()
        while retstr.find('g'.encode()) == -1:
            self.ser.write('w'.encode())
            retstr = self._read()
            time.sleep(self.loop_sleep)

        match = re.search(r'[\d.]+'.encode(), retstr)
        return float(match.group())

    def get_instant_value(self):
        self.ser.write('w'.encode())
        retstr = self._read()
        match = re.search(r'[\d.]+'.encode(), retstr)
        return float(match.group())

    def tare_sensor(self, timeout):
        start = time.perf_counter()

        self.ser.write('t'.encode())
        self.ser.write('w'.encode())
        retstr = self._read()
        while retstr.find('0.00'.encode()) == -1:
            self.ser.write('w'.encode())
            retstr = self._read()
            time.sleep(self.loop_sleep)
            if time.perf_counter() - start > timeout:
                return False
        return True

    def _read(self):
        retstr = self.ser.read(size=_N_message)
        return retstr


def main():
    print("Opening serial")
    scale = KernScaleDriver("COM9")
    print("Taring..")
    scale.tare_sensor(timeout=10)
    print("Place weight on scale...")
    while scale.get_instant_value() < 0.01:
        pass
    print("Weighting...")
    weight = scale.get_stable_value()
    print("Weight was: %2.2f g" % weight)


if __name__ == "__main__":
    main()
