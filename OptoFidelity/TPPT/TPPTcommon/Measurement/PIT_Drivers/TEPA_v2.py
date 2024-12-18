import time

class device_driver(object):
    """ The main class that gets instantiated by the PIT firmware 
    """
    scr = {"user":"MJU", "ver":"1.00", "date":"2020-03-30"}

    def __init__(self, fpga):
        self.fpga = fpga
        self.counter = 10
        self.paddress = 0x4B
        self.fpga.i2c_interruptMode(0) # Level mode

    def Multiplexer(self, port):
        self.fpga.i2c_set_port(port)
        return [port]

    def Initialize(self):
        # Set power off
        self.fpga.send_pit2_cmd("set_power 0")
        time.sleep(0.5)
        # Set panel voltages
        self.fpga.send_pit2_cmd("set_dutvoltage IO 3.3")
        self.fpga.send_pit2_cmd("set_dutvoltage PANEL 3.3")
        self.fpga.send_pit2_cmd("set_power 1")
        self.fpga.send_pit2_cmd("set_dutpower 1 1")
        # Wait panel boot up
        time.sleep(1)

        self.device = maXTouch(self.fpga, 400)
        self.paddress = self.device.address
        config = self.device.config()
        xres = (config[19] << 8) | config[18]
        yres = (config[21] << 8) | config[20]

        self.fpga.read_ext_rise_fall([0,0,1,1,1,1,1,1])
        #self.fpga.read_ext_rise_fall([0,1,1,1,1,1,1,1])

        return ['OK', [xres, yres, 0, 0, 0, 0]]

    def Configure(self):
        return str(self.device.config())

    def FlushBuffers(self):
        self.fpga.flush_event_fifos()
        return 'OK'
        
    def ReadInts(self):
        return self.fpga.read_ints(timeout=2000)

    def ReturnP2PArray(self, index = 0, waitForFingerInterrupt = True):
        self.fpga.flush_event_fifos()
        self.ClearBuffer()
        p2p, pos_array = self.device.read_messages(3, 0, True, 5000)
        return p2p + ['OK', pos_array]
    
    def InitCLine(self, timeout=8000, fingerTimeout=1000, waitForFingerInterrupt=False):
        """ Initialize cline function
        """
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
        self.fpga.resetPanelInt()
        if self.ClineTimeout + self.ClineStarttime < time.time():
            state = "Timeout"
        if state:
            self.ClineStarttime = time.time()
        return state
    
    def ReturnCLineArray(self):
        """ This function will be called by the PIT firmware when
            touch data is available.
        """
        cline, pos_array = self.device.read_messages(0, 0, self.CLineWaitFingerInterrupt, self.ClineWaitFingerTimeout)
        # Wait finger interrupt only once.
        self.CLineWaitFingerInterrupt = False
        return cline + ['OK', pos_array]

    def WriteSleepMode(self, sleepMode):
        if sleepMode == 1:
            self.device.set_sleep_mode([255,255])
        if sleepMode == 2:
            self.device.set_sleep_mode([20,7])
        if sleepMode == 3:
            self.device.set_sleep_mode([0,0])
        self.device.flush_messages()

        status = []
        status.append((0,0,0,0,0,0))
        status.append("OK")
        status.append("")

        return status

    def ReadFWVersion(self):
        """ Return chip fw and this script versions. Also date created and user name """
        status = []
        fw = "X.X build:X.X"
        status.append((0,0,0,0,0,0))
        status.append("Panel: " + fw + ", Script: " + self.scr['ver'] + ", User: " + self.scr['user'] + ", Date: " + self.scr['date'])
        status.append("")
        return status

    def ReturnInterruptStates(self):
        state = []
        state = self.fpga.read_interrupt_state()
        return state

    def ReturnTimestamps(self):
        timestamps = self.fpga.read_timestamps()
        timestamps = [x /1000 for x in timestamps]
        return timestamps + [timestamps[1]-timestamps[2]]

    def ReturnPosArray(self):
        pos_array = self.fpga.read_pos_array()
        return pos_array

    def SingleTrigger(self):
        self.fpga.set_trigger([False,True,True,True])
        return 0

    def NormalTrigger(self):
        self.fpga.set_trigger([True,True,True,True])
        return 0

    def ClearBuffer(self):
        self.device.flush_messages()

    def ReturnReportIDRange(self, table_number):
        return self.device.object_table[table_number].report_id_table_range()

    def read_data(self, address, size):
        data = self.fpga.i2c.write_then_read(self.paddress, _lsb_msb(address), size, 100, False)
        #Convert int values 0-255 to two character hexacode values
        data = [ '{:02x}'.format(value) for value in data ]
        #Combine all values to one string
        return_string = ''.join(data)
        return return_string


    def write_data(self, address, dataIn):
        """ Data is assumed to be one string containing all the hex codes. No space between hex codes.
        """
        data = []
        for i in xrange(0, len(dataIn), 2):
            #change hexadecimal values to int
            value = int('0x' + dataIn[i:i+2], 16)
            data.append( value )

        data_left = len(data)
        write_amount = 0
        #max_count = What is maximum amount of bytes that can be writen (normally 16) - address size (usually 2)
        max_count = 14 
        current_addr = address
        start_addr = current_addr

        #Write maximum 16 bytes at the time starting from address that is given in data
        i = 0
        while (data_left > 0):
            # Set address where reading is done
            begin = i*max_count
            current_addr = start_addr + begin

            if (data_left <= max_count):
                write_amount = data_left
                data_left = 0
            else:
                write_amount = max_count
                data_left = data_left - write_amount
            end = begin + write_amount

            self.fpga.i2c_write(self.paddress, _lsb_msb(current_addr) + data[begin:end], 100, False)       
            i += 1
        return 'OK'

