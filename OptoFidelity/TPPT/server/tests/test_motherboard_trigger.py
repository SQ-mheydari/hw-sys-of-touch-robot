from tests.test_opto_std_force import OptomotionCommStub
from tntserver.drivers.sensors.motherboard_trigger import MotherboardTriggerSensor
import tntserver.drivers.robots.sm_regs as SMRegs


def test_motherboard_trigger_reset():
    mb_trigger = MotherboardTriggerSensor(optomotion_comm=OptomotionCommStub(), io_dev_addr=31,
                                          io_dev_alias="io", trigger_pos=250)
    mb_trigger.reset_encoder_value(reset_value=100)
    trigger_value = mb_trigger._comm.get_axis_parameter("io", SMRegs.SMP_ENCODER_RESET)

    # Check that encoder reset value is set correctly
    assert trigger_value == 100


def test_trigger_direction_setting():
    mb_trigger = MotherboardTriggerSensor(optomotion_comm=OptomotionCommStub(), io_dev_addr=31,
                                          io_dev_alias="io", trigger_pos=250)

    # Check that trigger position from sensor init is stored
    param_value = mb_trigger._comm.get_axis_parameter("io", SMRegs.SMP_ENCODER_TRIGGER_POS)
    assert param_value == 250

    # Touch start is negative direction, default pulse_length 100
    mb_trigger.set_trigger_touch_start()
    param_value = mb_trigger._comm.get_axis_parameter("io", SMRegs.SMP_ENCODER_TRIGGER_PARAMS)
    assert param_value == 11 | (MotherboardTriggerSensor.DIRECTION_NEGATIVE << 4) | (100 << 6)

    # Touch end is positive direction, default pulse_length 100
    mb_trigger.set_trigger_touch_end()
    param_value = mb_trigger._comm.get_axis_parameter("io", SMRegs.SMP_ENCODER_TRIGGER_PARAMS)
    assert param_value == 11 | (MotherboardTriggerSensor.DIRECTION_POSITIVE << 4) | (100 << 6)

    # Check that trigger is enabled
    start = mb_trigger._comm.get_axis_parameter("io", SMRegs.SMP_ENCODER_TRIGGER_START)
    assert start == 1


def test_encoder_read():
    mb_trigger = MotherboardTriggerSensor(optomotion_comm=OptomotionCommStub(), io_dev_addr=31,
                                          io_dev_alias="io", trigger_pos=250)

    value = 12345
    mb_trigger._comm.set_axis_parameter("io", SMRegs.SMP_ENCODER_VALUE, value)
    assert mb_trigger._get_trigger() == value

