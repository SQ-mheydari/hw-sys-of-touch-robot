import logging
from . import ListingNode
from .Tip import Tip
from tntserver.Nodes.Node import *
from tntserver.Nodes.TnT.Tool import Tool
from tntserver.Nodes.TnT.Workspace import get_node_workspace
from tntserver.Nodes.Voicecoil.Gestures import VoicecoilMaxContPeakCurrent
from tntserver.memorydevice import MemoryDeviceManager

log = logging.getLogger(__name__)


class Tips(ListingNode):
    """
    TnT™ Compatible Tips resource
    Tips is a container for Tip resources
    """
    resources = {
        'Tip': Tip
    }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, resources=Tips.resources, **kwargs)


class TipChanger:
    """
    Tip changer that is applicable to one finger robot and similar robots.
    Handles also one-finger robots with rotating axes.
    Handles multifinger tips when attached to static tools.
    This can be subclassed to customize tip change movements.
    """

    def __init__(self, robot):
        self._robot = robot

        # TODO: These should be limited by the actual capabilities of robot axes.
        self.max_tip_change_speed = 100
        self.max_tip_change_acceleration = 300

        # Slow speed is used near the slot positions to make testing safer.
        # The slow speed is further limited by max_tip_change_speed so it should be sufficient to make
        # max_tip_change_speed configurable.
        self.max_tip_change_speed_slow = 20

        # Separation when attaching / detaching standard tips (i.e. not multifinger tips).
        # TODO: Should use tip.separation property also for standard tips to avoid this hard-coded value.
        self.tip_change_separation = 50.0

        # Distance from slot-in and slot-out positions where to use slow speed.
        self.slow_distance = 30.0

    @property
    def tip_change_speed(self):
        """
        Speed to change tip with. This is at most the current robot speed.
        """
        return min(self.max_tip_change_speed, self._robot.robot_velocity)

    @property
    def tip_change_speed_slow(self):
        """
        Speed to use near the slot positions. This is at most the current robot speed.
        """
        return min(self.max_tip_change_speed_slow, self.tip_change_speed)

    @property
    def tip_change_acceleration(self):
        """
        Acceleration to change tip with. This is at most the current robot acceleration.
        """
        return min(self.max_tip_change_acceleration, self._robot.robot_acceleration)

    def detach_all_tips(self, model=None, detach_manually=False):
        """
        Detach all tips or all tips of specific model
        :param model: Model of tips to detach or None to detach all tips.
        :param detach_manually: If tips are to be detached manually and not with the tip changer.
        """
        tips = []

        def find_attached_tips_recursively(node):
            if type(node) == Tip and node.is_attached and (model is None or model == node.model):
                tips.append(node)

            for child in node.object_children.values():
                find_attached_tips_recursively(child)

        find_attached_tips_recursively(self._robot)

        # If any tips are found and we are attaching the tip manually, raise exception as the process can not continue
        if len(tips) != 0 and detach_manually:
            if model == 'Multifinger':
                # We tried to attach manually a tip, but a multifinger is already attached
                raise NodeException(title='Unable to manually attach tip', http_code=500,
                                    messages=['Detach multifinger tip currently attached first.'])
            else:
                # We tried to attach a multifinger, but there is already atleast one tip attached on the robot
                raise NodeException(title='Unable to manually attach tip', http_code=500,
                                    messages=['Detach all attached tips before attaching multifinger.'])

        for tip in tips:
            self.detach_tip(tip.object_parent.name)

    def attach_tip(self, tip_name: str, tool_name=None, attach_manually=False):
        """
        Attach tip to given tool.
        If tip slot is defined, then robot performs a movement to pick the tip.
        :param tip_name: Name of tip node.
        :param tool_name: Name of tool where the tip is to be attached. Must be a child of Mount node.
        :param attach_manually: If tip is to be attached manually and not with the tip changer.
        """
        if tool_name is None:
            tool_name = self._robot.active_tool.name

        ws = get_node_workspace(self._robot)

        tool = Node.find_from(ws, tool_name)

        if tool is None:
            raise NodeException("Tip attach error: no such tool.")

        # Tool must be attached to a Mount.
        if tool.mount is None:
            raise NodeException("Tool {} is not a child of Mount node".format(tool_name))

        current_tip_node = tool.tip

        # If there is a tip attached to the tool, detach it first.
        if current_tip_node is not None:
            if current_tip_node.name == tip_name:
                log.warning("Tip {} already mounted".format(tip_name))
                return
            if attach_manually:
                raise NodeException(title='Unable to manually attach tip', http_code=500,
                                    messages=['Detach the currently attached tip first.'])
            else:
                self.detach_tip(tool_name)

        tip = Node.find_from(ws, tip_name)

        if tip is None:
            raise NodeException('Unknown tip {}'.format(tip_name), 400)

        if tip.is_multifinger:
            # Check if multifinger can be attached to target tool.
            if not tool.can_attach_multifinger_tip:
                raise NodeException('Multifinger tip cannot be attached to target tool')

            # Make sure there are no tips attached to any tools. They might collide with multifinger.
            self.detach_all_tips(detach_manually=attach_manually)

        # Make sure there is no multifinger tip attached that could occupy the target tool.
        self.detach_all_tips(model="Multifinger", detach_manually=attach_manually)

        # If the target tip is currently attached to another tool, detach it first.
        if tip.is_attached:
            log.info("Tip is attached to another tool")
            assert type(tip.object_parent) == Tool

            if attach_manually:
                raise NodeException(title='Unable to manually attach tip', http_code=500, messages=[
                    'Tip is already attached on another tool, detach tip from that tool first.'])
            else:
                self.detach_tip(tip.object_parent.name)

        log.info("Attaching tip %s", tip_name)

        # If slot is defined, move robot to pick the tip.
        # Otherwise only the tip book-keeping is updated.
        if tip.is_slot_defined() and not attach_manually:
            self.move_to_attach_tip(tool.mount.mount_point, tip)
        else:
            # Notify simulator that tip was attached.
            self._robot.send_message("tips", "attach_tip {} {}".format(tip.name, tool.mount.mount_point))

        if self._robot.program is not None:
            self._robot.program.reset()

        # Connect tip node to attached tool node.
        tool.add_object_child(tip)

        if self._robot.program is not None:
            self._robot.program.reset()

        # Save the changed parent-child relations.
        tip.save()
        tool.save()

    def get_slot_in_pose(self, kinematic_name, tip):
        """
        Get tip slot-in pose that is appropriately filtered for given kinematic.
        This function can be overloaded to define e.g. special orientation when going to slot-in position.
        :param kinematic_name: Name of kinematic when using slot-in pose. Can be used by overload in subclass.
        :param tip: Tip whose slot-in pose to use as base.
        :return: Slot-in pose.
        """
        return np.matrix(tip.slot_in)

    def get_slot_out_pose(self, kinematic_name, tip):
        """
        Get tip slot-out pose that is appropriately filtered for given kinematic.
        This function can be overloaded to define e.g. special orientation when going to slot-out position.
        :param kinematic_name: Name of kinematic when using slot-out pose. Can be used by overload in subclass.
        :param tip: Tip whose slot-out pose to use as base.
        :return: Slot-out pose.
        """
        return np.matrix(tip.slot_out)

    def get_safe_distance(self, separation):
        """
        Get safe margin from workspace xy-limits where robot can freely rotate azimuth axis.
        This is robot specific.
        :param separation: Separation value when rotation is to be performed.
        :return: Distance in mm.
        """
        return 0.0

    def get_safe_position(self, position, separation, tool_frame, kinematic_name, tip):
        """
        Get position from which it is safe to approach slot positions when robot
        azimuth may change. Generally there is danger of axis limit violation of x and y axes
        when changing azimuth angle to match slot orientation.
        Safe position is closest position to current position where robot azimuth can freely rotate.
        In case tip slot-out position is within safe zone, slot-out position is used as safe position.
        This is to provide user the possibility to set slot-out position far away from slot-in position to provide
        extra safety in case e.g. the tip is exceptionally tall. In such case, even if normal slot positions are
        within the safe zone (where robot azimuth can rotate without axis limit violations), the robot tool might
        collide with the tall tip.
        :param position: Current position.
        :param separation: Current separation.
        :param tool_frame: Tool frame used when performing movements.
        :param kinematic_name: Kinematic name to perform movements with.
        :return: Safe position.
        """
        bounds = self._robot.driver.bounds(tool=tool_frame, kinematic_name=kinematic_name)

        margin = self.get_safe_distance(separation)

        safe_x_min = bounds['x'][0] + margin
        safe_x_max = bounds['x'][1] - margin

        safe_y_min = bounds['y'][0] + margin
        safe_y_max = bounds['y'][1] - margin

        slot_out = np.matrix(tip.slot_out)
        slot_out_x = slot_out[0, 3]
        slot_out_y = slot_out[1, 3]

        # Clip x, y position where it is safe to rotate the tool.
        safe = position.copy()
        x = np.clip(safe[0, 3], safe_x_min, safe_x_max)
        y = np.clip(safe[1, 3], safe_y_min, safe_y_max)

        # If tip slot-out position is within safe region, use that as safe position.
        if safe_x_min < slot_out_x < safe_x_max:
            log.debug("Using slot-out x as safe position x.")
            x = slot_out_x

        if safe_y_min < slot_out_y < safe_y_max:
            log.debug("Using slot-out y as safe position y.")
            y = slot_out_y

        safe[0, 3] = x
        safe[1, 3] = y

        return safe

    def move_to_attach_tip(self, kinematic_name, tip):
        """
        Moves robot to physically attach a tip to the tool attached to given kinematic.
        This method can be overridden in a subclass to redefine the movement.
        :param kinematic_name: Name of kinematic to use for robot movement.
        :param tip: Tip node to attach.
        """

        # Use active tool to attach tip.
        tool = self._robot.active_tool.frame

        bounds = self._robot.driver.bounds(tool=tool, kinematic_name=kinematic_name)
        high_z = bounds['z'][1]

        prg = self._robot.program

        current_high_z = robotmath.frame_to_pose(
            self._robot.driver.frame(tool=tool, kinematic_name=kinematic_name))
        current_high_z.A[2, 3] = high_z

        separation = tip.separation if tip.is_multifinger else self.tip_change_separation

        slot_in = self.get_slot_in_pose(kinematic_name, tip)
        slot_out = self.get_slot_out_pose(kinematic_name, tip)

        slot_out_high_z = slot_out.copy()
        slot_out_high_z[2, 3] = high_z

        safe = self.get_safe_position(current_high_z, separation, tool,
                                      kinematic_name, tip)

        # Frame with safe position and slot-in rotation.
        safe_pos_slot_in_rot = slot_in.copy()
        robotmath.set_frame_translation_vector(safe_pos_slot_in_rot, robotmath.get_frame_translation_vector(safe))

        slot_out_slow = slot_out.copy()
        slot_out_slow[2, 3] = min(slot_out_slow[2, 3] + self.slow_distance, high_z)

        slot_in_high_z = slot_in.copy()
        slot_in_high_z[2, 3] = high_z

        slot_in_slow = slot_in.copy()
        slot_in_slow[2, 3] = min(slot_in_slow[2, 3] + self.slow_distance, high_z)

        log.debug("Moving to high-z and then over slot-out / safe position.")

        prg.begin(ctx=Node.root, toolframe=tool, kinematic_name=kinematic_name)

        # Move to high z position and then over slot-out position.
        # This is done because in some cases the tip or rack is so high that there is a risk of collision even
        # when moving from "safe position" over slot-in position. User can then position slot-out to be sufficiently
        # far away.
        prg.set_speed(self.tip_change_speed, self.tip_change_acceleration)
        prg.move(prg.line(current_high_z, safe))
        prg.run()

        # If robot has separation control, change separation to appropriate value.
        if hasattr(self._robot, "put_finger_separation"):
            log.debug("Setting separation.")
            self._robot.put_finger_separation(separation)

        log.debug("Rotating to slot-in orientation.")

        prg.begin(ctx=Node.root, toolframe=tool, kinematic_name=kinematic_name)
        prg.set_speed(self.tip_change_speed_slow, self.tip_change_acceleration)
        prg.move(prg.line(safe, safe_pos_slot_in_rot))
        prg.run()

        log.debug("Moving near slot-in position.")

        # Move over slot-in position at high z and then above slot-in slow position.
        prg.begin(ctx=Node.root, toolframe=tool, kinematic_name=kinematic_name)
        prg.set_speed(self.tip_change_speed, self.tip_change_acceleration)
        prg.move([prg.line(safe_pos_slot_in_rot, slot_in_high_z),prg.line(slot_in_high_z, slot_in_slow)])
        prg.run()

        log.debug("Moving to slot-in position.")

        # Use slow speed to move to the slot-in position.
        prg.clear()
        prg.set_speed(self.tip_change_speed_slow, self.tip_change_acceleration)
        prg.move(prg.line(slot_in_slow, slot_in))

        # verify finger attached successfully if required parameter is set
        threshold = getattr(self._robot, 'tip_attached_threshold', None)
        voicecoil_current = getattr(self._robot, 'tip_attaching_current_limit', None)
        voicecoil_name = getattr(self._robot, "_voicecoil_name", None)

        if threshold is not None and voicecoil_name is not None and voicecoil_current is not None:
            log.debug("threshold = {}, voicecoil_name = {}, voicecoil_current = {}".format(
                threshold, voicecoil_name, voicecoil_current))
            with VoicecoilMaxContPeakCurrent(robot=self._robot,
                                             max_cont_current=voicecoil_current, peak_current=voicecoil_current):
                prg.run()
                tip_successfully_attached, voicecoil_offset_in_z_direction = self.verify_finger_attached(
                    voicecoil_name=voicecoil_name, threshold=threshold)
        else:
            log.debug("threshold = {}, voicecoil_name = {}, voicecoil_current = {}, skipping verify_finger_attached method".format(
                threshold, voicecoil_name, voicecoil_current))
            prg.run()
            tip_successfully_attached = True

        if tip_successfully_attached:
            # Send message so that simulator re-parents the visualized tip.
            self._robot.send_message("tips", "attach_tip {} {}".format(tip.name, kinematic_name))

            prg.begin(ctx=Node.root, toolframe=tool, kinematic_name=kinematic_name)

            log.debug("Moving to slot-out position.")

            # Move to slot-out pose with slow speed.
            prg.set_speed(self.tip_change_speed_slow, self.tip_change_acceleration)
            prg.move(prg.line(slot_in, slot_out))
            prg.run()

            log.debug("Moving to high-z position.")

            # Move to high z position.
            prg.clear()
            prg.set_speed(self.tip_change_speed, self.tip_change_acceleration)
            prg.move(prg.line(slot_out, slot_out_high_z))
            prg.run()
        else:
            log.debug("Moving out of slot-in position.")

            prg.clear()
            prg.set_speed(self.tip_change_speed, self.tip_change_acceleration)
            prg.move(prg.point(slot_in_slow))
            prg.run()

            raise NodeException("Couldn't attach tip, offset in z direction = {} > threshold = {}".format(
                voicecoil_offset_in_z_direction, threshold))

    def verify_finger_attached(self, voicecoil_name, threshold):
        """
        return true if finger gets correctly attached before slot-out
        Read setpoint of the voicecoil and compare with the joint value
        if those differ by more than threshold then return False
        :return: pair of (True if attached, False otherwise and voicecoil_offset_in_z_direction)
        """
        setpoint = self._robot.driver.get_scaled_axis_setpoint(axis_alias=voicecoil_name)
        joint_position = self._robot.joint_position(joint=voicecoil_name)
        log.debug("After slot_in position, axis_name = {}, setpoint = {}, joint_position = {}".format(
            voicecoil_name, setpoint, joint_position
        ))
        voicecoil_offset_in_z_direction = abs(joint_position - setpoint)
        if voicecoil_offset_in_z_direction > threshold:
            return False, voicecoil_offset_in_z_direction
        else:
            return True, voicecoil_offset_in_z_direction

    def detach_tip(self, tool_name=None, detach_manually=False):
        """
        Detach tip from given tool.
        If tip slot is defined, then robot performs a movement to drop the tip.
        :param tool_name: Name of tool where a tip is currently attached. Must be a child of Mount node.
        :param detach_manually: If tip is to be detached manually and not with the tip changer.
        """
        ws = get_node_workspace(self._robot)

        tool = Node.find_from(ws, tool_name)

        if tool is None:
            raise NodeException("Tip detach error: no such tool.")

        if tool.mount is None:
            raise NodeException("Tool {} is not a child of Mount node".format(tool_name))

        tip = tool.tip

        # If the tool does not have Tip node as child, then do nothing.
        if tip is None:
            return

        log.info("Detaching tip %s", tip.name)

        if self._robot.program is not None:
            self._robot.program.reset()

        # If slot is defined and using automatic tip changing, move robot to drop the tip.
        # Otherwise only the tip book-keeping is updated.
        if tip.is_slot_defined() and not detach_manually:
            self.move_to_detach_tip(tool.mount.mount_point, tip)
        else:
            # Notify simulator that tip was detached.
            self._robot.send_message("tips", "detach_tip {}".format(tip.name))

        # Disconnect tip node from the tool.
        tip.remove_object_from_parent()

        if self._robot.program is not None:
            self._robot.program.reset()

        # Save changed parent-child relations.
        tool.save()
        tip.save()

    def move_to_detach_tip(self, kinematic_name, tip):
        """
        Moves robot to physically detach the tip from the currently active tool.
        This method can be overridden in a subclass to redefine the movement.
        :param kinematic_name: Name of kinematic to use for robot movement.
        :param tip: Tip node to detach. Assumes that this is attached to the active tool.
        """

        # Use tool frame where the effect of the tip is removed.
        # Tip connection is not removed until tip is successfully dropped.
        tool_frame = self._robot.active_tool.frame

        bounds = self._robot.driver.bounds(tool=tool_frame, kinematic_name=kinematic_name)
        high_z = bounds['z'][1]

        prg = self._robot.program

        current_high_z = robotmath.frame_to_pose(
            self._robot.driver.frame(tool=tool_frame, kinematic_name=kinematic_name))
        current_high_z.A[2, 3] = high_z

        separation = tip.separation if tip.is_multifinger else self.tip_change_separation

        slot_in = self.get_slot_in_pose(kinematic_name, tip)
        slot_out = self.get_slot_out_pose(kinematic_name, tip)

        slot_out_high_z = slot_out.copy()
        slot_out_high_z[2, 3] = high_z

        # Position where it is safe to rotate the tool.
        safe = self.get_safe_position(current_high_z, separation, tool_frame, kinematic_name, tip)

        # Frame with safe position and slot-out rotation.
        safe_pos_slot_out_rot = slot_out.copy()
        robotmath.set_frame_translation_vector(safe_pos_slot_out_rot, robotmath.get_frame_translation_vector(safe))

        slot_out_slow = slot_out.copy()
        slot_out_slow[2, 3] = min(slot_out_slow[2, 3] + self.slow_distance, high_z)

        slot_in_high_z = slot_in.copy()
        slot_in_high_z[2, 3] = high_z

        slot_in_slow = slot_in.copy()
        slot_in_slow[2, 3] = min(slot_in_slow[2, 3] + self.slow_distance, high_z)

        prg.begin(ctx=Node.root, toolframe=tool_frame, kinematic_name=kinematic_name)
        
        log.debug("Moving to high-z and then over slot-out / safe position.")

        # Move to high z position, then to slot-out at high z with current rotation and then to safe position.

        prg.set_speed(self.tip_change_speed, self.tip_change_acceleration)
        prg.move(prg.line(current_high_z, safe))
        prg.run()

        # If robot has separation control, change separation to appropriate value.
        if hasattr(self._robot, "put_finger_separation"):
            if not self._robot.has_multifinger():
                log.debug("Setting finger separation.")
                self._robot.put_finger_separation(self.tip_change_separation)
                
        log.debug("Rotating to slot-out orientation.")

        prg.begin(ctx=Node.root, toolframe=tool_frame, kinematic_name=kinematic_name)
        prg.set_speed(self.tip_change_speed_slow, self.tip_change_acceleration)
        prg.move(prg.line(safe, safe_pos_slot_out_rot))
        prg.run()

        log.debug("Moving near slot-out position.")

        # Rotate at safe position to slot-out rotation, then move to slot-out at high z and then to slot-out slow position.

        prg.begin(ctx=Node.root, toolframe=tool_frame, kinematic_name=kinematic_name)
        prg.set_speed(self.tip_change_speed, self.tip_change_acceleration)
        prg.move([prg.line(safe_pos_slot_out_rot, slot_out_high_z), prg.line(slot_out_high_z, slot_out_slow)])
        prg.run()

        log.debug("Moving to slot-out position and then to slot-in position.")

        # Move to slot-out position and then to slot-in position at slow speed.
        prg.clear()
        prg.set_speed(self.tip_change_speed_slow, self.tip_change_acceleration)
        prg.move([
            prg.line(slot_out_slow, slot_out),
            prg.line(slot_out, slot_in)
        ])
        prg.run()

        # Send message so that simulator re-parents the visualized tip.
        self._robot.send_message("tips", "detach_tip {}".format(tip.name))

        prg.begin(ctx=Node.root, toolframe=tool_frame, kinematic_name=kinematic_name)

        log.debug("Moving out of slot-in position.")

        # Move to slot-in slow position at slow speed.
        prg.set_speed(self.tip_change_speed_slow, self.tip_change_acceleration)
        prg.move(prg.line(slot_in, slot_in_slow))
        prg.run()

        log.debug("Moving to high-z position.")

        # Move to slot-in high z position.
        prg.clear()
        prg.set_speed(self.tip_change_speed, self.tip_change_acceleration)
        prg.move(prg.line(slot_in_slow, slot_in_high_z))
        prg.run()

        log.debug("Moving over slot-out at high-z.")

        # Move to slot-out high z position. Needed when the voice coils are lifted while dropping of the tip.
        prg.clear()
        prg.set_speed(self.tip_change_speed, self.tip_change_acceleration)
        prg.move(prg.line(slot_in_high_z, slot_out_high_z))
        prg.run()


