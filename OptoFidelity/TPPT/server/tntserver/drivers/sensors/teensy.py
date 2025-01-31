import serial
import numpy as np
import time
import array



class Teensy:
    def __init__(self, simulator = False):
        self._serial = None
        self._spring_constant = None
        self._simulated = simulator


    def set_spring_constant(self, v):
        self._spring_constant = v



    def open(self, port: str):
        if not self._simulated:
            self._serial = serial.Serial(port=port, baudrate=1000000, bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE, timeout=0.05)
            self._serial.close()
            self._serial.open()

    def begin(self):
        if not self._simulated:
            #___serial.write(b'd')  # interrupt signal disabled
            self._serial.write(b'r')
            self._serial.write(b't')
            #print("Taring teensy, waiting for 2 seconds.")
            #time.sleep(2)
            self._serial.write(b'c')


#def end():
#    ___serial.write(b'q')


    def read(self):

        if self._simulated:
            return [], []

        #spring_constant = 30500.0
        spring_constant = self._spring_constant
        if spring_constant is None:
            raise "spring constant is None"

        self._serial.write(b's')
        retstr = self._serial.readline()

        print("Status reply:", retstr)
        success = 0

        total_time = 0
        total_data = 0

        enc_data = []

        self._serial.write(b'p')
        time.sleep(0.05)
        datastr = []
        start_time = time.time()
        ii = 0
        while self._serial.in_waiting:
            read_bytes = array.array('B', self._serial.read(15000))
            datastr += list(read_bytes)

            ii += 1

        t_time = time.time() - start_time
        total_data += len(datastr)
        N_buff = datastr[0] * 256 + datastr[1]
        datastr = datastr[2:]  # remove sample number
        crc = datastr[-2] * 256 + datastr[-1]
        datastr = datastr[:-2]  # remove crc

        print("Loops:{}, total {}, transfer time:{:2.2f}".format(ii, len(datastr), t_time))

        data = datastr
        rgb = [[float(data[i] * 256 + data[i + 1]),
                float(data[i + 2] * 256 + data[i + 3]),
                float(data[i + 4] * 256 + data[i + 5])] for i in range(0, len(data), 8)]

        enc_pulses = np.array([float(data[i] * 256 + data[i + 1]) for i in range(6, len(data), 8)])


        # check for counter overflow
        rev_counter = 0
        for ii in range(0, len(enc_pulses)):
            value = enc_pulses[ii]

            # to 16-bit signed int
            value = ((int(value) + 0x8000) & 0xffff) - 0x8000

            # to grams
            value = -value * spring_constant / 1000000.0
            enc_data.append(value)

        crc_calc = int(0)
        for rgb_val, e in zip(rgb, enc_pulses):
            crc_calc ^= int(rgb_val[0])
            crc_calc ^= int(rgb_val[1])
            crc_calc ^= int(rgb_val[2])
            crc_calc ^= int(e)

        if crc_calc == int(crc):
            print("Checksum OK!")
            success += 1
        else:
            print("Invalid checksum")

        total_time += t_time

        return enc_data, rgb
