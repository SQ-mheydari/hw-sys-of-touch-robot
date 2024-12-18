import collections
import logging
import sys

import tntserver.Nodes.TnT as TnT
from tntserver.Nodes.Node import *
from tntserver.drivers.robots import golden_program
from tntserver.drivers.robots.golden_program import AxisPrimitive
from tntserver.Nodes.TnT.Tool import Tool
from tntserver.Nodes.TnT.Tools import ToolChanger, SmartToolManager
from tntserver.Nodes.TnT.Tip import Tip
from tntserver.Nodes.TnT.Tips import TipChanger, SmartTipManager
from tntserver.Nodes.TnT.PhysicalButton import PhysicalButton
from tntserver.Nodes.Mount import Mount
from tntserver.Nodes.TnT.Workspace import get_node_workspace

from tntserver.drivers.robots.goldenmov import GoldenMov, AxisLimitError
from tntserver.drivers.robots.goldenmov.open_loop_force import OpenLoopForce
from tntserver.drivers.robots.goldenmov.opto_std_force import OptoStdForce
from tntserver.drivers.robots.goldenmov.flexure_force import FlexureForce

log = logging.getLogger(__name__)


class Robot(Node):
    """
    TnT™ Compatible robot resource
    Should work together with
    - TnT Sequencer
    - TnT Positioning Tool
    """

    def __init__(self, name):
        super().__init__(name)

        # Limit maximum robot effector velocity and acceleration.
        # These are general safety limits.
        self.max_robot_velocity = 250
        self.max_robot_acceleration = 100000

        self.robot_velocity = 20
        self.robot_acceleration = 20
        self._robot_override = None
        self.driver = None

        # Mount node mount_point that represents the active kinematics.
        # Robot node can have multiple Mount nodes as children.
        # This value is used to indicate the default / active kinematic.
        self._kinematic_name = "tool1"

        # Name of kinematic to use by default if no kinematic is specified.
        self.default_kinematic_name = "tool1"

        self.program = None

        # Tip changer is an object that defines how tips are changed. See TipChanger class.
        self._tip_changer = TipChanger(self)

        self._tool_changer = ToolChanger(self)

        # Calibration data used by kinematics.
        self._calibration_data = {}

        self._smart_tip_manager = None
        self._smart_tool_manager = None

        # Robot may use varying force implementations.
        self._force_driver = None

        self._force_calibration_table = {}

        self._camera_capture_positions = {}

        # Typically a DUT is not that much tilted wrt the robot base plate. With more dexterous robots (like 6-axes etc)
        # this value can be increased
        self.maximum_dut_tilt_angle = 15.0

        # Sensor used for HW level triggering, e.g., for first contact latency and watchdog.
        self._triggersensor = None

    @property
    @private
    def force_driver(self):
        return self._force_driver

    def _init_goldenmov(self, **kwargs):
        host = kwargs["host"]
        port = kwargs["port"]
        model = str(kwargs["model"])
        simulator = kwargs.get("simulator", False)
        axis_specs = kwargs.get("axis_specs", None)
        position_limits = kwargs.get("position_limits", None)
        api_name = kwargs.get("api_name", "optomotion")
        visualize = kwargs.get("visualize", True)
        restore_axis_configs = kwargs.get("restore_axis_configs", True)
        home_axes = kwargs.get("home_axes", True)
        kinematic_parameters = kwargs.get("kinematic_parameters", None)

        if "program_arguments" in kwargs:
            visualize = kwargs["program_arguments"].visual_simulation

        driver_log_level = kwargs.get("driver_log_level", 2)

        try:
            self.driver = GoldenMov(self, host, port, model, simulator, visualize,
                                    log_level=driver_log_level, axis_specs=axis_specs, api_name=api_name,
                                    position_limits=position_limits, restore_axis_configs=restore_axis_configs,
                                    home_axes=home_axes, kinematic_parameters=kinematic_parameters)

        except Exception as e:
            log.error("error while initializing robot driver")
            log.exception(e)
            sys.exit(0)

        #
        # This is THE move program
        # all robot movement, gestures done with this one instance
        # do not create other instances.
        #
        self.program = golden_program.Program(self)

        smart_tip_config = kwargs.get("smart_tip", None)

        if smart_tip_config is not None:
            self._smart_tip_manager = SmartTipManager(smart_tip_config.get("mode", "normal"),
                                                      smart_tip_config.get("addresses"),
                                                      comm=self.driver._comm,
                                                      ip_address=smart_tip_config.get("ip_address", None),
                                                      id_chip_address=smart_tip_config.get("id_chip_address", 7),
                                                      hot_changing=smart_tip_config.get("hot_changing", False))

        smart_tool_config = kwargs.get("smart_tool", None)

        if smart_tool_config is not None:
            self._smart_tool_manager = SmartToolManager(smart_tool_config.get("mode", "normal"),
                                                      smart_tool_config.get("addresses"),
                                                      comm=self.driver._comm,
                                                      ip_address=smart_tool_config.get("ip_address", None),
                                                      id_chip_address=smart_tool_config.get("id_chip_address", 7),
                                                      hot_changing=smart_tool_config.get("hot_changing", False))

    def _init_force_driver(self, **kwargs):
        driver_name = kwargs.get("force_driver", None)

        if driver_name is None:
            return

        force_driver_parameters = kwargs.get("force_parameters", {})

        if driver_name == "open_loop_force":
            log.debug("Initializing open loop force.")

            self._force_driver = OpenLoopForce(self, force_driver_parameters)
        elif driver_name == "opto_std_force":
            log.debug("Initializing OptoStandard force.")

            # Make sure that force_parameters is given for opto_std_force.
            # This is mostly to detect incompatible configuration.
            if "force_parameters" not in kwargs:
                raise Exception("Could not initialize force: 'force_parameters' not in Robot arguments.")

            self._force_driver = OptoStdForce(self, force_driver_parameters)
        elif driver_name == "flexure_force":
            log.debug("Initializing flexure force.")

            self._force_driver = FlexureForce(self, force_driver_parameters)
        else:
            raise Exception("Unknown force driver '{}'.".format(driver_name))

        # Set force calibration table.
        self._force_driver.set_force_calibration_table(self._force_calibration_table)
 
    def _init(self, driver: str, **kwargs):
        robots = {
            "golden": self._init_goldenmov,
            }
        robot_init = robots.get(driver.lower(), None)
        if robot_init is not None:
            robot_init(**kwargs)
        else:
            raise Exception("Robot driver not initialized with proper type")

        # For safety, Robot speed and acceleration are always set to default values given as arguments.
        if "speed" in kwargs:
            self.robot_velocity = min(float(kwargs["speed"]), self.max_robot_velocity)
        if "acceleration" in kwargs:
            self.robot_acceleration = min(float(kwargs["acceleration"]), self.max_robot_acceleration)

        log.debug("Robot velocity={} acceleration={}".format(self.robot_velocity, self.robot_acceleration))

        self._tip_changer.max_tip_change_speed = kwargs.get("max_tip_change_speed", 100.0)
        self._tip_changer.max_tip_change_acceleration = kwargs.get("max_tip_change_acceleration", 300.0)

        # Positions where robot moves when a camera takes an image.
        # Example content: {"Camera1": {"x": 0, "y": 0, "z": 0}}.
        self._camera_capture_positions = kwargs.get("camera_capture_positions", {})

        self._init_force_driver(**kwargs)

        if kwargs.get('orient_after_homing', False):
            self.orient_after_homing()

        triggersensor = kwargs.get('triggersensor', None)

        if triggersensor is not None:
            self._triggersensor = Node.find(triggersensor)

    @property
    @private
    def triggersensor(self):
        """
        Trigger sensor object.
        """
        return self._triggersensor

    def orient_after_homing(self):
        """
        Changes robot orientation such that the orientation is identity wrt the robot base frame. This is mainly useful
        if due to robot calibration at joint home positions the robot orientation is slightly different from identity
        (matrix).
        :return:
        """
        try:
            # Change robot orientation such that there is no rotation wrt workspace reference frame after homing
            f0 = self.effective_frame

            # Replace orientation part
            f0[0:3, 0:3] = np.matrix([[-1, 0, 0],
                                      [0, 1, 0],
                                      [0, 0, -1]])
            self.effective_frame = f0

        # It may be that joint limits don't allow us to do this after homing. Log the failure if this is the case.
        except AxisLimitError:
            log.error("Failed to change robot orientation from home position. Check axis position limit settings.")

    def effective_pose(self):
        """
        :return: The effective pose of the robot.
        """
        return robotmath.frame_to_pose(self.effective_frame)

    @property
    def kinematic_name(self):
        """
        Name of the active kinematic.
        """
        return self._kinematic_name

    @kinematic_name.setter
    def kinematic_name(self, value):
        # TODO: Check that value is recognized as existing kinematic name.
        assert isinstance(value, str)
        self._kinematic_name = value

    @json_out
    def get_kinematic_name(self):
        """
        Get name of the active kinematic.
        :return:
        """
        return self.kinematic_name

    @json_out
    def put_kinematic_name(self, kinematic_name):
        """
        Set the active kinematic.
        :param kinematic_name: Name of the active kinematic.
        :return:
        """
        self.kinematic_name = kinematic_name

    @json_out
    def put_active_finger(self, finger_id: int):
        """
        Set active finger.
        Kinematics are applied to the active finger so that it is possible
        to command either of the two fingers to specified pose.
        :param finger_id: ID of finger to set active. 0=axial finger, 1=separated finger.
        """
        # TODO: This is 2-finger TPPT compatibility but overlaps with put_kinematic_name().
        assert isinstance(finger_id, int)
        self.kinematic_name = ["tool1", "tool2"][finger_id]

    @json_out
    def get_active_finger(self):
        """
        Get active finger.
        :return: Active finger ID.
        """

        # TODO: This is 2-finger TPPT compatibility but potentially overlaps with kinematic_name property.
        return {"tool1": 0, "tool2": 1}[self.kinematic_name]

    @json_out
    def put_home(self):
        """
        Commands the robot to go into home position.
        """
        self.driver.home()
        self.program.reset()

    @json_out
    def put_reset_error(self):
        """
        Resets robot error state.
        """
        self.driver.reset_error()

    @json_out
    def get_reset_error(self):
        self.driver.reset_error()

    @json_out
    def get_errors(self):
        return {"errors": self.driver.error}

    #
    # pose functions
    #

    @json_out
    def get_effective_pose(self, context: str, kinematic_name=None):
        """
        Current robot effective Pose in given context
        :param context: context node name as string
        :return: pose as 4x4 matrix
        """
        if context is not None:
            target_context = Node.find(context)
        else:
            target_context = self.parent

        if kinematic_name is None:
            kinematic_name = self.kinematic_name

        effective_frame = self.driver.frame(tool=self.tool_frame(kinematic_name), kinematic_name=kinematic_name)

        frame = robotmath.translate(effective_frame, self.object_parent, target_context)

        pose = robotmath.frame_to_pose(frame)

        return pose.tolist()

    def set_effective_pose(self, context: Node, pose, kinematic_name=None):
        """
        Moves robot effector to given Pose
        Pose is a 4x4 matrix where rotation part is identity matrix if Effector rotation is zero
            ( if user selects zero Tilt & Azimuth from UI )
        :param context: context as Node
        :param pose: target pose as 4x4 matrix
        :return:
        """
        pose = np.matrix(pose)
        assert pose.shape == (4, 4)
        frame = robotmath.pose_to_frame(pose)
        self.move_frame(frame, context, kinematic_name=kinematic_name)

    @json_out
    def put_effective_pose(self, context: str, pose, kinematic_name=None):
        """
        Moves robot effector to given Pose matrix
        :param context: name of the context Node
        :param pose: target pose 4x4 matrix
        :return: status
        """
        pose = np.matrix(pose)
        context_node = Node.find(context)
        self.set_effective_pose(context_node, pose, kinematic_name=kinematic_name)

        r = {"status": self.driver.error if self.driver.error else "ok"}
        return r

    def set_axis_position(self, axis: str, value, kinematic_name=None):
        if kinematic_name is None:
            kinematic_name = self.kinematic_name

        speed = self.robot_velocity
        acceleration = self.robot_acceleration

        prg = self.program
        prg.begin(self.object_parent, self.tool_frame(kinematic_name), kinematic_name=kinematic_name)
        prg.set_speed(speed, acceleration)
        p = AxisPrimitive(axis)
        p.target_value = value
        prg.move(p)
        prg.run()

    def axis_position(self, axis: str):
        p = self.driver.position(self.tool_frame(), kinematic_name=self.kinematic_name)
        position = getattr(p, axis)
        return position

    @json_out
    def get_joint_position(self, joint):
        return self.joint_position(joint)

    def joint_limits(self):
        return self.driver.get_joint_limits()

    @json_out
    def get_joint_limits(self):
        """
        Get joint movement limits.
        :return: Joint limits as dict {"x": (x_min, x_max), "y": (y_min, y_max)}.
        """
        return self.joint_limits()

    def joint_status(self):
        return self.driver.get_joint_status()

    @json_out
    def get_joint_status(self):
        """
        Get status of joints.
        :return: Status of each join as nested dict {"x": {"enabled": True}, "y": {"enabled": False}}.
        """
        return self.joint_status()

    def enable_joints(self, joints):
        self.driver.enable_axes(joints)

    @json_out
    def put_enable_joints(self, joints):
        """
        Enable joints.
        :param joints: List of joints to enable e.g. {"x", "y"}.
        """
        self.enable_joints(joints)

    def disable_joints(self, joints):
        self.driver.disable_axes(joints)

    @json_out
    def put_disable_joints(self, joints):
        """
        Disable joints.
        :param joints: List of joints to disable e.g. {"x", "y"}.
        """
        self.disable_joints(joints)

    def move_frame(self, frame, context: Node, kinematic_name: str=None, tool_frame=None, speed: float=None, acceleration: float=None):
        """
        Move robot's effective frame to given frame in given context.
        :param frame: target frame
        :param context: context of target frame
        :param kinematic_name: Name of kinematic to use in movement.
        :param speed: Robot speed to use in the movement. If None, then current robot speed is used.
        :param acceleration: Robot acceleration to use in the movement. If None, then current robot acceleration is used.
        """

        assert frame.shape == (4, 4)

        if speed is None:
            speed = self.robot_velocity

        if acceleration is None:
            acceleration = self.robot_acceleration

        if kinematic_name is None:
            kinematic_name = self.kinematic_name

        if tool_frame is None:
            tool_frame = self.tool_frame(kinematic_name)

        prg = self.program
        prg.begin(context, tool_frame, kinematic_name=kinematic_name)
        prg.set_speed(speed, acceleration)
        prg.move(prg.point(robotmath.frame_to_pose(frame)))
        prg.run()

    @property
    @private  # set invisible to configuration file
    def effective_frame(self):
        """
        Effective frame is the last frame in the robot transform hierarchy i.e.
        if there is a tip attached, it corresponds to the touch surface of the tip.
        """

        m = self.driver.frame(tool=self.tool_frame(), kinematic_name=self.kinematic_name)
        return m

    @effective_frame.setter
    def effective_frame(self, frame):
        self.move_frame(frame, context=self.object_parent)

    @json_out
    def put_effective_frame(self, context: str, frame, kinematic_name=None):
        """
        Moves robot's effector to given frame.
        :param context: name of the context Node
        :param frame: target frame 4x4 matrix
        :return:
        """
        frame = np.matrix(frame)

        context_node = Node.find(context)
        self.move_frame(frame, context_node, kinematic_name=kinematic_name)

        r = {}
        r["status"] = self.driver.error if self.driver.error else "ok"
        return r

    @json_out
    def get_effective_frame(self, context: str, kinematic_name=None):
        """
        Current robot effective frame in given context
        :param context: context node name as string
        :return: pose as 4x4 matrix
        """
        if context is not None:
            target_context = Node.find(context)
        else:
            target_context = self.parent

        if kinematic_name is None:
            kinematic_name = self.kinematic_name

        effective_frame = self.driver.frame(tool=self.tool_frame(kinematic_name), kinematic_name=kinematic_name)

        frame = robotmath.translate(effective_frame, self.object_parent, target_context)

        return frame.tolist()

    def put_position(self, context, **kwargs):
        """
        Moves robot's effector to given position.
        This is legacy TnT API support.
        """

        self._move(context=context, **kwargs)
        return self.get_position(context)

    def post_position(self, context, **kwargs):
        """
        Moves robot's effector to given position.
        This is legacy TnT API support.
        """

        self._move(context=context, **kwargs)
        return self.get_position(context)

    # No @json_out because get_position() has this.
    def put_move(self, x, y, z, tilt=None, azimuth=None, context="tnt"):
        """
        Moves robot into a given location using a linear motion. Coordinates and angles are interpreted in given context.
        Values tilt and azimuth are taken from Euler angles for global static y and z axes (in selected context)
        that are applied in order y, z. Tilt is angle around y-axis and azimuth is negative angle around z-axis.
        :param x: Target x coordinate.
        :param y: Target y coordinate.
        :param z: Target z coordinate.
        :param tilt: Euler angle for static y-axis (default: 0) in selected context.
        :param azimuth: Negative Euler angle for static z-axis (default: 0) in selected context.
        :param context: Name of context where coordinates and angles are interpreted.
        """

        self._move(x=x, y=y, z=z, tilt=tilt, azimuth=azimuth, context=context)

        return self.get_position(context)

    def move_relative(self, x=None, y=None, z=None, tilt=None, azimuth=None):
        position = self._position_info(self.object_parent)
        position = position["position"]

        if x is not None:
            position["x"] += x
        if y is not None:
            position["y"] += y
        if z is not None:
            position["z"] += z
        if tilt is not None:
            position["tilt"] += tilt
        if azimuth is not None:
            position["azimuth"] += azimuth

        self._move(x=position["x"], y=position["y"], z=position["z"], tilt=position["tilt"],
                   azimuth=position["azimuth"])

    @json_out
    def put_move_relative(self, x=None, y=None, z=None, tilt=None, azimuth=None):
        """
        Moves robot axes by specified distance using linear motion.
        Parameters are relative to current position and can hence be negative or positive.

        :param x: Relative x axis movement.
        :param y: Relative y axis movement.
        :param z: Relative z axis movement.
        :param tilt: Relative tilt axis movement.
        :param azimuth: Relative azimuth axis movement.
        """

        self.move_relative(x, y, z, tilt, azimuth)

    @json_out
    def get_position(self, context: str="tnt", details=False, kinematic_name=None):
        """
        Returns the current robot position in given context.
        :param context: Name of context where to evaluate the position.
        :param details: Return detailed position info.
        :param kinematic_name: Name of kinematic that corresponds to the position.
        :return: Dictionary with keys 'position' and 'status'.
        """

        if context is not None:
            target_context = Node.find(context)
        else:
            target_context = self.object_parent

        result = self._position_info(target_context, kinematic_name)

        if not details:
            if 'head' in result:
                del result['head']
            if 'frame' in result:
                del result['frame']

        return result

    def _move(self, x: float, y: float, z: float, x_roll: float = None, y_roll: float = None, z_roll: float = None,
              tilt: float = None, azimuth: float = None, spin: float = None, speed: float = None,
              acceleration: float = None, context: str = None, **kwargs):
        """
        Moves the robot effector to given position.
        """

        assert np.isreal(x)
        assert np.isreal(y)
        assert np.isreal(z)

        if context is not None:
            context_node = Node.find(context)
        else:
            context_node = self.object_parent

        if (x_roll is not None or y_roll is not None or z_roll is not None) and \
                (tilt is not None or azimuth is not None or spin is not None):

            # TODO: Deliver sensible error message as response!
            raise ValueError("X, Y or Z roll parameters cannot be used with tilt or azimuth parameters.")

        pose = None
        if x_roll is not None or y_roll is not None or z_roll is not None:
            assert np.isreal(x_roll)
            assert np.isreal(y_roll)
            assert np.isreal(z_roll)
            if x_roll is None:
                x_roll = 0
            if y_roll is None:
                y_roll = 0
            if z_roll is None:
                z_roll = 0
            x_roll = float(x_roll)
            y_roll = float(y_roll)
            z_roll = float(z_roll)
            pose = robotmath.xyz_euler_to_frame(x, y, z, float(x_roll), float(y_roll), float(z_roll))

        if tilt is not None or azimuth is not None or spin is not None:
            assert np.isreal(tilt)
            assert np.isreal(azimuth)
            assert np.isreal(spin)
            if tilt is None:
                tilt = 0
            if azimuth is None:
                azimuth = 0
            if spin is None:
                spin = 0
            pose = robotmath.xyz_euler_to_frame(x, y, z, spin, tilt, -azimuth, "szyz")

        if pose is None:
            pose = robotmath.xyz_to_frame(x, y, z)
        else:
            pose = pose.copy()

        frame = robotmath.pose_to_frame(pose)

        # move
        self.move_frame(frame, context=context_node, speed=speed, acceleration=acceleration)

    def _position_info(self, target_context, kinematic_name=None):
        """
        Get effective, head, tool and tip positions in given context.
        Effective frame is the last frame in the whole hierarchy so it is affected by whether
        a tool or a tip is attached or not.
        :param target_context: Context where the positions are expressed.
        :param kinematic_name: Name of kinematic that corresponds to the position.
        :return: Dictionary containing the various positions.
        """

        if kinematic_name is None:
            kinematic_name = self.kinematic_name

        effective_frame = self.driver.frame(tool=self.tool_frame(kinematic_name), kinematic_name=kinematic_name)

        # Robot's effective frame in target context.
        frame = robotmath.translate(effective_frame, self.object_parent, target_context)

        tool_node = self.find_mount(kinematic_name).tool

        try:
            tool_frame = tool_node.frame
        except AttributeError:
            tool_frame = np.matrix(np.eye(4))

        tip_node = tool_node.tip if (tool_node is not None and type(tool_node) is Tool) else None

        try:
            tip_frame = tip_node.frame
        except AttributeError:
            tip_frame = None

        if tip_frame is not None:
            # If there is a tip, then the tip total frame is the effective frame
            f_tip = frame

            # frame: effective -> context
            # tip_frame: effective -> tool
            # f_tool: tool -> context
            f_tool = frame * tip_frame.I

            # tool_frame: tool -> head
            # f_head: head -> context
            f_head = f_tool * tool_frame.I

        elif tool_frame is not None:
            f_tip = None

            # Because there is no tip, tool frame is the effective frame.
            # Hence f_tool: tool -> context
            f_tool = frame

            # tool_frame: tool -> head
            # f_head: head -> context
            f_head = frame * tool_frame.I

        else:
            # In case there is neither tool nor tip, head is the effective frame.
            f_head = frame
            f_tip = None
            f_tool = None

        # Convert frames from server to client conventions.
        pose = robotmath.frame_to_pose(frame)
        pose_head = robotmath.frame_to_pose(f_head)
        pose_tool = robotmath.frame_to_pose(f_tool) if f_tool is not None else None
        pose_tip = robotmath.frame_to_pose(f_tip) if f_tip is not None else None

        r = collections.OrderedDict()

        r["position"] = TnT.frame_to_tnt_tilt_azimuth_pose(pose)
        r["effective"] = TnT.frame_to_tnt_tilt_azimuth_pose(pose)
        r["head"] = TnT.frame_to_tnt_tilt_azimuth_pose(pose_head)
        r["head_pose"] = pose_head.tolist()

        # Tool pose is used to e.g. position tip slots.
        r["tool_pose"] = pose_tool.tolist() if pose_tool is not None else None

        if tool_node is not None:
            r[tool_node.name] = TnT.frame_to_tnt_tilt_azimuth_pose(pose_tool)

        if tip_node is not None:
            r[tip_node.name] = TnT.frame_to_tnt_tilt_azimuth_pose(pose_tip)

        r["frame"] = frame.tolist()
        r["status"] = self.driver.error if self.driver.error else "ok"
        try:
            # joint values are used for testing kinematics integration with the server
            # TODO: verify if this is just being overly cautious
            r["joints"] = self.driver.get_joint_positions()
        except Exception as e:
            log.exception(e)

        return r

    def set_speed(self, speed: float, acceleration: float = None):
        if speed is not None:
            assert np.isreal(speed)

            if speed <= 0:
                raise Exception("Attempting to set robot velocity to non-positive value {}. Velocity not set.".
                                format(speed))

            self.robot_velocity = min(speed, self.max_robot_velocity)

            if speed > self.max_robot_velocity:
                log.warning("Attempting to set robot velocity to {}. Clamped to maximum velocity {}.".
                            format(speed, self.max_robot_velocity))

            log.info("Robot %s default velocity -> %f", self.name, self.robot_velocity)
        if acceleration is not None:
            assert np.isreal(acceleration)

            if acceleration <= 0:
                raise Exception("Attempting to set robot acceleration to non-positive value {}. Acceleration not set.".
                                format(acceleration))

            self.robot_acceleration = min(acceleration, self.max_robot_acceleration)

            if acceleration > self.max_robot_acceleration:
                log.warning("Attempting to set robot acceleration to {}. Clamped to maximum acceleration {}.".
                            format(acceleration, self.max_robot_acceleration))

            log.info("Robot %s default acceleration -> %f", self.name, self.robot_acceleration)

        self.driver.speed = self.robot_velocity
        self.driver.acceleration = self.robot_acceleration

    @json_out
    def put_speed(self, speed: float, acceleration: float = None, override: float = None):
        """
        Set robot speed and acceleration.
        :param speed: Linear movement speed in mm/s.
        :param acceleration: Robot acceleration in mm/s^2.
        :param override: Not used. DEPRECATED.
        """
        self.set_speed(speed, acceleration)

    @json_out
    def get_speed(self):
        """
        Returns robot's current speed and acceleration.
        :return: Dictionary with keys 'speed' and 'acceleration'.
        """
        return {"speed": self.robot_velocity, "acceleration": self.robot_acceleration}

    @json_out
    def get_has_tool_tip(self):
        """
        This is legacy TnT API support.
        """
        self.match_attached_tips_to_smart_tips()

        log.warning("DEPRECATED. Use get_attached_tips() instead.")
        tool = self.active_tool

        if tool is None:
            return {"tip": None, "tool": None}

        tip = tool.tip

        return {"tip": tip.name if tip is not None else None, "tool": tool.name}

    def attached_tips(self):
        """
        Get names of tips attached to the robot.
        :return: Dictionary where key is tool name and value is name of tip attached to that tool. If no tip is
        attached then value is None.
        """
        result = {}

        def find_tips_recursively(node):
            if type(node) is Mount:
                object_children = list(node.object_children.values())

                if len(object_children) > 0 and type(object_children[0]) is Tool:
                    tool = object_children[0]

                    result[tool.name] = None if tool.tip is None else tool.tip.name

            for child in node.object_children.values():
                find_tips_recursively(child)

        find_tips_recursively(self)

        return result

    @json_out
    def get_attached_tips(self):
        """
        Get names of tips attached to the robot.
        :return: Dictionary where key is tool name and value is name of tip attached to that tool. If no tip is
        attached then value is None.
        """
        self.match_attached_tips_to_smart_tips()

        return self.attached_tips()

    def attached_tools(self):
        """
        Get names of tools attached to the robot.
        :return: Dictionary where key is mount name and value is name of tool attached to that mount. If no tool is
        attached then value is None.
        """
        result = {}

        def find_tools_recursively(node):
            if type(node) is Mount:
                object_children = list(node.object_children.values())

                result[node.name] = None

                if len(object_children) > 0 and type(object_children[0]) is Tool:
                    tool = object_children[0]

                    result[node.name] = None if tool is None else tool.name

            for child in node.object_children.values():
                find_tools_recursively(child)

        find_tools_recursively(self)

        return result

    @json_out
    def get_attached_tools(self):
        """
        Get names of tools attached to the robot.
        :return: Dictionary where key is mount name and value is name of tool attached to that mount. If no tools is
        attached then value is None.
        """
        self.match_attached_tools_to_smart_tools()

        return self.attached_tools()

    @json_out
    def get_bounds(self):
        """
        :return: working area bounds with current tool and angles
        """
        return self.bounds()

    def bounds(self):
        """
        :return: working area bounds with current kinematic, tool frame and angles
        """
        return self.driver.bounds(tool=self.tool_frame(), kinematic_name=self.kinematic_name)

    def match_attached_tips_to_smart_tips(self):
        """
        Match TnT tip attach status according to currently attached smart tip HW.
        This has only effect if "hot changing" has been enabled for smart tip manager.
        """
        if self._smart_tip_manager is None:
            return

        if not self._smart_tip_manager.hot_changing:
            return

        tip_data = {}

        # Loop through each tool that can have a tip attached.
        for tool_name in self._smart_tip_manager.names:
            tip_data[tool_name] = None

            try:
                data = self._smart_tip_manager.read_memory_device_data(tool_name)
                tip_data[tool_name] = data
            except:
                raise Exception("Smart tip is not attached while hot changing is enabled. Please attach smart tip.")

            smart_tip_name = data["name"]

            if self.attached_tips()[tool_name] != smart_tip_name:
                self._tip_changer.detach_tip(tool_name, detach_manually=True)

                log.info("Attaching tip {} to tool {} according to currently attached smart tip.".
                         format(smart_tip_name, tool_name))

                self._tip_changer.attach_tip(smart_tip_name, tool_name, attach_manually=True)

        return tip_data

    def match_attached_tools_to_smart_tools(self):
        """
        Match TnT tool attach status according to currently attached smart tool HW.
        This has only effect if "hot changing" has been enabled for smart tool manager.
        :return: Dict of currently attached tools e.g. {"tool1_mount": "tool1"}.
        """
        if self._smart_tool_manager is None:
            return

        if not self._smart_tool_manager.hot_changing:
            return

        tool_data = {}

        # Loop through each mount that can have a tool attached.
        for mount_name in self._smart_tool_manager.names:
            tool_data[mount_name] = None

            try:
                data = self._smart_tool_manager.read_memory_device_data(mount_name)
                tool_data[mount_name] = data
            except:
                raise Exception("Smart tool is not attached while hot changing is enabled. Please attach smart tool.")

            smart_tool_name = data["name"]

            attached_tools = self.attached_tools()

            if attached_tools[mount_name] != smart_tool_name:
                if attached_tools[mount_name] is not None:
                    self._tool_changer.detach_tool(mount_name)

                log.info("Attaching tool {} to mount {} according to currently attached smart tool.".
                         format(smart_tool_name, mount_name))

                self._tool_changer.attach_tool(smart_tool_name, mount_name)

        return tool_data

    def tool_frame(self, kinematic_name=None):
        """
        Calculate tool frame for given kinematic name.
        Kinematic name is used to find correct Mount node child of robot. Tool frame is then the
        total transform from that Mount node until the end of the hierarchy. This hierarchy can not branch or
        the correct branch must somehow be specified by the nodes that are traversed.
        :param kinematic_name: Name of kinematic under which the tool frame is calculated. If None, then active kinematic is used.
        :return: Total tool frame.
        """

        if kinematic_name is None:
            kinematic_name = self.kinematic_name

        node = self.find_mount(kinematic_name)

        if node is None:
            raise Exception("Tool frame for kinematic '{}' not found from {}".format(kinematic_name, self.name))

        # Make sure the tool frame computation is done using correct tool.
        if self._smart_tool_manager is not None:
            tools = Node.find_from(get_node_workspace(self), "tools")

            tool_data = self.match_attached_tools_to_smart_tools()

            self._smart_tool_manager.verify_attached_tools(self.attached_tools(), tools, tool_data)

        # Make sure the tool frame computation is done using correct tips.
        if self._smart_tip_manager is not None:
            tips = Node.find_from(get_node_workspace(self), "tips")

            tip_data = self.match_attached_tips_to_smart_tips()

            self._smart_tip_manager.verify_attached_tips(self.attached_tips(), tips, tip_data)

        tool_frame = robotmath.identity_frame()

        # Traverse child nodes under mount node to compute total tool frame.
        # Assumes that each child has only one child so that the chain is unique.
        while node is not None:
            if len(node.object_children.keys()) == 0:
                break

            assert len(node.object_children.keys()) == 1

            node = list(node.object_children.values())[0]

            # Chain node's frame as part of the total tool frame.
            # This should work even if another robot is encountered.
            tool_frame = tool_frame * node.frame

        return tool_frame

    def find_mount(self, kinematic_name: str):
        """
        Find Mount node that has given kinematic name (mount point) and is part of
        transform hierarchy under robot.
        :param kinematic_name: Name of the kinematic.
        :return: Mount node if found, otherwise None.
        """

        def find_mount_recursively(node, kinematic_name):
            if type(node) is Mount and node.mount_point == kinematic_name:
                return node

            for child in node.object_children.values():
                ret = find_mount_recursively(child, kinematic_name)

                if ret is not None:
                    return ret

        return find_mount_recursively(self, kinematic_name)

    @property
    @private
    def active_tool(self):
        """
        Active tool is Tool node under the active kinematic Mount node.
        Note that it is possible that there are other Tool nodes or other node types as children
        of the active tool. This property is handy in the most typical case where the node hierarchy is something like
        Robot -> Mount1 (active kinematic) -> Tool1 (active tool) -> Tip1 (active tip)
              -> Mount2 -> Tool2 -> Tip2
        where one kinematic is active at a time.
        """

        mount = self.find_mount(self.kinematic_name)

        return mount.tool

    @property
    @private
    def active_tip(self):
        """
        Active tip is Tip node under the active Tool node.
        See the description of active_tool for more info.
        """
        self.match_attached_tips_to_smart_tips()

        tool_node = self.active_tool

        if tool_node is None or type(tool_node) is not Tool:
            return None

        return tool_node.tip

    @json_out
    def put_attach_tip(self, tip_id: str, tool_name="tool1", finger_id=None, attach_manually=False):
        """
        Attach tip to specific tool.
        :param tip_id: Name of tip node to attach.
        :param tool_name: Name of tool node where tip is attached to. Must be a child of Mount node.
        :param finger_id: Integer value (0 or 1) to select target finger. TODO: This is 2-finger TPPT compatibility.
        :param attach_manually: If tip is to be attached manually and not with the tip changer.
        """
        if self._tip_changer is None:
            raise NodeException("Robot does not have tip changing functionality")

        if finger_id is None and tool_name is None:
            raise ValueError("Either tool_name or finger_id must be given.")

        if finger_id is not None:
            tool_name = ["tool1", "tool2"][finger_id]

        self._tip_changer.attach_tip(tip_id, tool_name, attach_manually)

        tip = self.active_tip

        return {"tip": None if tip is None else tip.name}

    @json_out
    def put_detach_tip(self, tool_name="tool1", finger_id=None, detach_manually=False):
        """
        Detach tip from robot finger if one is attached.
        :param tool_name: Name of tool node where tip is detached from. Must be a child of Mount node.
        :param finger_id: ID of finger.
        :param detach_manually: If tip is to be detached manually and not with the tip changer.
        :return: Name of the tip that was detached as dict {"tip": tip_name}.
        """
        if self._tip_changer is None:
            raise NodeException("Robot does not have tip changing functionality")

        if finger_id is None and tool_name is None:
            raise ValueError("Either tool_name or finger_id must be given.")

        if finger_id is not None:
            tool_name = ["tool1", "tool2"][finger_id]

        self._tip_changer.detach_tip(tool_name, detach_manually)

        tip = self.active_tip

        return {"tip": None if tip is None else tip.name}

    @json_out
    def put_change_tip(self, tip: str, finger_id=0, attach_manually=False):
        """
        Commands robot to change new tool tip from tip holder.
        DEPRECATED: This is 2-finger TPPT compatibility and does the same as put_attach_tip().
        :param tip: Name of tip to make the current tip.
        :param finger_id: ID of finger where to change tip to. Ignored if robot has only one tool.
        :param attach_manually: If tip is to be attached manually and not with the tip changer.
        :return: Name of the tip that was attached as dict {"tip": tip_name}
        """
        if self._tip_changer is None:
            raise NodeException("Robot does not have tip changing functionality")

        # Get list of attached tool names.
        attached_tools = self.attached_tools()
        attached_tools = [tool for tool in attached_tools.values() if tool is not None]

        if len(attached_tools) > 1:
            tool_name = ["tool1", "tool2"][finger_id]
        else:
            # Get the unique attached tool name.
            tool_name = attached_tools[0]

        self._tip_changer.attach_tip(tip, tool_name, attach_manually)

        tip_node = self.active_tip

        return {"tip": None if tip_node is None else tip_node.name}

    @json_out
    def put_attach_tool(self, tool_name: str, mount_name: str = None):
        """
        Attach tool to robot.
        :param tool_name: Name of tool node to attach.
        :param mount_name: Name of robot mount where to attach the tool.
        """
        if self._tool_changer is None:
            raise NodeException("Robot does not have tool changing functionality")

        if mount_name is None:
            mount_name = "tool1_mount"

        self._tool_changer.attach_tool(tool_name, mount_name)

        return {mount_name: tool_name}

    @json_out
    def put_detach_tool(self, mount_name: str = None):
        """
        Detach tool from robot finger if one is attached.
        :param mount_name: Name of robot mount where to detach tool from.
        """
        if self._tool_changer is None:
            raise NodeException("Robot does not have tool changing functionality")

        if mount_name is None:
            mount_name = "tool1_mount"

        self._tool_changer.detach_tool(mount_name)

        return {mount_name: None}

    def has_multifinger(self):
        """
        :return: True if robot has multifinger tip attached.
        """

        def has_multifinger_recursive(node):
            if type(node) == Tip and node.is_multifinger:
                return True

            for child in node.object_children.values():
                if has_multifinger_recursive(child):
                    return True

        return has_multifinger_recursive(self)

    @json_out
    def put_plot_recorded_axes(self):
        """
        Plot previously recorded axis values.
        Must be called between put_start_recording_axes() and put_stop_recording_axes().
        Requires matplotlib package.
        """

        # matplotlib is not requirement for server so import only if needed.
        import matplotlib.pyplot as plt

        time_step = golden_program.TIME_STEP

        if self.driver.executed_axes is None:
            return

        for buffered_motion in self.driver.executed_axes:
            for alias, positions in buffered_motion.items():
                plt.figure(1)
                plt.subplot(311)
                t_vect = np.linspace(0, time_step * len(positions), len(positions))
                plt.plot(t_vect, positions, label=alias)
                plt.ylabel('Position (mm)')
                plt.legend()
                plt.grid()
                plt.subplot(312)
                plt.plot(t_vect[1:], np.diff(positions) * (1 / time_step), label=alias)
                plt.ylabel('Velocity (mm/s)')
                plt.legend()
                plt.grid()
                plt.subplot(313)
                plt.plot(t_vect[2:], np.diff(positions, n=2) * (1 / time_step)**2, label=alias)
                plt.ylabel('Acceleration (mm/s^2)')
                plt.legend()
                plt.grid()

            plt.show()

    @json_out
    def put_start_recording_axes(self):
        """
        Start recording axes values during robot motion.
        """
        self.driver.start_recording_axes()

    @json_out
    def put_stop_recording_axes(self):
        """
        Stop recording axes values during robot motion.
        """
        self.driver.stop_recording_axes()

    @json_out
    def put_save_recorded_axes(self, path):
        """
        Save previously recorded axis values to a file in JSON format.
        Must be called between put_start_recording_axes() and put_stop_recording_axes().
        :param path: Path of file to write to.
        :return:
        """

        if self.driver.executed_axes is None:
            return

        with open(path, "w") as f:
            f.write(json.dumps(self.driver.executed_axes))

    @property
    def calibration_data(self):
        """
        Calibration data is an arbitrary dictionary of data that kinematics
        can use to calibrate parts of a kinematic chain.
        """
        return self._calibration_data

    @calibration_data.setter
    def calibration_data(self, value):
        self._calibration_data = value

    @json_out
    def put_calibrate_kinematics(self, parameters):
        """
        Calibrate robot kinematics (robot model, tool offsets etc.) based on measurement data.
        :param parameters: Calculation parameters, measurement data etc.
        :return: Calculation result.
        """
        return self.driver.kinematics.calibrate(parameters)

    @json_out
    def put_press_physical_button(self, button_name, duration: float = 0):
        """
        Press a physical button.

        :param button_name: Name of button to press.
        :param duration: Duration of press in seconds. (default: 0s)
        """
        self.press_physical_button(button_name, duration)

    def press_physical_button(self, button_name, duration: float = 0):
        """
        Implementation for press gesture on a given button.

        :param button_name: The button to press.
        :param duration: How long to keep button pressed in seconds (default: 0s).
        :return: "ok" / error
        """
        ws = get_node_workspace(self)

        button = Node.find_from(ws, button_name)

        if button is None or type(button) != PhysicalButton:
            raise NodeException('No physical button found with name {}'.format(button_name))

        log.info("put_press_physical_button button_name={}, duration={}".format(button_name, duration))

        if button.approach_position is None or button.pressed_position is None or button.jump_height is None:
            raise Exception("Button's properties approach_position, pressed_position and jump_height"
                            " must be defined before call this press method")

        if self.has_multifinger():
            raise Exception("Press button gesture can't be performed with multifinger")

        # voicecoil tap if normal finger attached
        prg = self.program

        approach_position_pose = np.matrix(button.approach_position)
        pressed_position_pose = np.matrix(button.pressed_position)

        prg.begin(ctx=button.object_parent, toolframe=self.tool_frame(self.default_kinematic_name),
                  kinematic_name=self.default_kinematic_name)
        prg.set_speed(self.robot_velocity, self.robot_acceleration)

        current_robot_pose = self.effective_pose()
        initial_jump_frame = robotmath.translate(current_robot_pose, self.object_parent, button.object_parent)

        init_x, init_y, init_z = robotmath.frame_to_xyz(initial_jump_frame)
        z_jump = max(initial_jump_frame[2, 3], (approach_position_pose[2, 3] + button.jump_height))

        target_x, target_y, target_z = robotmath.frame_to_xyz(approach_position_pose)

        init_jump_pose = robotmath.xyz_to_frame(init_x, init_y, z_jump)
        target_jump_pose = robotmath.xyz_to_frame(target_x, target_y, z_jump)

        p1 = prg.line(init_jump_pose, target_jump_pose)
        p2 = prg.line(target_jump_pose, approach_position_pose)
        jump_primitives = [p1, p2]

        prg.move(jump_primitives)
        prg.run()

        prg.clear()
        press_primitives = [prg.line(approach_position_pose, pressed_position_pose),
                            prg.pause(duration),
                            prg.line(pressed_position_pose, approach_position_pose)]
        prg.move(press_primitives)
        prg.run()

        return "ok"

    def move_joint_position(self, joint_position: dict, speed=None, acceleration=None):
        """
        Moves robot to a specified joint configuration.
        :param joint_position: Target joint configuration as a dictionary of (axis_name: value) items.
        :param speed: Speed of joint movement. If None, current robot speed is used.
        :param acceleration: Acceleration of joint movement. If None, current robot acceleration is used.
        """
        if speed is None:
            speed = self.robot_velocity

        if acceleration is None:
            acceleration = self.robot_acceleration

        self.driver.move_joint_position(joint_position, speed, acceleration)

    @json_out
    def put_move_joint_position(self, joint_position: dict, speed=None, acceleration=None):
        """
        Moves robot to a specified joint configuration.
        :param joint_position: Target joint configuration as a dictionary of (axis_name: value) items.
        :param speed: Speed of joint movement. If None, current robot speed is used.
        :param acceleration: Acceleration of joint movement. If None, current robot acceleration is used.
        """
        self.move_joint_position(joint_position, speed, acceleration)

        return {'status': 'ok'}

    def joint_position(self, joint: str):
        p = self.driver.get_joint_positions()
        return p[joint]

    def camera_capture_preparations(self, camera_name):
        """
        Perform preparation actions on the robot required for capturing camera images on an object.
        E.g., moving any robot parts away from the camera image.
        If camera capture position has been defined for given camera, robot is moved to that position. This
        is useful if the camera is static and the moving robot stage can block view to imaging targer.
        :param camera_name: Name of camera for which to prepare.
        """
        if camera_name not in self._camera_capture_positions:
            return

        # Get robot maximum z value where to jump to.
        bounds = self.bounds()
        max_z = bounds['z'][1]

        position = self._camera_capture_positions[camera_name]

        if "x" not in position or "y" not in position:
            raise Exception("Robot camera_capture_positions must specify x and y coordinates for camera {}".format(camera_name))

        x, y = position["x"], position["y"]
        z = position.get("z", max_z)

        log.debug("Moving robot to camera capture position {}".format(position))

        current_x, current_y, _ = robotmath.frame_to_xyz(self.effective_pose())

        # Go to capture position via maximum z.
        self._move(x=current_x, y=current_y, z=max_z)
        self._move(x=x, y=y, z=max_z)
        self._move(x=x, y=y, z=z)

    def read_smart_tip_data(self, tool_name):
        """
        Read data of smart tip that is attached to given robot tool.
        :param tool_name: Name of tool.
        :return: Smart tip data.
        """
        return self._smart_tip_manager.read_memory_device_data(tool_name)

    @json_out
    def get_read_smart_tip_data(self, tool_name):
        """
        Read data of smart tip that is attached to given robot tool.
        :param tool_name: Name of tool.
        :return: Smart tip data.
        """
        return self.read_smart_tip_data(tool_name)

    def write_smart_tip_data(self, tool_name, data):
        """
        Write data to smart tip that is attached to given robot tool.
        Note that the maximum size of data may be quite limited.
        :param tool_name: Name of tool.
        :param data: Data as dict.
        """
        self._smart_tip_manager.write_memory_device_data(tool_name, data)

    @json_out
    def put_write_smart_tip_data(self, tool_name, data):
        """
        Write data to smart tip that is attached to given robot tool.
        Note that the maximum size of data may be quite limited.
        :param tool_name: Name of tool.
        :param data: Data as dict.
        """
        self.write_smart_tip_data(tool_name, data)

    def read_smart_tool_data(self, mount_name):
        """
        Read data of smart tool that is attached to given robot mount.
        :param mount_name: Name of mount.
        :return: Smart tool data.
        """
        return self._smart_tool_manager.read_memory_device_data(mount_name)

    @json_out
    def get_read_smart_tool_data(self, mount_name):
        """
        Read data of smart tool that is attached to given robot tool.
        :param mount_name: Name of mount.
        :return: Smart tool data.
        """
        return self.read_smart_tool_data(mount_name)

    def write_smart_tool_data(self, mount_name, data):
        """
        Write data to smart tool that is attached to given robot tool.
        Note that the maximum size of data may be quite limited.
        :param mount_name: Name of mount.
        :param data: Data as dict.
        """
        self._smart_tool_manager.write_memory_device_data(mount_name, data)

    @json_out
    def put_write_smart_tool_data(self, mount_name, data):
        """
        Write data to smart tool that is attached to given robot tool.
        Note that the maximum size of data may be quite limited.
        :param mount_name: Name of mount.
        :param data: Data as dict.
        """
        self.write_smart_tool_data(mount_name, data)

    @property
    @skip_nones
    def force_calibration_table(self):
        return self._force_calibration_table

    @force_calibration_table.setter
    def force_calibration_table(self, value):
        self._force_calibration_table = value

        if self.force_driver is not None:
            self.force_driver.set_force_calibration_table(value)

