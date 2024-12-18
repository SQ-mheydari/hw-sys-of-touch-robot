from tntserver.drivers.robots.goldenmov.mbmemory import MotherboardMemory, MotherboardMemorySimulator
from optomotion import OptoMotionComm
import time
import logging


log = logging.getLogger(__name__)


class MemoryDeviceManager:
    """
    Memory device manager that uses communication with Optomotion motherboard.
    Implements several modes of operation:
    normal - Use the same Optomotion motherboard and connection as the robot motion axes.
    external - Use different Optomotion motherboard and connection than the robot motion axes (if any e.g. simulator).
    simulator - Simulate motherborad connection.
    The external mode is useful for testing memory device functionality by using robot simulator but real HW for the
    memory devices.
    """
    MODE_NORMAL = "normal"
    MODE_EXTERNAL = "external"
    MODE_SIMULATOR = "simulator"

    def __init__(self, mode, addresses, comm=None, ip_address=None, id_chip_address=7):
        """
        Initialize memory device manager.
        :param mode: Operation mode. One of MODE_NORMAL, MODE_EXTERNAL, MODE_SIMULATOR.
        :param addresses: Dictionary of abstract name - motherboard address pairs e.g. {"tool1": 8}.
        :param comm: Pre-initialized OptoMotionComm object when using normal mode.
        :param ip_address: IP address of motherboard when using external mode.
        :param id_chip_address: Last digit of ID chip part number is used as its memory address.
        """
        self.mode = mode
        self.addresses = addresses
        self.aliases = {}
        self.id_chip = id_chip_address
        self.memory_managers = {}
        self.comm = None

        if mode == MemoryDeviceManager.MODE_EXTERNAL:
            self.comm = OptoMotionComm(ip_address, [])
        elif mode == MemoryDeviceManager.MODE_NORMAL:
            self.comm = comm

        for name, address in addresses.items():
            alias = "IO" + str(address)
            self.aliases[name] = alias

        if self.comm:
            for name, address in addresses.items():
                self.comm.discover_axis(address, self.aliases[name])

        if mode == MemoryDeviceManager.MODE_EXTERNAL:
            for name in self.addresses.keys():
                self.memory_managers[name] = MotherboardMemory(self.comm, self.aliases[name],
                                                                    mem_dev_addresses=[self.id_chip])
        elif mode == MemoryDeviceManager.MODE_NORMAL:
            for name in self.addresses.keys():
                self.memory_managers[name] = MotherboardMemory(self.comm, self.aliases[name],
                                                                    mem_dev_addresses=[self.id_chip])
        elif mode == MemoryDeviceManager.MODE_SIMULATOR:
            for name in self.addresses.keys():
                self.memory_managers[name] = MotherboardMemorySimulator(self.comm, self.aliases[name],
                                                                             mem_dev_addresses=[self.id_chip])
        else:
            raise Exception("Unrecognized memory device mode {}.".format(mode))

    @property
    def names(self):
        return self.aliases.keys()

    def is_device_connected(self, name, retry_count=10):
        """
        Check if smart tip is attached to specific tool.
        :param name: Name matching to device.
        :param retry_count: How many times to retry read operation.
        :return: True if tip is connected.
        """
        if name not in self.aliases:
            raise Exception("Unrecognized device name {}.".format(name))

        memory = self.memory_managers[name]

        for i in range(retry_count + 1):
            try:
                # Try to read one byte to check for connection.
                memory.read_memory(0, 1)

                return True
            except Exception as e:
                time.sleep(0.01)

        return False

    def read_memory_device_data(self, name, retry_count=10):
        """
        Read memory device data.
        :param name: Name of device.
        :param retry_count: How many times to retry read operation.
        :return: Data as dict.
        """
        memory = self.memory_managers[name]

        for i in range(retry_count + 1):
            try:
                data = memory.read_dict(address=0)
                log.debug("Read memory device data: %s" % data)

                return data
            except Exception as e:
                log.error("Could not read memory device data: {}. Retrying.".format(str(e)))
                time.sleep(0.01)
        else:
            log.error("Could not read memory device data.")
            raise Exception("Could not read memory device data after {} retries.".format(retry_count))

    def write_memory_device_data(self, name, data, retry_count=10):
        """
        Write data to smart tip device.
        :param name: Name of device.
        :param data: Data as dict. Note that maximum size of data can be quite limited.
        :param retry_count: How many times to retry write operation.
        """
        memory = self.memory_managers[name]

        for i in range(retry_count + 1):
            try:
                size = memory.write_dict(0, data)
                log.debug("Write (%d): %s" % (size, str(data)))
                break
            except Exception as e:
                log.error("Could not write memory device data: {}. Retrying.".format(str(e)))
                time.sleep(0.01)
        else:
            raise Exception("Could not write memory device data after {} retries.".format(retry_count))
