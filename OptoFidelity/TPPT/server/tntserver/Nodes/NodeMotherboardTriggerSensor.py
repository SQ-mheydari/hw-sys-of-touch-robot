from tntserver.Nodes.NodeTriggerSensor import *
from tntserver.drivers.sensors.motherboard_trigger import MotherboardTriggerSensor

log = logging.getLogger(__name__)


class NodeMotherboardTriggerSensor(NodeTriggerSensor):
    """
    Node for OptoMotion motherboard trigger solution.

    Example server configuration for this node:
        - name: triggersensor
          cls: NodeMotherboardTriggerSensor
          parent: ws
          arguments:
            robot: Robot1
            io_dev_addr: 8
            trigger_pos: -50
            debug: false
          connection:
    """
    _IO_DEV_ALIAS = "IO"

    def __init__(self, name):
        super().__init__(name)

    def _init(self, robot, io_dev_addr=None, trigger_pos=-50, debug=False,
              swap_encoder_read_dir=False, **kwargs):
        """
        Initialize sensor.
        :param robot: Name of the robot that has trigger IO in given address.
        :param io_dev_addr: IO device address of the trigger.
        :param trigger_pos: Default triggering position in encoder pulses.
        :param debug: Determines whether trigger HW for development purposes is used.
        :param swap_encoder_read_dir: Swap encoder_read_direction.
        :param kwargs:
        """
        self._driver = None
        try:
            if debug:
                # Either robot simulator is used or there is no robot at all but there is trigger HW
                # for development purposes.
                self._driver = MotherboardTriggerSensor(None, io_dev_addr, self._IO_DEV_ALIAS, trigger_pos=trigger_pos)
            else:
                # Check robot name from which we take the driver.
                # We need to access Optomotion handle through robot.driver._comm at the moment.
                robot = Node.find(robot)
                if robot is not None and robot.driver is not None and robot.driver._comm is not None:
                    # Don't initialize trigger sensor connection towards robot simulator as there is no support.
                    self._driver = MotherboardTriggerSensor(robot.driver._comm, io_dev_addr, self._IO_DEV_ALIAS,
                                                            trigger_pos=trigger_pos,
                                                            swap_encoder_read_dir=swap_encoder_read_dir)
                else:
                    log.error("Triggersensor init failed: Robot driver not available for Robot={}".format(robot))

        except Exception as e:
            log.error("Triggersensor init failed: " + str(e))
