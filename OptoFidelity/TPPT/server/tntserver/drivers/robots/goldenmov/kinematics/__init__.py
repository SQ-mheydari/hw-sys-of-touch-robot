import numpy as np
import logging
import importlib
import copy
from fik.ap_model import APModel

log = logging.getLogger(__name__)


class RobotKinematics:
    """
    Kinematics class for implementing transformation
    between robot joints and our world coordinates.

    Kinematics handled base transformation and tool transformation.
    """

    class RobotPositionBase:
        """
        Base class for RobotPosition
        This class should be subclassed by kinematic model and passed to RobotKinematics.__init__
        The subclass must define __slots__ (__slots__ = ["frame", "d", "t"] at least)

        Class using __slots__ should be quicker than using dicts

        RobotPosition should have at least parameters (and the default has):
            'frame' which contains effective position with orientation
            't' track time in seconds
            'd' track position in millimeters
        """

        def __init__(self, **kwargs):
            for field in self.__slots__:
                setattr(self, field, kwargs.get(field, None))

        def copy(self):
            return copy.copy(self)

        def __str__(self):
            s = ""
            for name in [v for v in dir(self) if not v.startswith("_")]:
                value = getattr(self, name)
                if not callable(value):
                    if issubclass(value.__class__, np.ndarray):
                        from toolbox import robotmath
                        value = robotmath.frame_to_xyz_abc_string(value)
                    s += "{} = {}\n".format(name, value)
            return s

    def __init__(self, robot, robotposition_cls):
        """
        :param robotposition_cls: RobotPosition class, defined by the kinematic model for a robot
        """

        self.robot = robot

        # Robot driver that uses the kinematic.
        self.driver = None

        self._robotposition_cls = robotposition_cls

        # Build joints <-> axis names mapping
        axis = []
        for address, specs in self.specs().items():
            axis.append((address, specs["alias"]))

        # Kinematics parameters that are read from robot configuration during init.
        self.parameters = {}

        self.joint_calibration_model = None
        if self.calibration_data:
            if self.calibration_data.get('ap_model', None) is not None:
                log.info("Using AP model calibration.")
                self.joint_calibration_model = \
                    APModel.from_coefficient_dictionary(coefficients=self.calibration_data['ap_model']['coefficients'])

    def create_robot_position(self, **kwargs):
        """
        Create robot position object corresponding to the kinematic model.
        E.g. kinematics.create_robot_position(frame=frame, voicecoil1=0).
        :param kwargs: Keyword arguments passed to the init method of the robot position object.
        :return: Robot position object.
        """
        return self._robotposition_cls(**kwargs)

    @property
    def calibration_data(self):
        """
        Calibration data is an arbitrary dictionary of data that kinematics
        can use to calibrate parts of a kinematic chain.
        The data is primarily stored under Robot node.
        """
        return self.robot.calibration_data

    def calibrate(self, parameters):
        raise NotImplemented("Abstract base class method")

    @staticmethod
    def get_model(model):
        """
        Kinematic model files are named "kinematic_xxxx_yyyy_py"
        model = xxxx

        :param model: model name as string; "3axis"
        :return: Kinematic model
        """
        module = importlib.import_module(".kinematic_{}".format(model),
                                         "tntserver.drivers.robots.goldenmov.kinematics")
        cls = getattr(module, "Kinematic_{}".format(model))

        return cls

    def joints_to_position(self, joints: dict, kinematic_name=None, tool=None, calibrated=False):

        # Apply possible joint calibration to joint values, then call actual FK function with modified joints. Each
        # child class must implement self._joints_to_position()
        if self.joint_calibration_model is not None:
            joints = self.joint_calibration_model.compensate_joint_value_fk(joints)

        return self._joints_to_position(joints=joints, kinematic_name=kinematic_name, tool=tool, calibrated=calibrated)

    def _joints_to_position(self, joints: dict, kinematic_name=None, tool=None, calibrated=False):
        raise Exception("Abstract base class method")

    def positions_to_joints(self, positions: list, kinematic_name=None, tool_inv=None, calibrated=False) -> list:
        """
        Map list of positions to corresponding list of joint values.
        :param positions: List of positions.
        :param kinematic_name: Name of kinematic to use.
        :param tool_inv: Inverse of tool transform.
        :param calibrated: Use calibrated model?
        :return: Joints corresponding to each position.
        """
        raise Exception("Abstract base class method")

    def _positions_to_joints(self, positions: list, axis_setpoints, kinematic_name=None,  tool_inv=None) -> list:
        # Compute IK for position and apply calibration to joint values, if available. Child class must implement
        # self._position_to_joints()
        joints_list = [self._position_to_joints(pos=pos, axis_setpoints=axis_setpoints, kinematic_name=kinematic_name,
                                                tool_inv=tool_inv) for pos in positions]

        if self.joint_calibration_model is not None:
            joints_list = self.joint_calibration_model.compensate_joint_values_list_ik(joints_list)
        return joints_list

    def _position_to_joints(self, pos, axis_setpoints, kinematic_name=None, tool_inv=None) -> dict:
        raise Exception("Abstract base class method")

    def get_scaled_axis_setpoints(self):
        """
        Get scaled axis setpoints. If kinematics has joint calibration model the value is compensated
        to FK direction. This method should be used if IK uses current axis setpoint to resolve redundant kinematics.
        All setpoints must be returned because the compensation must know the value of all axis setpoints.
        """
        setpoints = {alias: self.driver.get_scaled_axis_setpoint(alias) for alias in self.get_axis_aliases()}

        if self.joint_calibration_model is not None:
            setpoints = self.joint_calibration_model.compensate_joint_value_fk(setpoints)

        return setpoints

    def homing_sequence(self):
        return [
            ("homeall", []),
        ]

    def specs(self):
        pass

    def set_specs(self, axis_specs):
        pass
        
    def get_axis_spec_by_alias(self, alias):
        """
        Get axis specification by axis alias.
        :param alias: Alias such as "x".
        :return: Axis specification dictionary or None if alias is not found.
        """
        for spec in self.specs().values():
            if spec["alias"] == alias:
                return spec

        return None

    def get_axis_aliases(self):
        """
        Get a list of axis aliases in the kinematic specs.
        :return: List e.g. ["x", "y"].
        """
        return [spec["alias"] for spec in self.specs().values()]

    def check_dynamic_position_limits(self, positions):
        """
        Check that dynamically changing axis position limits are not violated. For example, minimum or maximum allowed
        joint position may depend on the current configuration of the robot, i.e. currently attached tips, tools etc.
        Throw exception if limits are violated.
        :param positions: Dictionary of joint positions.
        :return: None
        """
        pass

    # default arc_r to be used
    # zero will result in instant rotations in Program, good for 3-axis robot
    def arc_r(self, toolframe=None, kinematic_name=None):
        return 0

    def pre_force_mode_change(self, axis, mode):
        """
        Method that is called before axis force mode changes.
        :param axis: Axis name e.g. "x".
        :param mode: Mode that is about to be changed.
        """

        # By default do nothing. Kinematics can override.
        pass


def append_post_homing_move(homing_sequence, axis_specs):
    """
    Append post-homing move commands to homing sequence according to given axis spec.
    :param homing_sequence: Homing sequence. Post-homing move commands are appended to this list.
    :param axis_specs: Axis spec.
    """
    if axis_specs is None:
        return

    for spec in axis_specs.values():
        if "post_homing_move" in spec:
            homing_sequence.append(("move", {spec["alias"]: spec["post_homing_move"]}))
