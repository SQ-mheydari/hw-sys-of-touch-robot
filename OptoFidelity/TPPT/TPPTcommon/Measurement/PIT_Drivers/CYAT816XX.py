import time
from fpga_driver import *

class device_driver:
    """Driver for Cypress CYAT816XX controllers"""

    scr = {"user":"MJU", "ver":"1.20", "date":"2020-05-15"}

    signalReference = []
    signalUntouched = []
    signalUntouchedExist = False
    signalTouched = []
    signalStrength = []
    signalNoise = []
    signalSNR = []

    signalUntouchedMaxArray = []
    signalUntouchedMax = 0
    signalTouchedMaxArray = []
    signalTouchedMax = 0

    LastTimeStamp = 0

    def __init__(self, fpga):
        self.fpga = fpga
        self.fpga.i2c_setspeed(400)
        self.fpga.i2c_interruptMode(1) # Set edge detect
        self.delay_old = 0

    def FindAddress(self):
        tempaddress = []
        for i in range(0, 127):
            try:
                self.fpga.i2c_read(i+1, 1)
                tempaddress.append(i+1)
            except:
                pass

        return tempaddress

    def Initialize(self):
        """ This called from upper level to initialize panel
        """
        # Power off first
        self.fpga.send_pit2_cmd("set_power 0")
        time.sleep(0.5)
        # Power on
        self.fpga.send_pit2_cmd("set_dutvoltage IO 3.3")
        self.fpga.send_pit2_cmd("set_dutvoltage PANEL 4.8")
        self.fpga.send_pit2_cmd("set_power 1")
        self.fpga.send_pit2_cmd("set_dutpower 1 1")

        self.address = 0x24
        self.fpga.read_ext_rise_fall([0, 1, 1, 1, 1, 1, 1, 1])
        time.sleep(2)
        #Workaround before it is clear how it is possible to know if program in bootloader
        try:
            ret = self.InitializePanel()
        except:
            ret = self.InitializePanel()
        return ret

    def InitializePanel(self):
        """ Initialize panel
        """
        self.SynchronousHandshaingEnabled = False
        self.HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1).data()[0]
        if self.HST_MODE & 0b00000001 == 0b00000001:
            #Exit Bootloader
            self.fpga.i2c_write(self.address,
                                [0x00, 0xFF, 0x01, 0x3B, 0x00, 0x00, 0x4F, 0x6D, 0x17])
            self.fpga.i2c_read(self.address, 1, timeout=2000, wait_for_interrupt=True)
            time.sleep(2)
        #Go to System information mode
        self.SetInformationMode()

        #Read register offset informations
        OPCFG_OFS_Temp = self.fpga.i2c_write_read(self.address, [0x0A], 2, reg_add_size=1).data()
        OPCFG_OFS = OPCFG_OFS_Temp[0] * 0x100 + OPCFG_OFS_Temp[1]
        Offsets = self.fpga.i2c_write_read(self.address, [OPCFG_OFS], 9, reg_add_size=1).data()

        self.CMD_OFS = Offsets[0]
        self.REP_OFS = Offsets[1]
        self.REP_SZH = Offsets[2]
        self.REP_SZL = Offsets[3]
        self.NUM_BTNS = Offsets[4]
        self.TT_STAT_OFS = Offsets[5]
        self.TCH_REC_SIZ = Offsets[8]

        #Read number of nodes
        PCFG_OFS_Temp = self.fpga.i2c_write_read(self.address, [0x08], 2, reg_add_size=1).data()
        PCFG_OFS = PCFG_OFS_Temp[0] * 0x100 + PCFG_OFS_Temp[1]
        Offsets = self.fpga.i2c_write_read(self.address, [PCFG_OFS], 10, reg_add_size=1).data()
        self.Nodes = [Offsets[0], Offsets[1]]
        RES_XH = Offsets[6] & 0x7f
        RES_XL = Offsets[7]
        RES_YH = Offsets[8] & 0x7f
        RES_YL = Offsets[9]

        xres = (RES_XH << 8) | RES_XL
        yres = (RES_YH << 8) | RES_YL

        #Go to Operation mode
        self.SetOperationMode()

        return ['OK', [xres, yres, RES_XH, RES_XL, RES_YH, RES_YL]]

    def SetOperationMode(self):
        """ Go to Operation mode
        """
        self.HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1).data()[0]
        if self.HST_MODE & 0b01110000 != 0b00000000:
            self.HST_MODE = (((self.HST_MODE ^ 0x80) & 0x80) + 0x08)
            self.fpga.i2c_write_read(self.address, [0x00, self.HST_MODE], 1, reg_add_size=2)

    def SetInformationMode(self):
        """ Go to System information mode
        """
        self.HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1).data()[0]
        if self.HST_MODE & 0b01110000 != 0b00010000:
            self.HST_MODE = (((self.HST_MODE ^ 0x80) & 0x80) + 0x18)
            self.fpga.i2c_write_read(self.address, [0x00, self.HST_MODE], 1, reg_add_size=2)
            time.sleep(2)

    def SetConfigurationMode(self):
        """ Go to System configurations mode
        """
        self.HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1).data()[0]
        if self.HST_MODE & 0b01110000 != 0b00100000:
            self.HST_MODE = (((self.HST_MODE ^ 0x80) & 0x80) + 0x28)
            self.fpga.i2c_write_read(self.address, [0x00, self.HST_MODE], 1, reg_add_size=2)
            time.sleep(2)

    def toggleDataBit(self):
        if self.SynchronousHandshaingEnabled:
            self.HST_MODE = self.HST_MODE ^ 0x80
            self.fpga.i2c_write(self.address, [0x00, self.HST_MODE])

    def Multiplexer(self, port):
        """ Set i2c port
        """
        self.fpga.i2c_set_port(port)
        return [port]

    def ReturnTimestamps(self):
        """ Return interrupt timestamps
        """
        return self.fpga.read_timestamps()

    def FlushBuffers(self):
        """ Flush event buffer
        """
        self.fpga.flush_event_fifos()
        return 'OK'

    def ClearBuffer(self):
        """ Empty buffer by reading all data
        """
        # empty buffer
        while True:
            try:
                # dummy read
                self.fpga.i2c_write_read(self.address, [self.TT_STAT_OFS], 1, timeout=5,
                                            wait_for_interrupt=True,
                                            reg_add_size=1).data()[0] & 0b00011111
                self.toggleDataBit()
            except:
                break
        return 'OK'

    def ReturnFingerIntsTimestamp(self, timeout=0):
        """ Read interrupts
        """
        return self.fpga.read_ints(timeout=timeout).timestamp()

    def SingleTrigger(self):
        """ Set single strigger mode.
        """
        self.fpga.set_trigger([False, True, True, True])
        return 0

    def NormalTrigger(self):
        """ Set single strigger mode.
        """
        self.fpga.set_trigger([True, True, True, True])
        return 0

    def ReturnFingerDelay(self, timeout=8000):
        timeStamps = {'0':0, '1':0}
        self.fpga.read_ext_rise_fall([0, 1, 1, 1, 1, 1, 1, 1])

        while (timeStamps['0'] == 0 or timeStamps['1'] == 0):
            event = self.fpga.read_ints(timeout=timeout)
            if event.data()[0] == 0 and timeStamps['0'] == 0:
                timeStamps['0'] = event.timestamp()

            if event.data()[0] == 1 and timeStamps['1'] == 0:
                timeStamps['1'] = event.timestamp()

        return [(timeStamps['0'] - timeStamps['1'])/1000.0]

    def ReturnP2PArray(self, timeout=5000, waitForFingerInterrupt=True):
        """ Return P2P array
        """
        self.fpga.flush_event_fifos()
        # togle bit
        HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1).data()[0]

        # empty buffer
        self.ClearBuffer()

        CollectTuples = []

        # Wait touch interrupt
        touchEvent = self.fpga.i2c_write_read(self.address, [self.TT_STAT_OFS], 1, timeout=timeout,
                                              wait_for_interrupt=True, reg_add_size=1)
        NumberOfTouches = touchEvent.data()[0] & 0b00011111
        touchTimestamp = touchEvent.timestamp() / 1000

        # Wait finger interrupt if set.
        if waitForFingerInterrupt:
            fingerTimestamp = self.fpga.read_ints(timeout=timeout).timestamp()/1000

        for i in range(NumberOfTouches):
            data = self.fpga.i2c_write_read(self.address, [self.TT_STAT_OFS+1+i*self.TCH_REC_SIZ],
                                            self.TCH_REC_SIZ, reg_add_size=1).data()
            Xcoord = data[0] * 0x100 + data[1]
            Ycoord = data[2] * 0x100 + data[3]
            Zcoord = data[4]
            FingerID = data[5]&0b00011111
            CollectTuples.append((Xcoord, Ycoord, Zcoord, FingerID, fingerTimestamp, touchTimestamp,
                                  waitForFingerInterrupt))

        #Check if report is valid
        REP_STAT = self.fpga.i2c_write_read(self.address, [self.REP_OFS+1], 1,
                                            reg_add_size=1).data()[0]
        Invalid = REP_STAT & 0b00100000
        Bootloader = REP_STAT & 0b00000001

        # togle bit
        self.toggleDataBit()

        if NumberOfTouches == 0:
            CollectTuples.append((0, 0, 0, 0, 0, 0))
            CollectTuples.append("No fingers")  # note
        elif Bootloader != 0:
            #CollectTuples.append('Bootloader') # note
            raise Exception('Bootloader running', REP_STAT)
        elif Invalid != 0:
            CollectTuples.append('Invalid') # note
        else:
            CollectTuples.append('OK') # note

        #CollectTuples.append(str(REP_STAT) + "," + str(HST_MODE))   # Log
        return CollectTuples

    def InitCLine(self, timeout=8000, fingerTimeout=1000, waitForFingerInterrupt=False):
        """ Initialize cline function
        """
        self.fpga.resetPanelInt()
        self.fpga.flush_event_fifos()
        self.ClearBuffer()
        self.CLineWaitFingerInterrupt = waitForFingerInterrupt
        self.ClineWaitFingerTimeout = fingerTimeout
        self.ClineTimeout = timeout/1000
        self.ClineStarttime = time.time()
        return 'OK'

    def IsTouchDataAvailable(self):
        """ This is polled from LV code
        """
        state = self.fpga.panel_int()
        if self.ClineTimeout + self.ClineStarttime < time.time():
            state = "Timeout"
        if state:
            self.ClineStarttime = time.time()
        return state

    def ReturnCLineArray(self, timeout=8000, waitForTouchInterrupt=False):
        """ Return continuous line arrays
        """
        CollectTuples = []

        # Read touch event
        touchEvent = self.fpga.i2c_write_read(self.address, [self.TT_STAT_OFS], 1,
                                              timeout=timeout,
                                              wait_for_interrupt=waitForTouchInterrupt,
                                              reg_add_size=1)

        NumberOfTouches = touchEvent.data()[0] & 0b00011111
        touchTimestamp = touchEvent.timestamp() / 1000

        # Get finger interrupt if CLineWaitFingerInterrupt is true.
        if self.CLineWaitFingerInterrupt:
            fingerTimestamp = self.fpga.read_ints(timeout=self.ClineWaitFingerTimeout).timestamp()/1000
            # Wait only once.
            self.CLineWaitFingerInterrupt = False
        else:
            fingerTimestamp = 0

        for i in range(NumberOfTouches):
            data = self.fpga.i2c_write_read(self.address, [self.TT_STAT_OFS+1+i*self.TCH_REC_SIZ],
                                            self.TCH_REC_SIZ, reg_add_size=1).data()
            Xcoord = data[0] * 0x100 + data[1]
            Ycoord = data[2] * 0x100 + data[3]
            Zcoord = data[4]
            FingerID = data[5] & 0b00011111
            Event = data[5] & 0b11100000
            CollectTuples.append((Xcoord, Ycoord, Zcoord, FingerID, fingerTimestamp, touchTimestamp, Event))

        # Check if report is valid
        REP_STAT = self.fpga.i2c_write_read(self.address, [self.REP_OFS+1], 1,
                                            reg_add_size=1).data()[0]
        Invalid = REP_STAT & 0b00100000
        Bootloader = REP_STAT & 0b00000001

        # Togle data bit
        #self.toggleDataBit()

        if NumberOfTouches == 0:
            CollectTuples.append((0, 0, 0, 0, 0, 0))
            CollectTuples.append("No fingers")  # note
        elif Bootloader != 0:
            #CollectTuples.append('Bootloader') # note
            raise Exception('Bootloader running', REP_STAT)
        elif Invalid != 0:
            CollectTuples.append('Invalid') # note
        else:
            CollectTuples.append('OK') # note

        CollectTuples.append(str(REP_STAT) + ",") # + str(HST_MODE))   # Log
        return CollectTuples

    def Reset(self):
        """ Send reset to controller
        """
        self.HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1).data()[0]
        self.HST_MODE = (((HST_MODE ^ 0x80) & 0x80) + 0x09)
        self.fpga.i2c_write_read(self.address, [0x00, self.HST_MODE], 1)

        return self.HST_MODE

    def Base(self):
        # CAT mode
        HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1)[0]
        HST_MODE = (((HST_MODE ^ 0x80) & 0x80) + 0x28)
        self.fpga.i2c_write_read(self.address, [0x00, HST_MODE], 1)

        time.sleep(3)
        HST_MODE = self.fpga.write_then_read(self.address, [0x00], 1, reg_add_size=1)[0]
        time.sleep(1)
        self.fpga.write(self.address, [0x00, 0xA0, 0X00, 0X0A, 0X0F])

        time.sleep(3)
        HST_MODE = self.fpga.write_then_read(self.address, [0x00], 1)[0]

        self.fpga.write(self.address, [0X00, 0x20, 0x00, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x00])
        time.sleep(3)
        self.fpga.write(self.address, [0X00, 0xA0, 0x00, 0x0C, 0x00, 0x00, 0x00, 0xB0, 0x01])

        time.sleep(3)
        Data = self.fpga.read(self.address, 100, timeout=2000, wait_for_interrupt=False)

