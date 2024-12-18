import time
import numpy as np
import re
import os
import sys
from functools import wraps
import logging

log = logging.getLogger(__name__)

try:
    import clr
    from System import Byte, Int32

    sys.path.append(os.path.dirname(__file__))
    clr.AddReference('FUTEK USB DLL')
except:
    pass


try:
    from FUTEK_USB_DLL import USB_DLL  # import the C# assembly class from FUTEK_USB_DLL namespace
except:
    pass


def retryable(times=3):
    """
    :param times: How many times function is retried
    :return:
    """
    def methodwrapper(func):
        @wraps(func)
        def retryable_func(*args, **kwargs):
            ex = None
            for i in range(times):
                try:
                    return func(*args, **kwargs)
                except ValueError as e:
                    ex = e
            raise ex
        return retryable_func
    return methodwrapper


class ForceSensor(object):

    def __init__(self, serial_number, n_averages=4, samplerate=25, flip_polarity=True):
        """ Initialize the C# Object and open try to open connection. """
        self.interface = USB_DLL()
        self.channel = 1

        # open connection
        self.open(serial_number)

        # check that connection is ok
        if self.interface.DeviceHandle == 0 or self.interface.DeviceStatus != 0:
            raise Exception("Cannot establish connection. Check provided serial number {}.".format(serial_number))

        self.lbs_to_grams = 453.59237
        self.direction = -1.0 if flip_polarity else 1.0
        self.handle = self.interface.DeviceHandle

        self.n_average = n_averages
        self.set_averaging(self.n_average)

        self.loading_vals = [0.0]*self.get_number_of_loading_points()

        self.factor = float(pow(10, (-1)*int(self.get_decimal_point())))

        #  create 1-degree polynomial fit for calibration data
        self.load_adc = []
        for i, x in enumerate(self.loading_vals):
            self.loading_vals[i] = float(self.get_load_of_loading_pont(i))*self.factor
            self.load_adc.append(float(self.get_loading_point(i)))

        self.loading_vals.append(self.get_fullscale_load()*self.factor)
        self.load_adc.append(self.get_fullscale_value())  # add adc output at full load
        self.p = np.polyfit(self.load_adc, self.loading_vals, 1)

        self.set_sampling_rate(samplerate)
        self.rate = samplerate
        self.data_stream_initialized = False

    def close(self):
        """ Closes the connection. """
        self.interface.Close_Device_Connection(self.handle)

    def open(self, serno):
        """ Opens device connection """
        self.interface.Open_Device_Connection(str(serno))

    def get_status(self):
        """ See:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#DeviceStatusCodes.html
        """
        return self.interface.DeviceStatus

    def initialize_datastream(self, timeout=15):
        """
        This function attempts to read data from Futek sensor until the data stream stabilizes. If not executed, several
        initial samples from the sensor would read 0.0 instead of the real value.
        :param timeout: Timeout for waiting.
        :return: None.
        """
        logging.info("Starting Futek sensor data stream initialization")
        start_time = time.time()
        # Read a couple of times to flush possible old data from buffer
        for _ in range(3):
            self.fast_data_request()
        while True:
            # Typical time is about 6-8 seconds.
            if time.time() - start_time > timeout:
                log.error("Failed to initialize Futek sensor data stream in {} seconds.".format(timeout))
                return
            data = self.fast_data_request()
            if len(data) != 0:
                self.data_stream_initialized = True
                log.info("Futek sensor data stream initialized successfully")
                return
            else:
                # Databuffer is 30 samples, so sleep until about half of buffer is full.
                time.sleep(1/self.rate * 15)

    @retryable()
    def get_decimal_point(self):
        """ See:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#FUTEK_USB_DLL~FUTEK_USB_DLL.USB_DLL~Get_Decimal_Point.html
        """
        return float(self.interface.Get_Decimal_Point(self.handle, self.channel))

    @retryable()
    def get_number_of_loading_points(self):
        """ See:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#FUTEK_USB_DLL~FUTEK_USB_DLL.USB_DLL~Get_Number_of_Loading_Points.html
        """
        return int(self.interface.Get_Number_of_Loading_Points(self.handle, self.channel))

    @retryable()
    def get_fullscale_value(self):
        """ See:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#FUTEK_USB_DLL~FUTEK_USB_DLL.USB_DLL~Get_Fullscale_Value.html
        """
        return float(self.interface.Get_Fullscale_Value(self.handle, self.channel))

    @retryable()
    def get_fullscale_load(self):
        """ See:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#FUTEK_USB_DLL~FUTEK_USB_DLL.USB_DLL~Get_Fullscale_Load.html
        """
        return float(self.interface.Get_Fullscale_Load(self.handle, self.channel))

    @retryable()
    def get_load_of_loading_pont(self, index):
        """ See:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#FUTEK_USB_DLL~FUTEK_USB_DLL.USB_DLL~Get_Load_of_Loading_Point.html
        """
        return float(self.interface.Get_Load_of_Loading_Point(self.handle, index, self.channel))

    @retryable()
    def get_sampling_rate_setting(self):
        """ Possible settings:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#ADCConfigurationCodes.html
        """
        return self.interface.Get_ADC_Sampling_Rate_Setting(self.handle, self.channel)

    @retryable()
    def normal_data_request(self):
        """ See:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#FUTEK_USB_DLL~FUTEK_USB_DLL.USB_DLL~Normal_Data_Request.html
        """
        if not self.data_stream_initialized:
            raise Exception("Attempting to read data without initializing sensor data stream")

        return self.interface.Normal_Data_Request(self.handle, self.channel)

    def set_adc_configuration(self, setting, channel=1):
        """ Possible settings:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#ADCConfigurationCodes.html
        """
        self.interface.Set_ADC_Configuration(self.handle, Byte(setting), Byte(channel))

    @retryable()
    def get_unit_code(self, channel=1):
        """ Codes:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#UnitCodes.html
        """
        self.interface.Get_Unit_Code(self.handle, Byte(channel))

    @retryable()
    def get_loading_point(self, point, channel=1, type_of_cal=0):
        """ See:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#FUTEK_USB_DLL~FUTEK_USB_DLL.USB_DLL~Get_Loading_Point.html
        """
        return self.interface.Get_Loading_Point(self.handle, point, channel, type_of_cal)

    def set_averaging(self, n_samples):
        """ See:
            https://www.futek.com/files/docs/API/FUTEK_USB_DLL/webframe.html#FUTEK_USB_DLL~FUTEK_USB_DLL.USB_DLL~Set_Average_Setting.html
        """
        return self.interface.Set_Average_Setting(self.handle, n_samples, self.channel)

    def set_sampling_rate(self, rate):

        rates = {5: 0, 10: 1, 15: 2, 20: 3, 25: 4, 30: 5, 50: 6, 60: 7, 100: 8, 300: 9}
        try:
            self.set_adc_configuration(rates[rate])

        except KeyError:
            print("Unsupported sampling rate", rate, "Hz. Current sampling rate set to", \
                rates.keys()[rates.values().index(int(self.get_sampling_rate_setting()))])

    def fast_data_request(self):
        fw = self.interface.Get_Firmware_Version(self.handle)
        channel = 0
        samplerate = "10"
        boardtype = "1"
        devicenum = 1
        retstring = self.interface.Fast_Data_Request(self.handle, 0, devicenum, boardtype, samplerate, fw, channel)
 
        # retstring is a collection of results in following format 0,14,13214336,,,,Tuesday, October 18,2011,2:29:27 PM,
        # 1,14,13214336,,,,Tuesday, October 18,2011,2:29:27 PM,2,14,13214336,,,,Tuesday, October 18,2011,2:29:27 PM,.
        # Date and time formats might be different depending on computer settings.
        # We need to collect third values from results (13214336 in the example).
        # The 4th value in results seems to always be empty so we can use that to locate the value we need.

        values = []
        if retstring is not None:
            retstring_separated = retstring.split(',')
            
            for counter in range(len(retstring_separated) - 1):
                if retstring_separated[counter] == '' and retstring_separated[counter - 1] != '':
                    value = self.adc_to_gf(float(retstring_separated[counter - 1]))
                    values.append(value)

        return values

    def adc_to_gf(self, adc_val):
        return np.polyval(self.p, float(adc_val)) * self.lbs_to_grams * self.direction

    def get_gramforce(self):
        val = self.normal_data_request()
        if val != "Error":
            return self.adc_to_gf(val)
        return None


