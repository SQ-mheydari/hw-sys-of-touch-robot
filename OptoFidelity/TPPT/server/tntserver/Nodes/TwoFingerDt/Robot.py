from tntserver.Nodes.Node import json_out, NodeException
from .tip_changer import TwoFingerTipChanger
from tntserver.drivers.robots import two_finger_dt_program
from tntserver.drivers.robots.two_finger_dt import TwoFingerDT
import tntserver.Nodes.TnT.Robot
import logging
log = logging.getLogger(__name__)


class Robot(tntserver.Nodes.TnT.Robot.Robot):
    def __init__(self, name):
        super().__init__(name)

    def _init(self, **kwargs):
        # For safety, Robot speed and acceleration are always set to default values given as arguments.
        if "speed" in kwargs:
            self.robot_velocity = float(kwargs["speed"])
        if "acceleration" in kwargs:
            self.robot_acceleration = float(kwargs["acceleration"])

        log.debug("Robot velocity={} acceleration={}".format(self.robot_velocity, self.robot_acceleration))

        self._tip_changer = TwoFingerTipChanger(self)

        self._tip_changer.max_tip_change_speed = kwargs.get("max_tip_change_speed", 100.0)
        self._tip_changer.max_tip_change_acceleration = kwargs.get("max_tip_change_acceleration", 300.0)

        # If multifinger is attached according to config, ask user to remove it before homing can proceed.
        if self.has_multifinger():
            input("Please remove multifinger from robot. Then press Enter to continue homing.")

            mount = self.find_mount("tool1")
            mount.tool.tip.remove_object_from_parent()

            # TODO: Tip status is not updated to config. For some reason self.save() does not work if invoked here.

        host = kwargs.get("host", None)
        port = kwargs.get("port", None)
        axis_limits = kwargs.get("axis_limits", None)
        tf_rotate_speed = kwargs.get("tf_rotate_speed", 30)
        tf_move_speed = kwargs.get("tf_move_speed", 30)
        thresholds = kwargs.get("thresholds", None)
        simulator = kwargs.get("simulator", False)
        separation_offset = kwargs.get("separation_offset", 10.0)
        safe_distance = kwargs.get("safe_distance", 200.0)

        self.driver = TwoFingerDT(host, port, axis_limits, tf_rotate_speed, tf_move_speed,
                                   thresholds, simulator, separation_offset, safe_distance)

        self.program = two_finger_dt_program.Program(self.object_parent, self.driver)

    @json_out
    def put_home(self):
        """
        Commands the robot to go into home position.
        """
        # Prevent homing via API if multifinger is attached.
        if self.has_multifinger():
            raise NodeException("Cannot home while multifinger is attached.")

        self.driver.home()
        self.program.reset()

    @json_out
    def put_finger_separation(self, distance, kinematic_name=None):
        """
        Set separation of two fingers in mm. Separation distance is measured from finger axes.
        :param distance: Distance in mm.
        :param kinematic_name: Name of kinematic to use for the motion. Does not affect tw-finger robot.
        :return: Dictionary with "status" key.
        """
        if self.has_multifinger():
            raise NodeException("Can't change finger separation while multifinger is attached!")

        self.driver.set_finger_separation(distance)

        return {"status": "ok"}

    @json_out
    def get_finger_separation(self):
        """
        Get separation of two fingers in mm.
        :return: Separation distance in mm.
        """
        return self.driver.get_finger_separation()

    @json_out
    def get_finger_separation_limits(self):
        """
        Get minimum and maximum axis-to-axis separation values.
        :return: Minimum and maximum values as list [min_separation, max_separation].
        """
        return self.driver.get_finger_separation_limits()
