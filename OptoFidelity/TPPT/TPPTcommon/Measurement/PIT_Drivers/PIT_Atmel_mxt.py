import time

# The main class that gets instantiated by the PIT firmware
class device_driver(object):

    def __init__(self, i2c):
        self.i2c = i2c
        self.counter = 10

    def Multiplexer(self,index):
        self.i2c.write_multiplexer_index(index)
        return [index]

    def Initialize(self):
        self.Multiplexer(0)
        self.device = maXTouch(i2c, 400)
        self.device.config()
        self.i2c.read_ext_rise_fall([1,0,1,1,1,1,1,1])
        return "OK"

    def ReturnP2PArray(self, index = 0, waitForFingerInterrupt = True):
        self.device.flush_messages()
        return self.device.read_messages(3.0,0.0) + [ 'OK', '' ]
    
    # this function will be called by the PIT firmware, until I2C-timeout occurs
    def ReturnCLineArray(self, waitForFingerInterrupt = True):
        return self.device.read_messages(3.0,0.0, True) + [ 'OK', '' ]
    
    def WriteSleepMode(self, sleepMode):
        if sleepMode == 1:
            self.device.set_sleep_mode([255,255])
        if sleepMode == 2:
            self.device.set_sleep_mode([20,7])
        if sleepMode == 3:
            self.device.set_sleep_mode([0,0])
        
        status = []
        status.append((0,0,0,0,0,0))
        status.append("OK")
        status.append("")

        return status
    def FindAddress(self):
        address = []
        for addr in range(0x01,0x7F):
            try:
                self.i2c.read(addr, 1)
                address.append(addr)
                break
            except I2CError:
                time.sleep(0.001)
        return address

    def ReadFWVersion(self):
        """ Return chip fw and this script versions. Also date created and user name """

        status = []
        fw = "1.0 build:1.0"
        status.append((0,0,0,0,0,0))
        status.append("Panel: " + fw)
        status.append("")

        return status

    def ReturnInterruptStates(self):
        state = []
        state = self.i2c.read_interrupt_state()
        return state
    
    def ReturnInterruptStates(self):
        state = []
        state = self.i2c.read_interrupt_state()
        return state
    
    def ReturnTimestamps(self):
        timestamps = self.i2c.read_timestamps()
        timestamps = [x /1000.0 for x in timestamps]
        return timestamps + [timestamps[1]-timestamps[2]]
    
    def SingleTrigger(self):
        self.i2c.set_trigger([False,True,True,True])
        return 0
    
    def NormalTrigger(self):
        self.i2c.set_trigger([True,True,True,True])
        return 0
    
    def ClearBuffer(self):
        try:
            self.device.read_messages(0.001, 0.001)
        except I2CError:
            pass

    
# Class to implement maXTouch -specific functionality
class maXTouch(object):

    def __init__(self, i2c, speed):

        self.i2c = i2c
        self.i2c.setspeed(speed)
        self.address = 0x4A # Default I2C address for Atmel
        
        # Lets find device address
        for addr in range(0x40,0x7F):
            try:
                self.i2c.read(addr, 1)
                break
            except I2CError:
                time.sleep(0.001)
        self.address = addr

        # First, read the information block
        self.info_block = self.i2c.write_then_read(self.address, _lsb_msb(0), 6, 100, False)

        # Read rest of the information block, based on the number of elements in the Object Table
        self.info_block += self.i2c.write_then_read(self.address, _lsb_msb(6), self.info_block[5]*6+3, 100, False)

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
                tobj = getattr(TObjectClasses, 'T%dObject' % tobj_data[0])(tobj_data)
            except AttributeError:
                # If no specific class was found, use a generic one
                tobj = TObjectBase(tobj_data)

            tobj.configure( self.i2c.write_then_read(self.address, tobj.i2c_addr(), tobj.size(), 100, False) )
            self.object_table.add( tobj )

    def config(self):
        t9 = self.object_table[9]
        t9.conf_table[0] = 0x8f    # report PRESS, RELEASE and MOVE
        self.i2c.write(self.address, t9.i2c_addr(), t9.size())

    def set_sleep_mode(self, params):
        t7 = self.object_table[7]
        t7.conf_table[0] = params[0]
        t7.conf_table[1] = params[1]
        self.i2c.write(self.address, t7.i2c_addr(), t7.size())



    # flush the command processor object from pending messages
    def flush_messages(self):
        try:
            self.read_messages(0.1, 0.1)
        except I2CError:
            pass

    # read and process all messages after trigger occurs, until timeout occurs
    # if wait_time is zero, message trigger is not waited on
    # if timeout is zero, only first message trigger is processed
    # if no trigger occurs until wait_time has passed, timeout exception will occur
    # if no message is received until wait_time+timeout has passed, timeout exception will occur
    def read_messages(self, wait_time=1.0, timeout=0.0, line=False):

        # if wait time is defined, wait for trigger
        wait_for_int = ( wait_time > 0 )

        response = []
        t5 = self.object_table[5]
        msg_size = t5.size()
        t44 = self.object_table[44]

        # read the number of pending messages from message count object T44, and store timestamp of the trigger
        msg_count = self.i2c.write_then_read(self.address, t44.i2c_addr(), t44.size(), wait_time*1000+1, wait_for_int)[0]
        timestamps = self.i2c.read_timestamps()
        timestamp = timestamps[0] / 1000.0
        delay = timestamps[1]/1000.0 - timestamp
        delayCLine = self.i2c.read_PanelInterruptDelay()[0]/1000.0
        if line:
            delay = delayCLine
        
        start_time = timestamp

        try:
            
            while True:
                
                # check, if we should exit due to timeout
                if timestamp - start_time > timeout * 1000:
                    break
                
                # read all the pending messages from command processor object T5
                data = self.i2c.write_then_read(self.address, t5.i2c_addr(), msg_count*msg_size, 100, True)

                # pass the retrieved messages to the appropriate object handlers
                for i in range(msg_count):
                    proc_msg = self.object_table.handle_report( data[i*msg_size:i*msg_size+msg_size] )
                    response.append( proc_msg + (delay,start_time))
                    #if proc_msg != None:
                        #response.append( proc_msg + (8, msg_count ))

                # read the number of pending messages from message count object T44
                msg_count = self.i2c.write_then_read(self.address, t44.i2c_addr(), t44.size(), 100, wait_for_int)[0]
                timestamp = self.i2c.read_timestamps()[0] / 1000

        except I2CError:
            
            # if we did not receive any messages, exit with a timeout
            if len(response) == 0:
                raise

        return response
    
# Helper class to store Atmel's base object information
class TObjectTable(object):

    def __init__(self):
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

    def handle_report(self, msg):
        return self.report_id_table[msg[0]].process_report(msg)

    def __getitem__(self, key):
        return self.object_table[key]

        
# ###################################################################
# Helper class to store Atmel's base object information
class TObjectBase(object):

    def __init__(self, element_data):
        self.element_data = element_data

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
        msg = msgtemp[:-2]+"Unhandled T%d message" % (self.type())+ msgtemp[-2:]
        return msg

# ###################################################################
# Specific Object handler classes
class TObjectClasses(object):

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

            return ( x_pos, y_pos, msg[6], msg[0]-2, )


# ###################################################################
        
# Helper function to generate an [lsb,msb] -list from an integer address
def _lsb_msb(address):
    return [address % 0x100, address // 0x100]

# Helper function to convert little-endian pair of bytes into an integer
def _lsb_msb_2_int(bytearray):
    return bytearray[1]*0x100 + bytearray[0]