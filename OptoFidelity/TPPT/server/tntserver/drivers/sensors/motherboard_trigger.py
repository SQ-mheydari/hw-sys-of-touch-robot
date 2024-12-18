import logging

from optomotion import *
import tntserver.drivers.robots.sm_regs as SMRegs

log = logging.getLogger(__name__)


class MotherboardTriggerSensor:
    """
    Class for OptoMotion motherboard based trigger sensor. Specs:
    https://git.optofidelity.net/tnt/OptoMotion/blob/OFMD2_master/OFIC_FW/docs/OFMD2_SM_control.pdf
    """

    DIRECTION_POSITIVE = 0
    DIRECTION_NEGATIVE = 1

    IP_ADDRESS = '192.168.127.254'

    def __init__(self, optomotion_comm, io_dev_addr: int, io_dev_alias: str, trigger_pos: int,
                 swap_encoder_read_dir: bool = False):
        """
        Set up handling of motherboard trigger solution, and initialize Optomotion connection if requested.
        :param optomotion_comm: OptoMotionComm object to be used to communicate with motherboard.
                                None means that there is not one and it should be created.
        :param io_dev_addr: IO device address of the trigger.
        :param io_dev_alias: IO device alias of the trigger.
        :param trigger_pos: Default triggering position in encoder pulses.
        :param swap_encoder_read_dir: Swap encoder_read_direction.
        """
        self._comm = optomotion_comm
        # Indicates whether development optomotion board is used for trying out triggering
        self._dev_hw = False
        self._io_dev_alias = io_dev_alias
        self._trigger_pos = trigger_pos
        self._swap_encoder_read_dir = swap_encoder_read_dir

        if self._comm is None:
            # This is a solution for robot simulator and motherboard trigger dev HW combination
            # It seems to do 5 connection attempts which is too much to have when not having the debug board

            self._dev_hw = True

            # If this is done and there is already optomotion connection towards real robot, this connection will
            # succeed and previous connection will be disconnected and you will see plenty of failure messages.
            self._comm = OptoMotionComm(self.IP_ADDRESS, [])

            # Thread for checking dev HW encoder value regularly and print it for debugging purposes.
            # Thread start delay is a rather random value so that the server would have time to start and
            # then first printout would be seen.
            print_encoder_value = threading.Timer(3, function=self._print_encoder)
            print_encoder_value.start()

        # REMEMBER THIS! OTHERWISE SM COMMUNICATION DOESN'T WORK TO MOTHERBOARD!
        self._comm.discover_axis(io_dev_addr, self._io_dev_alias)

        self.reset_encoder_value()

        # Set trigger to some initial value so that the output from motherboard is correctly initialized.
        self._set_trigger(direction=self.DIRECTION_NEGATIVE)

    def __del__(self):
        """
        Destructor. Close connection to development HW.
        """
        if self._dev_hw is True:
            self._comm.close_connection()
            log.info("Closed trigger sensor connection.")

    def _set_trigger(self, direction, trigger_pos=None, pulse_length=100):
        """
        Resets, sets trigger and starts triggering.
        :param direction: Trigger direction (DIRECTION_POSITIVE/DIRECTION_NEGATIVE).
        :param trigger_pos: Encoder position when the trigger will occur (unit: encoder pulse count).
                            If None, default pulse count configured for the sensor will be used.
        :param pulse_length: Length of the pulse in milliseconds. 16bit value from 0-65535.
        """

        # Set pin 1 output and 2-8 input (00 00 00 00 00 00 00 01)
        # This is not needed in this example, beacause trigger output is set to output pin 12.
        # That pin is automatically set output when trigger is configured.
        self._comm.set_axis_parameter('IO', SMRegs.SMP_DIGITAL_PIN_MODES_1, 0b0000000000000001)

        # Reset encoder to zero
        self._comm.set_axis_parameter('IO', SMRegs.SMP_ENCODER_RESET, 0)

        # Trigger output pin 12 (3.3V) (0 -> output 1)
        param = 11
        # Trigger direction positive (0=positive, 1=negative). Bits 4:5 in SMP_ENCODER_TRIGGER_PARAMS.
        assert(direction == self.DIRECTION_POSITIVE or direction == self.DIRECTION_NEGATIVE)
        param |= (direction << 4)
        # Trigger pulse length in milliseconds. Bits 6:21 in SMP_ENCODER_TRIGGER_PARAMS. 16 bit value so max is 65535.
        assert(pulse_length < 65536)
        param |= (pulse_length << 6)
        # Encoder read direction. (0=A&B not swapped, 1=A&B swapped)
        if self._swap_encoder_read_dir:
            param |= (1 << 22)
        # Set parameters
        self._comm.set_axis_parameter(self._io_dev_alias, SMRegs.SMP_ENCODER_TRIGGER_PARAMS, param)

        # Set trigger position
        if trigger_pos is None:
            trigger_pos = self._trigger_pos
        self._comm.set_axis_parameter(self._io_dev_alias, SMRegs.SMP_ENCODER_TRIGGER_POS, trigger_pos)

        # Start trigger
        self._comm.set_axis_parameter(self._io_dev_alias, SMRegs.SMP_ENCODER_TRIGGER_START, 1)

    def _get_trigger(self):
        """
        Gets encoder value of the trigger.
        :return: Trigger value.
        """
        return self._comm.get_axis_parameter(self._io_dev_alias, SMRegs.SMP_ENCODER_VALUE)

    def reset_encoder_value(self, reset_value=0):
        """
        Reset internal encoder pulse counter value to 0.
        :return: Device response to command.
        """
        return self._comm.set_axis_parameter(self._io_dev_alias, SMRegs.SMP_ENCODER_RESET, reset_value)

    def set_trigger_touch_start(self):
        """
        Set camera sync pulse triggering to single pulse output. Generate one pulse when finger touches the DUT
        or other surface. In practice, this means that encoder count decreases below threshold value.
        """
        # TODO: And there is a risk that rising and falling will swap as it depends on which direction encoder stripe
        # is installed. There's no markings on it. Motherboard could handle this by checking whether direction
        # is inverted as that's what we configure to the drive card if positive values are not going down.
        self._set_trigger(direction=self.DIRECTION_NEGATIVE)

    def set_trigger_touch_end(self):
        """
        Set camera sync pulse triggering to single pulse output. Generate one pulse when finger releases up from the
        DUT or other surface. In practice, this means that encoder count increases above threshold value.
        """
        self._set_trigger(direction=self.DIRECTION_POSITIVE)

    def _print_encoder(self):
        """
        Prints dev HW encoder value regularly.
        """
        prev_val = -99999
        while True:
            val = self._get_trigger()
            if abs(val - prev_val) > 10:
                print("Trigger sensor encoder value: {}".format(val))
                prev_val = val
            time.sleep(0.1)


if __name__ == "__main__":
    # Test trigger dev HW without TnT server.
    # Change io_dev_addr according to HW board configuration.
    sensor = MotherboardTriggerSensor(optomotion_comm=None, io_dev_addr=38, io_dev_alias="IO", trigger_pos=-50)

    # To test different features, you can uncomment some of the following lines.
    #sensor.set_trigger_touch_start()
    #sensor.set_trigger_touch_end()
    sensor._set_trigger(MotherboardTriggerSensor.DIRECTION_POSITIVE, trigger_pos=1000, pulse_length=1000)