class ForceSensorStub:
    """
    Stub sensor which returns 0 when force is queried
    """
    def __init__(self):
        n = 10
        self.stub_values = []
        self.stub_values.extend([0] * 50) # taring
        # get calibratons
        self.stub_values.extend([56] * n)
        self.stub_values.extend([130] * n)
        self.stub_values.extend([186] * n)
        self.stub_values.extend([243] * n)
        self.stub_values.extend([298] * n)
        # test calibrations
        self.stub_values.extend([40] * n)
        self.stub_values.extend([80] * n)
        self.stub_values.extend([120] * n)
        self.stub_values.extend([160] * n)
        self.stub_values.extend([200] * n)

    def get_gramforce(self):
        return self.stub_values.pop(0)

    def initialize_datastream(self):
        pass


def main():
    """ Simple test. """

    sensor = ForceSensor(732644, samplerate=100)

    # Initialize the datastream
    sensor.initialize_datastream()
    offset = np.mean(np.array(sensor.fast_data_request()))
    values = []
    n = 0
    while True:

        try:
            value = sensor.get_gramforce()
            n += 1
            if value:
                print(n, value - offset)
                values.append(value)
            time.sleep(0.01)
        except KeyboardInterrupt:
            break

    print(sensor.close())  # close connection to the device


if __name__ == "__main__":
    main()