class maXTouch(object):
    """ Class to implement maXTouch -specific functionality
    """
    def __init__(self, i2c, speed):

        self.fpga = i2c
        self.fpga.i2c_setspeed(speed)
        self.address = 0x4A # Default I2C address for Atmel

        # Lets find device address
        for addr in range(0x40,0x7F):
            try:
                self.fpga.i2c_read(addr, 1)
                break
            except:
                time.sleep(0.001)
        self.address = addr
    
        #print "Addr:",addr
        
        # First, read the information block
        self.info_block = self.fpga.i2c_write_read(self.address, _lsb_msb(0), 6, 100, False).data()

        # Read rest of the information block, based on the number of elements in the Object Table
        self.info_block += self.fpga.i2c_write_read(self.address, _lsb_msb(6), self.info_block[5]*6+3, 100, False).data()

        # TODO: implement checksum verification here

        # Walk the Object Element Table, and create corresponding objects to the object table
        self.object_table = TObjectTable()
        for i in range( self.info_block[5] ):
            begin = 7 + i*6
            end = begin + 6
            tobj_data = self.info_block[begin:end]
            # Try to instantiate a specific class defined for this type of object
            # from TObjectClass -class
            # Class naming is e.g. "T5Object", "T42Object", etc.
            try:
                tobj = getattr(TObjectClasses, 'T%dObject' % tobj_data[0])(tobj_data, self.object_table.report_id_count())
            except AttributeError:
                # If no specific class was found, use a generic one
                tobj = TObjectBase(tobj_data, self.object_table.report_id_count())
            tobj.configure( self.fpga.i2c_write_read(self.address, tobj.i2c_addr(), tobj.size(), 100, False).data() )
            self.object_table.add( tobj )

        t5 = self.object_table[5]
        self.fpga.set_msgcfg(t5.i2c_addr(),t5.size())
        
    def config(self):
        t9 = self.object_table[9]
        t9.conf_table[0] = 0x8f    # report PRESS, RELEASE and MOVE
        t9.conf_table[9] = 0b00000010 #InvertY, InvertX, Switch X<->Y
        X_resolution = 4095
        Y_resolution = 4095
        #t9.conf_table[11] = 0x00    #Disable movement hysteresis initial
        #t9.conf_table[12] = 0x00     #Disable movement hysteresis next
        #t9.conf_table[12] = 0x80     #Disable move filter
        t9.conf_table[19] = (X_resolution & 0xFF00) >> 8 #X MSB
        t9.conf_table[18] = (X_resolution & 0x00FF)      #X LSB
        t9.conf_table[21] = (Y_resolution & 0xFF00) >> 8 #Y MSB
        t9.conf_table[20] = (Y_resolution & 0x00FF)      #Y LSB
        #Clipping
        clipping_parameter = 15
        t9.conf_table[22] = clipping_parameter
        t9.conf_table[23] = clipping_parameter
        t9.conf_table[24] = clipping_parameter
        t9.conf_table[25] = clipping_parameter

        self.fpga.i2c_write(self.address, t9.i2c_addr() + t9.conf_table)
        return t9.conf_table

    def set_sleep_mode(self, params):
        t7 = self.object_table[7]
        t7.conf_table[0] = params[0]
        t7.conf_table[1] = params[1]
        # This is commented out, because it doesn't work correctly.
        # Power mode setting needs to be checked from the Atmel programming spec.
        #self.fpga.i2c_write(self.address, t7.i2c_addr()+ t7.conf_table)

    def flush_messages(self):
        """ flush the command processor object from pending messages.
        """
        try:
            self.read_messages(0, 0, False, 0)
        except:
            pass

    def read_messages(self, wait_time=1, timeout=0, wait_finger_interrupt=False, wait_finger_timeout=1000):
        """ read and process all messages after trigger occurs, until timeout occurs
        """
        # if wait time is defined, wait for trigger
        wait_for_int = ( wait_time > 0 )
        response = []
        t5 = self.object_table[5]
        msg_size = t5.size()
        t44 = self.object_table[44]
        
        # read the number of pending messages from message count object T44, and store timestamp of the trigger
        readevent = self.fpga.i2c_write_read(self.address, t44.i2c_addr(), t44.size(), wait_time*1000, wait_for_int)
        msg_count = readevent.data()[0]
        pos_array = readevent.positions()
        timestamp = readevent.timestamp() / 1000

        if wait_finger_interrupt:
            fingerTimestamp = self.fpga.read_ints(timeout=wait_finger_timeout).timestamp()/1000
        else: 
            fingerTimestamp = 0
        start_time = timestamp

        try:
        
            while True:

                # check, if we should exit due to timeout
                if timestamp - start_time > timeout * 1000:
                    break
                                
                # read all the pending messages from command processor object T5
                data = self.fpga.i2c_write_read(self.address, t5.i2c_addr(), msg_count * msg_size, 100, True).data()
                    
                # pass the retrieved messages to the appropriate object handlers
                for i in range(msg_count):
                    try:
                        proc_msg = list(self.object_table.handle_report( data[i*msg_size:i*msg_size+msg_size] ))
                        response.append(proc_msg[:4] + [fingerTimestamp, timestamp, proc_msg[-1]])
                        #if proc_msg != None:
                            #response.append( proc_msg + (8, msg_count ))
                    except:
                        pass

                # read the number of pending messages from message count object T44
                readevent = self.fpga.i2c_write_read(self.address, t44.i2c_addr(), t44.size(), 100, wait_for_int)
                msg_count = readevent.data()[0]
                timestamp = readevent.timestamp() / 1000 #self.fpga.read_timestamps()[0] / 1000

        except: # FPGAError:
            # if we did not receive any messages, exit with a timeout
            if len(response) == 0:
                raise

        return response, pos_array

