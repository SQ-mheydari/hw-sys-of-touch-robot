"""
Optomotion motherboard memory IO.
Can be used to write and read data to memory controlled by the motherboard.
"""
import base64
import logging
import typing

log = logging.getLogger(__name__)


class MotherboardMemoryBase:
    """
    Optomotion motherboard memory manager.
    Performs operations via OptomotionComm object.
    This is a base class that must be subclassed so that sf_mem_cmd method
    is implemented. This allows easily to create a simulator version of the class.
    """
    # Smart finger memory access SM registers.
    SMP_MEM_SET_CMD = 300
    SMP_MEM_EXE_CMD = 301

    # Smart finger memory commands.
    MEM_CMD_INIT = 0
    MEM_CMD_GET_MAN_ID = 1
    MEM_CMD_SET_MEM_ADDRESS = 2
    MEM_CMD_MEM_WRITE = 3
    MEM_CMD_MEM_READ = 4
    MEM_CMD_GET_DEV_SERIAL_NUMBER = 5
    MEM_CMD_GET_ERROR = 6
    MEM_CMD_SET_DEV_ADDRESS = 7
    MEM_CMD_RESET = 8

    MEM_MAX_SIZE = 127  # bytes

    def __init__(self, optomotion, motherboard_address, mem_dev_addresses=None):
        """
        Initialize motherboard memory interface.
        :param optomotion: OptomotionComm object.
        :param motherboard_address: Address as string e.g. "IO7".
        :param mem_dev_addresses: Devices addresses where memory is accessed.
        There can be multiple memory chips at different addresses.
        """
        log.info("Initializing motherboard memory.")

        self.optomotion = optomotion
        self.motherboard_address = motherboard_address

        if mem_dev_addresses is None:
            mem_dev_addresses = [0, 7]

        self.mem_dev_addresses = mem_dev_addresses

        # Initialize memory operations. Argument 0 means that memory chip read is not yet tested.
        # Thus memory chip can be disconnected at this point.
        val = self.memory_command(self.MEM_CMD_INIT, 0)

        if val != 0:
            raise Exception("Failed to initialize motherboard memory access.")

        self.set_address()

        # Memory should be reset before first read or write operation.
        # Resetting requires memory chip to be connected so this operation is done lazily.
        self._is_reset = False

    def _reset(self):
        if self._is_reset:
            return

        log.debug("Resetting motherboard memory.")

        self.memory_command(MotherboardMemoryBase.MEM_CMD_RESET)
        self._is_reset = True

    def memory_command(self, command, data: typing.Union[int, list] = 0):
        raise NotImplementedError()

    def set_address(self):
        """
        Set motherboard address to use for memory operations.
        """

        val = None

        for mem_addr in self.mem_dev_addresses:
            val = self.memory_command(self.MEM_CMD_SET_DEV_ADDRESS, mem_addr)
            log.debug("Dev %d ID: 0x%06X" % (mem_addr, self.memory_command(self.MEM_CMD_GET_MAN_ID)))

        if val != 0:
            raise Exception("Failed to set device memory access.")

    def read_memory(self, address, size):
        """
        Read data from memory.
        :param address: Address offset in bytes.
        :param size: Number of bytes to read.
        """
        self._reset()

        rdata = []
        self.memory_command(self.MEM_CMD_SET_MEM_ADDRESS, address)

        # 1 bytes read at time.
        for i in range(size):
            val = self.memory_command(self.MEM_CMD_MEM_READ)
            rdata.append(val & 0xff)

        return rdata

    def write_memory(self, address, byte_list):
        """
        Write data to memory.
        :param address: Address offset in bytes.
        :param byte_list: List of bytes to write.
        """
        self._reset()

        log.debug("Writing {} bytes to smart tip.".format(len(byte_list)))

        if (address + len(byte_list)) > self.MEM_MAX_SIZE:
            raise MemoryError("Out of memory. (Max size: %d bytes)" % self.MEM_MAX_SIZE)

        self.memory_command(self.MEM_CMD_SET_MEM_ADDRESS, address)

        return self.memory_command(self.MEM_CMD_MEM_WRITE, byte_list)

    def erase_memory(self, fill_byte=0x00, address=0, size=None):
        """
        Erase or fill memory area.
        :param fill_byte: Byte to fill memory with.
        :param address: Address offset in bytes.
        :param size: Number of bytes to fill.
        """

        if size is None:
            size = MotherboardMemoryBase.MEM_MAX_SIZE

        byte_list = [fill_byte] * size
        self.memory_command(self.MEM_CMD_SET_MEM_ADDRESS, address)

        self.memory_command(self.MEM_CMD_MEM_WRITE, byte_list)

    def write_dict(self, address, dict):
        """
        Store dict to memory.
        :param address: Memory address offset in bytes.
        :param dict: Dict to write. Note that the size of dict converted to bytes may be limited.
        """
        # Convert dict to bytes. Note that some values e.g. 1/3 may take unexpected number of bytes.
        dict_bytes = base64.b64encode(str(dict).encode('ascii'))

        # Write to memory.
        size = len(dict_bytes)
        size_bytes = bytearray([size >> 8, size & 0xff])

        self.write_memory(address, size_bytes + dict_bytes)

        return len(size_bytes + dict_bytes)

    def read_dict(self, address):
        """
        Read dict from memory.
        :param address: Memory address offset in bytes.
        """
        # Read dict from memory
        size_bytes = self.read_memory(address, 2)
        size = (size_bytes[0] << 8) | size_bytes[1]

        if size > MotherboardMemoryBase.MEM_MAX_SIZE - 2:
            raise MemoryError("Maximum size of smart tip memory exceeded.")

        dict_bytes = self.read_memory(address + 2, size)

        if len(dict_bytes) == 0:
            raise IOError("Could not read dictionary from motherboard.")

        return eval(base64.b64decode(bytearray(dict_bytes)).decode('ascii'))


