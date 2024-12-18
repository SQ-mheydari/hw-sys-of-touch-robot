import logging
log = logging.getLogger(__name__)
from tntserver.Nodes.Node import Node, NodeException, json_out
from tntserver.drivers.robots import sm_regs


class Motherboard(Node):
    def __init__(self, name):
        super().__init__(name)
        self._bus_address = None
        self.robot_name = None
        self.io_spec_output = None

    def _init(self, *args, **kwargs):
        # self.robot_name = kwargs.get("robot", "Robot1")
        self._bus_address = int(kwargs.get("bus_address", None))

    def get_robot_driver_connection(self):
        """
        Return robot driver communication object, preferably OptoMotion (It's not tested with any other library)
        :return: robot driver _comm object with set_device_parameter method or None
        """
        try:
            robot = self.find(self.robot_name)
            comm = robot.driver._comm
            if hasattr(comm, 'set_device_parameter'):
                return comm
            else:
                return None
        except AttributeError:
            return None

    @json_out
    def put_output_state(self, name_or_number, state):
        """
        Set state of certain motherboard output.
        :param name_or_number: Configured alias or number of the output.
        :param state: 0 or 1.
        :return: Request output.
        """
        comm = self.get_robot_driver_connection()
        # TODO: needs to be done only once after connecting and only for used output
        #  it should keep track of I/O usage: meaning keep input as input and output as output until said otherwise
        # set pins 1-8 output (01 01 01 01 01 01 01 01)
        if comm is not None:
            comm.set_device_parameter(self._bus_address, param=sm_regs.SMP_DIGITAL_IO_DIRECTION_3,
                                      value=0b0101010101010101)
            output_number = self.get_output_number(name_or_number)
            if output_number is not None:
                return self.set_digital_output(output_number=int(output_number), state=int(state))
            else:
                raise NodeException("Couldn't find configured output named: {}".format(name_or_number))
        else:
            raise NodeException("Robot driver isn't initialized or doesn't have set_device_parameter method")

    def set_digital_output(self, output_number: int, state: int):
        """
        Set digital output using direct simplemotion (SM) register
        examples:
        1 on:
            0b1100
        output 3 off:
            0b010000
        """
        # TODO: check if output_number is a sane value, depending on motherboard type
        #  detect that during runtime or configure in settings
        comm = self.get_robot_driver_connection()
        value = (state << (output_number * 2 + 1)) | (1 << (output_number * 2))
        comm.set_device_parameter(self._bus_address, param=sm_regs.SMP_DIGITAL_OUT_VALUE_1, value=value)
        return {'status': 'OK'}

    def get_output_number(self, name_or_number) -> int:
        """
        Return output number as int based on alias or number (can be int or float)
        :param name_or_number: int or str
        :return: output number or None
        """
        for key in self.io_spec_output:
            if key == name_or_number or self.io_spec_output[key]['alias'] == name_or_number:
                return int(key)     # in case someone puts number as float in configuration
        return None
