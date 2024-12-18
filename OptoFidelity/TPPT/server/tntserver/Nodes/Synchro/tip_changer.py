from tntserver.Nodes.TnT.Tips import TipChanger
from tntserver.Nodes.Node import *
from tntserver import robotmath
import numpy as np


class SynchroFingerTipChanger(TipChanger):
    """
    Finger changer for robot that has synchro-finger tool.
    Assumes that both finger kinematics see the azimuth rotation in the same way in relation to workspace.
    Hence picking tips to the two fingers requires special movements to make sure the synchro tool
    does not collide with a tip rack.
    """
    def __init__(self, robot, finger1_kinematic_name="tool1", finger2_kinematic_name="tool2"):
        """
        Initialize tip changer.
        :param robot: Robot that performs the tip change movements.
        :param finger1_kinematic_name: Name of kinematic that corresponds to finger along negative local pose x-axis.
        :param finger2_kinematic_name: Name of kinematic that corresponds to finger along positive local pose x-axis.
        """
        super().__init__(robot)

        self.finger1_kinematic_name = finger1_kinematic_name
        self.finger2_kinematic_name = finger2_kinematic_name

    def get_safe_distance(self, separation):
        # Separation is the minimum margin so add a little bit more to avoid issues with round-off and robot accuracy.
        return separation + 10.0

    def _determine_tool_rotation(self, kinematic_name, tip):
        """
        Determine tool rotation that should be used when picking the given tip with given kinematic.
        This is required to make sure that the finger where tip is picked is the finger closest to
        the tip rack.
        :param kinematic_name: Name of kinematic to use.
        :param tip: Tip to pick
        :return: 4x4 pose matrix that has correct orientation and zero translation.
        """
        slot_in = np.matrix(tip.slot_in)
        slot_out = np.matrix(tip.slot_out)

        # Slot positions define a direction vector for correct local x-axis when changing tip.
        local_x = robotmath.get_frame_translation_vector(slot_out) - robotmath.get_frame_translation_vector(slot_in)
        local_x /= np.linalg.norm(local_x)

        if kinematic_name == self.finger1_kinematic_name:
            # local_x is initially designed for finger 1.
            pass
        elif kinematic_name == self.finger2_kinematic_name:
            # Finger 2 requires opposite approach rotation to finger 1.
            local_x = -local_x
        else:
            raise Exception("Invalid kinematic {} for synchro-finger tip changer".format(kinematic_name))

        transform = robotmath.identity_frame()

        # Local z of pose points along +z in workspace.
        local_z = np.matrix([0, 0, 1])

        local_y = np.matrix(np.cross(local_z, local_x))

        transform[0:3, 0] = local_x.reshape(3, 1)
        transform[0:3, 1] = local_y.reshape(3, 1)
        transform[0:3, 2] = local_z.reshape(3, 1)

        return transform

    def get_slot_in_pose(self, kinematic_name, tip):
        """
        Get tip slot-in pose for robot that is correct for given kinematic.
        :param kinematic_name: Name of kinematic to use.
        :param tip: Tip whose slot-in pose is used as base.
        :return: Slot-in pose for robot to use
        """
        if tip.is_multifinger:
            return np.matrix(tip.slot_in)
        else:
            pose = self._determine_tool_rotation(kinematic_name, tip)
            robotmath.set_frame_xyz(pose, *robotmath.frame_to_xyz(np.matrix(tip.slot_in)))

            return pose

    def get_slot_out_pose(self, kinematic_name, tip):
        """
        Get tip slot-out pose for robot that is correct for given kinematic.
        :param kinematic_name: Name of kinematic to use.
        :param tip: Tip whose slot-out pose is used as base.
        :return: Slot-out pose for robot to use
        """
        if tip.is_multifinger:
            return np.matrix(tip.slot_out)
        else:
            pose = self._determine_tool_rotation(kinematic_name, tip)
            robotmath.set_frame_xyz(pose, *robotmath.frame_to_xyz(np.matrix(tip.slot_out)))

            return pose

    def move_to_attach_tip(self, kinematic_name, tip):
        pick_drop_current = self._robot.voicecoil_multifinger_pick_drop_current

        with VoicecoilMaxContCurrent(robot=self._robot,
                                     max_cont_current=pick_drop_current,
                                     voicecoil_names=['voicecoil1', 'voicecoil2']):
            if tip.voice_coil_position is not None and not np.isclose(tip.voice_coil_position, 0.0):
                with LiftVoiceCoilsForPicking(self._robot, tip.voice_coil_position):
                    super().move_to_attach_tip(kinematic_name, tip)
            else:
                super().move_to_attach_tip(kinematic_name, tip)

        if tip.grippable:
            self._robot.grip_with_separation_axis(tip.separation)

    def move_to_detach_tip(self, kinematic_name, tip):
        if tip.grippable:
            self._robot.release_separation_axis_grip(tip.separation)

        pick_drop_current = self._robot.voicecoil_multifinger_pick_drop_current

        with VoicecoilMaxContCurrent(robot=self._robot,
                                     max_cont_current=pick_drop_current,
                                     voicecoil_names=['voicecoil1', 'voicecoil2']):
            if tip.voice_coil_position is not None and not np.isclose(tip.voice_coil_position, 0.0):
                with LiftVoiceCoilsForPicking(self._robot, tip.voice_coil_position):
                    super().move_to_detach_tip(kinematic_name, tip)
            else:
                super().move_to_detach_tip(kinematic_name, tip)


class LiftVoiceCoilsForPicking:
    """
    Enables picking up tips when there is not enough space while the voice coils are normally extended to home position.
    Mandatory parameters are the used robot class and the position of the voice coils.
    """
    def __init__(self, robot, voice_coil_lifted_position):
        """
        :param robot: The robot object to use when moving the voice coils.
        :param voice_coil_lifted_position: The position of the voice coils when lifted to proper picking height.
        """
        super().__init__()
        self._robot = robot
        self._voice_coil_lifted_position = voice_coil_lifted_position

    def __enter__(self):
        log.debug("Lifting voicecoils for picking.")

        self._robot.move_voicecoils(self._voice_coil_lifted_position)

    def __exit__(self, *args, **kwargs):
        log.debug("Zeroing voicecoil positions.")
        self._robot.move_voicecoils(0.0)


class VoicecoilMaxContCurrent:
    """
    State class to temporarily set maximum continuous and peak current to the voice coils.
    """
    def __init__(self, robot, max_cont_current, voicecoil_names: list()):
        self.robot = robot
        self.max_cont_current = max_cont_current
        self.original_max_cont_currents = {}
        self.voicecoil_names = voicecoil_names

    def __enter__(self):
        for voicecoil_name in self.voicecoil_names:
            self.original_max_cont_currents[voicecoil_name] = self.robot.read_torque_limit(axis_name=voicecoil_name)
            self.robot.set_torque_limit(axis_name=voicecoil_name,
                                         torque_limit=self.max_cont_current)

    def __exit__(self, *args, **kwargs):
        # Restore original settings
        for voicecoil_name in self.voicecoil_names:
            self.robot.set_torque_limit(axis_name=voicecoil_name,
                                         torque_limit=self.original_max_cont_currents[voicecoil_name])