class MotherboardMemorySimulator(MotherboardMemoryBase):
    """
    Motherboard memory simulator. Notice that unlike the real hardware, this does not
    keep values between application restart.
    """
    def __init__(self, optomotion, motherboard_address, mem_dev_addresses=None):
        """
        Initialize motherboard memory interface.
        :param optomotion: OptomotionComm object.
        """
        self._data = bytearray(self.MEM_MAX_SIZE)
        self._current_address = 0

        # This attribute is not part of real motherboard memory interface but can be used to simulate
        # the connection status of HW.
        self.connected = True

        super().__init__(optomotion, motherboard_address, mem_dev_addresses)

    def memory_command(self, command, data=0):
        """
        Send memory command.
        :param command: Command identifier.
        :param data: Command data value.
        :return: Command-specific return value.
        """
        result = None

        if not self.connected:
            raise Exception("Not connected")

        if command == self.MEM_CMD_SET_MEM_ADDRESS:
            self._current_address = data
            result = 0
        elif command == self.MEM_CMD_MEM_WRITE:
            if isinstance(data, int):
                self._data[self._current_address] = data
                self._current_address += 1
            else:
                for val in data:
                    self._data[self._current_address] = val
                    self._current_address += 1
            result = 0
        elif command == self.MEM_CMD_MEM_READ:
            result = self._data[self._current_address]
            self._current_address += 1
        elif command == self.MEM_CMD_INIT:
            result = 0
        elif command == self.MEM_CMD_SET_DEV_ADDRESS:
            result = 0
        elif command == self.MEM_CMD_GET_MAN_ID:
            result = 32

        return result


class MotherboardMemory(MotherboardMemoryBase):
    """
    Optomotion motherboard memory manager.
    Performs operations via OptomotionComm object.
    """

    def __init__(self, optomotion, motherboard_address, mem_dev_addresses=None):
        """
        Initialize motherboard memory interface.
        :param optomotion: OptomotionComm object.
        """
        super().__init__(optomotion, motherboard_address, mem_dev_addresses)

    def memory_command(self, command, data=0):
        """
        Send memory command.
        :param command: Command identifier.
        :param data: Command data value.
        :return: Command-specific return value.
        """

        if self.motherboard_address is None:
            raise Exception("Motherboard address not set when sending memory command.")

        if type(data) != list and type(data) != bytearray:
            data = [data]

        ret = 0

        # How many bytes a single write operation contains.
        # The simplemotion packet max payload is 111 bytes
        # so we can send 27 32-bit values in one packet.
        data_size = 27

        while len(data) != 0:
            wdata = []
            for d in data[:data_size]:
                # First 4 bits are command ID and the rest is associated data.
                wdata.append((command & 0x0f) | (d << 4))

            # Use new command to write multiple values in one sm message
            # Command available in optomotion library version 1.8.3->
            self.optomotion.write_sm_data(self.motherboard_address, self.SMP_MEM_SET_CMD, wdata)

            # Execute write command
            ret = self.optomotion.get_axis_parameter(self.motherboard_address, self.SMP_MEM_EXE_CMD)

            # Zero means that further data should be written before command is completed.
            if ret != 0:
                break

            # Remove sent values from the list
            data = data[data_size:]

        return ret

    def add_command(self, cmd, data):
        """
        Add command to memory handler.
        """
        wdata = (cmd & 0x0f) | (data << 4)
        self.optomotion.write_sm_data(self.motherboard_address, self.SMP_MEM_SET_CMD, [wdata])

    def execute_commands(self):
        """
        Execute commands in memory handler.
        """
        return self.optomotion.get_axis_parameter(self.motherboard_address, self.SMP_MEM_EXE_CMD)

    def read_memory(self, address, size):
        """
        Read data from memory.
        This version is faster than the base implementation.
        :param address: Address offset in bytes.
        :param size: Number of bytes to read.
        """
        self._reset()

        if (address + size) > self.MEM_MAX_SIZE:
            raise Exception("Out of memory. (Max size: %d bytes)" % self.MEM_MAX_SIZE)

        rd_data_list = []

        # Set start address for memory read.
        self.memory_command(self.MEM_CMD_SET_MEM_ADDRESS, address)

        # Send command to read data chunk and return first value.
        self.add_command(self.MEM_CMD_MEM_READ, size)
        rd_data_list.append(self.execute_commands())

        # Read values from buffer
        self.add_command(self.MEM_CMD_MEM_READ, 0)

        while len(rd_data_list) < size:
            # Returned data contains 2 bytes
            rd_data = self.execute_commands()

            rd_data_list.append(rd_data & 0xff)
            rd_data_list.append((rd_data >> 8) & 0xff)
            rd_data_list.append((rd_data >> 16) & 0xff)

        rd_data_list = rd_data_list[:size]

        return rd_data_list
