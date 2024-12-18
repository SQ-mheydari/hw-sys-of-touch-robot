import logging
from functools import wraps

import tntserver.drivers.robots.sm_regs as SMRegs
from optomotion import OptoMotionComm

log = logging.getLogger(__name__)


def log_optomotion_error(func):
    """
    Decorator used to log optomotion errors in methods that use the communication class.
    Requires self.get_errors() and log to be available to the function being decorated. Original exception will be
    re-raised after sending log message.

    Intended usage is for functions that cannot be safely retried. For functions that can be retried use
    optomotion_retry decorator, it will log error and retry function call.
    :param func: function to be decorated
    :return: decorated function
    """
    @wraps(func)
    def f(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as exc:
            log.exception(exc)
            optomotion_errors = self.get_errors()
            log.error('Active drive faults: {}'.format(optomotion_errors))
            raise exc
    return f


class LoggingMeta(type):
    """
    Helper metaclass to decorate all member functions with a wrapped version to get proper error logging.
    """
    def __new__(cls, name, bases, namespace):
        for attributeName, attribute in namespace.items():
            if callable(attribute) and attributeName != 'get_errors':
                # replace it with a wrapped version
                attribute = log_optomotion_error(attribute)
            namespace[attributeName] = attribute
        return super().__new__(cls, name, bases, namespace)


class GoldenMovOptomotion(OptoMotionComm, metaclass=LoggingMeta):
    """
    Wrapper class for Optomotion which allows overriding some of the base class methods.
    """

    def __init__(self, com_spec, axis_specs=None):
        super().__init__(com_spec, axis_spec=[])
        self.axis_specs = axis_specs
        self.optomotion_axis_specs = {}

    def discover_axis(self, address, axis_alias):
        """
        Calls discover_axis of optomotion and gathers each optomotion (Simplemotion) level axis specs to a dict.
        :param address: Axis address to discover.
        :param axis_alias: Axis alias.
        :return: None.
        """
        super().discover_axis(address, axis_alias)
        self.optomotion_axis_specs[axis_alias] = self.get_axis_spec(axis_alias)

    def get_scaled_axis_setpoint(self, axis_alias):
        """
        Returns current axis setpoint scaled to millimeters or degrees.
        :param axis_alias: Axis name.
        :return: Current setpoint scaled to user units.
        """
        setpoint = self.get_axis_parameter(axis_alias, SMRegs.SMP_ABSOLUTE_SETPOINT)
        return setpoint * self.optomotion_axis_specs[axis_alias].scaling_factors.posFromDevice

    def read_axis_parameter(self, axis, param):
        """
        Reads one parameter value.
        Returns int value of parameter.
        This is Rocktomotion compatibility.
        """
        return self.get_axis_parameter(axis, param)

    # metaclass will be only applied to methods defined here
    # that's why below methods are being 'overridden'
    def home(self):
        return super().home()

    def home_axes(self, axes):
        return super().home_axes(axes)

    def restore_axis_configuration(self, axis):
        return super().restore_axis_configuration(axis)

    def set_speed(self, speed):
        return super().set_speed(speed)

    def set_acceleration(self, acc):
        return super().set_acceleration(acc)

    def move_absolute(self, axes, with_speed=False):
        return super().move_absolute(axes, with_speed)

    def move_buffered(self, axes):
        return super().move_buffered(axes)

    def move_ptp(self, axes):
        return super().move_ptp(axes)

    def move_axis_relative(self, axis_alias, distance, with_speed=False):
        return super().move_axis_relative(axis_alias, distance, with_speed)

    def force_move(self, force, force_axis, positions={}, with_speed=False):
        return super().force_move(force, force_axis, positions, with_speed)

    def probe(self, force, force_axis, max_position, positions={}):
        return super().probe(force, force_axis, max_position, positions)

    def disable_axes(self, axes=["x", "y"]):
        return super().disable_axes(axes)

    def tare(self):
        return super().tare()

    def get_state(self):
        return super().get_state()

    def wait(self, time_in_millis):
        return super().wait(time_in_millis)

    def clear_errors(self):
        return super().clear_errors()

    def stop_motion(self):
        return super().stop_motion()

    def abort_motion(self):
        return super().abort_motion()

    def write_output(self, axis, line, value):
        return super().write_output(axis, line, value)

    def write_outputs(self, axis, *outputs):
        return super().write_outputs(axis, outputs)

    def get_force(self, cached=False):
        return super().get_force(cached)

    def get_position(self, cached=False):
        return super().get_position(cached)

    def set_axis_parameter(self, axis, param, value):
        return super().set_axis_parameter(axis, param, value)

    def set_device_parameter(self, address, param, value):
        return super().set_device_parameter(address, param, value)

    def get_axis_parameter(self, axis, param):
        return super().get_axis_parameter(axis, param)

    def get_axis_spec(self, alias):
        return super().get_axis_spec(alias)

    def get_axis_specs(self):
        return super().get_axis_specs()

    def remove_axis(self, alias):
        return super().remove_axis(alias)

    def set_force_control_params(self, axis, p, i, d, constant):
        return super().set_force_control_params(axis, p, i, d, constant)