class SmartTipManager(MemoryDeviceManager):
    def __init__(self, mode, addresses, comm=None, ip_address=None, id_chip_address=7, hot_changing=False):
        """
        Initialize smart tip manager.
        :param mode: Operation mode. One of MODE_NORMAL, MODE_EXTERNAL, MODE_SIMULATOR.
        :param addresses: Dictionary of tool name - motherboard address pairs e.g. {"tool1": 8}.
        :param comm: Pre-initialized OptoMotionComm object when using normal mode.
        :param ip_address: IP address of motherboard when using external mode.
        :param id_chip_address: Last digit of ID chip part number is used as its memory address.
        :param hot_changing: If true, TnT tip attach status is automatically changed to match smart tip HW status.
        """
        super().__init__(mode, addresses, comm, ip_address, id_chip_address)
        self.hot_changing = hot_changing

    def verify_attached_tips(self, attached_tips, tips_node, tip_data=None):
        """
        Verify that the tips that are attached to robot according to SW book-keeping match
        the physically attached tip. This is only possible when using smart tips that have
        capability to return stored data.
        Raises exception if verification fails.
        :param attached_tips: Dictionary of attached tips to each tool e.g. {"tool1": "tip1", "tool2": None}.
        :param tips_node: Tips node object. Only tips under this node are considered.
        :param tip_data: Dictionary where key is tool name and value is data read via read_smart_tip_data().
        This allows reading the tip data only once if other operations need to be performed with the data.
        """

        if tip_data is None:
            tip_data = {}

            for tool_name in self.names:
                tip_data[tool_name] = None
                try:
                    tip_data[tool_name] = self.read_memory_device_data(tool_name)
                except:
                    pass

        # Make sure that the state of currently attached tips match smart tip data.
        for tool_name, tip_name in attached_tips.items():
            if tip_name is None:
                # If tip_name is None, no tip is attached to the tool. Make sure that smart tip is not connected.
                if tool_name in self.names and tip_data[tool_name] is not None:
                    raise Exception("Smart tip is physically attached to {} but not attached "
                                    "according to TnT Server. Detach the tip and try again.".format(tool_name))
            else:
                tip = Node.find_from(tips_node, tip_name)

                if tip.smart:
                    # If smart tip is attached to the tool, compare the attributes.
                    data = tip_data[tool_name]

                    if data is None:
                        log.error("Could not read smart tip data. Tip might not be attached to the robot.")
                        raise Exception("Could not read smart tip data. Tip might not be attached to the robot.")

                    smart_tip_name = data["name"]
                    smart_tip_properties = data["properties"]

                    # Check that smart tip name matches current tip resource name.
                    if smart_tip_name != tip.name:
                        raise Exception("Current tip name {} does not match smart tip name {}.".
                                        format(tip.name, smart_tip_name))

                    # Check that smart tip properties match current tip resource properties.
                    for key, smart_tip_value in smart_tip_properties.items():
                        tip_value = getattr(tip, key)

                        if isinstance(tip_value, bool) and smart_tip_value != tip_value or\
                                abs(smart_tip_value - tip_value) > 0.1:
                            raise Exception("Current tip property {} value {} does not match smart tip property value {}.".
                                            format(key, tip_value, smart_tip_value))
                else:
                    # A non-smart tip is attached to the tool. Make sure that a smart tip is not physically
                    # attached to the tool.
                    if tip_data[tool_name] is not None:
                        raise Exception("Smart tip is physically attached to {} but another tip is attached "
                                        "according to TnT Server. Change the tip and try again.".format(tool_name))