#        time.sleep(3)
#        HST_MODE = self.fpga.write_then_read(self.address,
#                                             [0x00, 0x20, 0x00, 0x0C,
#                                              0x00, 0x00, 0x00, 0x10, 0x09],1)[0]

        return [HST_MODE, Data]

    def ReadCAT(self):
        # CAT mode
        HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1).data()[0]
        HST_MODE = (((HST_MODE ^ 0x80) & 0x80) + 0x28)
        self.fpga.i2c_write_read(self.address, [0x00, HST_MODE], 1, reg_add_size=2)
        HST_MODE = (((HST_MODE ^ 0x80) & 0x80) + 0x20)
        time.sleep(1)
        id = 0
        Data = []
        Datas = []

        # Get Config Row Size
        self.fpga.i2c_write(self.address, [0x00] + [HST_MODE] + [0x00, 0x02, 0x00, 0x00,
                                                                 0x00, 0x00, 0x00])
        time.sleep(1)
        Len = self.fpga.i2c_read(self.address, 128, timeout=2000, wait_for_interrupt=False).data()

        id = 0x197 / int(Len[4])
        time.sleep(1)

        for i in range(id):
            HST_MODE = (((HST_MODE ^ 0x80) & 0x80) + 0x20)
            #self.fpga.write(self.address,[0x00, 0xA0, 0x00, 0x03, 0x00] +
            #                              [i] + [0x00] + [Len[4]] + [0x00])
            self.fpga.i2c_write(self.address, [0x00] + [HST_MODE] +
                                [0x00, 0x03, 0x00, 0x00, 0x00] + [Len[4]] + [i])
            time.sleep(1)
            Data = self.fpga.i2c_read(self.address, Len[4], timeout=2000,
                                      wait_for_interrupt=False).data()
            time.sleep(1)
            Datas.append(Data)
        return [[id], Len, Datas]

    def PanelScan(self, GetBase=False):
        """if GetBase == True:
            # CAT mode
            HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1).data()[0]
            HST_MODE = (((HST_MODE ^ 0x80) & 0x80) + 0x28)
            self.fpga.i2c_write_read(self.address, [0x00, HST_MODE], 1)

            time.sleep(1)
            #Data = self.fpga.read(self.address,100,timeout=2000, wait_for_interrupt = False)
            #time.sleep(1)

            # init all base lines (0x0F)
            self.fpga.i2c_write(self.address, [0x00, 0xA0, 0X00, 0X0A, 0x0F])
            Data = self.fpga.i2c_read(self.address, 4, timeout=2000, wait_for_interrupt=True)
            while Data[2] & 0x40 != 0x40:
                Data = self.fpga.i2c_read(self.address, 4, timeout=2000, wait_for_interrupt=False)
        """
        self.SetConfigurationMode()

        # execute full panel scan
        self.fpga.i2c_write(self.address, [0x02, 0x0B])
        Data_exe = self.fpga.i2c_read(self.address, 1, timeout=2000, wait_for_interrupt=False).data()
        #while Data[2] & 0x40 != 0x40:
        #    Data = self.fpga.i2c_read(self.address, 4, timeout=2000,
        #                              wait_for_interrupt=False).data()
        time.sleep(1)
        # retrieve data
        Len = self.Nodes[0] * self.Nodes[1] + 8
        self.fpga.i2c_write(self.address, [0x02, 0x0C, 0x00, 0x00] +
                            [(Len >> 8) & 0xff, Len & 0xff] + [0x00])
        Data = self.fpga.i2c_read(self.address, Len, timeout=2000, wait_for_interrupt=False).data()

        # remove header
        #Data = Data[8:]

        #return [HST_MODE, Len, Data]
        return [Data_exe, Data]
        #return Len

    def HST_MODE(self):
        HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1).data()
        return HST_MODE

    def SysInfo(self):
        #Go to System information mode
        HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1, reg_add_size=1).data()[0]
        if HST_MODE & 0b01110000 != 0b00010000:
            HST_MODE = (((HST_MODE ^ 0x80) & 0x80) + 0x18)
            self.fpga.i2c_write_read(self.address, [0x00, HST_MODE], 1, reg_add_size=1)
            time.sleep(1)
        #Read register offset informations
        OPCFG_OFS_Temp = self.fpga.i2c_write_read(self.address, [0x0A], 2, reg_add_size=1).data()
        OPCFG_OFS = OPCFG_OFS_Temp[0] * 0x100 + OPCFG_OFS_Temp[1]
        Offsets = self.fpga.i2c_write_read(self.address, [OPCFG_OFS], 9, reg_add_size=1).data()
        self.CMD_OFS = Offsets[0]
        self.REP_OFS = Offsets[1]
        self.REP_SZH = Offsets[2]
        self.REP_SZL = Offsets[3]
        self.NUM_BTNS = Offsets[4]
        self.TT_STAT_OFS = Offsets[5]
        self.TCH_REC_SIZ = Offsets[8]

        PCFG_OFS_Temp = self.fpga.i2c_write_read(self.address, [0x08], 2, reg_add_size=1).data()
        PCFG_OFS = PCFG_OFS_Temp[0] * 0x100 + PCFG_OFS_Temp[1]
        Offsets = self.fpga.i2c_write_read(self.address, [PCFG_OFS], 2, reg_add_size=1).data()
        self.Nodes = [Offsets[0], Offsets[1]]

        return [OPCFG_OFS, PCFG_OFS, self.Nodes]

    def WriteSleepMode(self, SleepMode):
        #Read Current SleepMode and toggle bit
        HST_MODE = self.fpga.i2c_write_read(self.address, [0x00], 1,
                                            reg_add_size=1).data()[0] ^ 0x80
        # Active mode
        if SleepMode == 1:
            # Switch to Free Running mode
            HST_MODE = (HST_MODE & 0b11110001)
        # Doze mode
        if SleepMode == 2:
            # Switch to Auto Switchin mode with Wake-on-Touch
            HST_MODE = (HST_MODE & 0b11110001) + 0b00000100
        # Deep Sleep
        if SleepMode == 3:
            # Switch to Deep Sleep mode
            HST_MODE = (HST_MODE & 0b11110001) + 0b00000010
        self.fpga.i2c_write(self.address, [0x00, HST_MODE])
        self.fpga.i2c_write_read(self.address, [0x00], 1,
                                 reg_add_size=1).data()[0] ^ 0x80

        return [HST_MODE]

    #
    # Returns basic info
    #
    def ReadFWVersion(self):
        status = []

        self.fpga.i2c_write(self.address, [0x00, 0x10]) # Switch to System Information mode
        time.sleep(0.1)

        rev = self.fpga.i2c_write_read(self.address, [0x00], 32).data() # Read system info registers

        fw = "%d.%d build:%d" % (rev[0x11] >> 4 & 0x0F, rev[0x11] & 0x0F, rev[0x12])
        status.append((0, 0, 0, 0, 0, 0))
        status.append("Panel: " + fw + ", Script: " + self.scr['ver'] + ", User: " +
                      self.scr['user'] + ", Date: " + self.scr['date'] + ", fpga:" + self.fpga.FPGA_version()[0])
        status.append("")

        self.fpga.i2c_write(self.address, [0x00, 0x00]) # Switch to Normal mode
        time.sleep(0.1)

        return status

    def ReturnInterruptStates(self):
        state = []
        state = self.fpga.read_interrupt_state()
        return state