class TObjectTable(object):
    """ Helper class to store Atmel's base object information
    """
    def __init__(self):
        self._report_id_count = 0
        self.object_table = {}
        self.report_id_table = [0]   # 0 index reserved for Atmel's internal use
        pass

    def __str__(self):
        str_out = "TObjectTable/"
        for key in self.object_table.keys():
            str_out += "/%s" % str(self[key])
        str_out += "ReportIDs/"
        for id in self.report_id_table:
            str_out += "/%d" % id
        return str_out

    def add(self, object ):
        self.object_table[ object.type() ] = object
        self.report_id_table += [object]*object.report_ids()
        self._report_id_count += object.report_ids()

    def handle_report(self, msg):
        return self.report_id_table[msg[0]].process_report(msg)
    
    def report_id_count(self):
        return self._report_id_count

    def __getitem__(self, key):
        return self.object_table[key]


class TObjectBase(object):
    """ Helper class to store Atmel's base object information
    """
    def __init__(self, element_data, id_count):
        self.element_data = element_data
        self.id_count = id_count

    # Output the object data in a human readable format with str()-operator
    def __str__(self):
        ret = "T%d at %04x - %04x (%d)" % (self.type(), self.address(), self.address()+self.size(), self.report_ids())
        return ret

    # Return object type
    def type(self):
        return self.element_data[0]

    # Return object start address
    def address(self):
        return self.element_data[1] + self.element_data[2]*0x100

    # Return object start address as tuple for i2c methods
    def i2c_addr(self):
        return _lsb_msb( self.address() )

    # Return object size
    def size(self):
        return self.element_data[3] + 1

    # Return object's report ID count (i.e. instance count times report IDs)
    def report_ids(self):
        return (self.element_data[4] + 1) * self.element_data[5]

    # Store object configuration data
    def configure(self,conf_table):
        self.conf_table = conf_table

    # Placeholder for message processing, override this
    def process_report(self, msg):
        msgtemp = msg
        msg = msgtemp[:-2]+["Unhandled T%d message" % int(self.type())]+ msgtemp[-2:]
        #msg = msgtemp[:-2]+[int(self.type())]+ msgtemp[-2:]
        return list(msg)
    
    # Report id range
    # Valid range for T100 finger id is returned range without first two elements
    def report_id_table_range(self):
        return [self.id_count + 1, self.id_count + 1 + self.report_ids()]

class TObjectClasses(object):
    """ Specific Object handler classes
    """
    # #####################################################
    # class to handle T5 Message Processor objects
    class T5Object(TObjectBase):

        # add checksum request to address
        def address(self):
            return self.element_data[1] + self.element_data[2]*0x100 + 0x8000

    # #####################################################
    # class to handle T9 Multiple Touch Touchscreen objects
    class T9Object(TObjectBase):

        def process_report(self, msg):

            if _lsb_msb_2_int(self.conf_table[18:]) < 1024:
                x_pos = msg[2] * 4 + ((msg[4] & 0xC0) >> 6)
            else:
                x_pos = msg[2] * 16 + ((msg[4] & 0xF0) >> 4)

            if _lsb_msb_2_int(self.conf_table[20:]) < 1024:
                y_pos = msg[3] * 4 + ((msg[4] & 0x0C) >> 2)
            else:
                y_pos = msg[3] * 16 + (msg[4] & 0x0F)
                    #X,Y,Z,Finger ID, delay, event type
            return (x_pos, y_pos, msg[6], msg[0] - 2, msg[1])

# ###################################################################

# Helper function to generate an [lsb,msb] -list from an integer address
def _lsb_msb(address):
    return [address % 0x100, address // 0x100]

# Helper function to convert little-endian pair of bytes into an integer
def _lsb_msb_2_int(bytearray):
    return bytearray[1]*0x100 + bytearray[0]