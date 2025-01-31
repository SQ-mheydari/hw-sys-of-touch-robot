from .Node import *
from client.tntclient.tnt_client import RequestError

class TipNode(Node):
    """
    Node that represents robot tip.
    """

    def __init__(self, name, tnt_tip):
        super().__init__(name)
        self.tnt_tip = tnt_tip
        self.display_enabled = True
        self.enabled = False

class TipsNode(Node):
    """
    Node that hosts tip nodes as children and keeps track of current robot tip.
    """

    def __init__(self, context):
        super().__init__('Tips')

        self.active_tip = None
        self.context = context

    def create_tips(self):
        """
        Create a group of controls for enabling tips for tests.
        """

        # Get tip definitions from server.
        tips = self.context.tnt.tips()

        tips.sort(key=lambda t: t.name)

        for tip in tips:
            tip_node = TipNode(tip.name, tip)

            self.add_child(tip_node)

    def set_active_tip(self, tip_node):
        """
        Set active tip to be used by test cases.
        Makes robot to physically change tip if appropriate.
        :param tip_node: Tip node to set active.
        """

        tip = tip_node.tnt_tip

        # Set active ip state.
        self.active_tip = tip

        self.context.html_color("Picking tip: " + str(self.active_tip), 'orange')

        prev_status = self.context.indicators.get_status()
        self.context.indicators.set_status("Changing tip to " + str(self.active_tip))
        self.context.indicators.set_tip_name(str(self.active_tip))

        # Make robot change tip.
        self.context.set_robot_default_speed()
        self.context.robot.change_tip(self.active_tip.name)
        self.context.indicators.set_status(prev_status)

    def set_active_tip_by_name(self, tip_name):
        self.set_active_tip(self.get_child(tip_name))

    def check_tips(self):
        """
        Check that at least one tip is enabled.
        """

        for tip in self.children:
            if tip.enabled:
                return True

        return False

    def detach_tip(self, finger_id):
        """
        Detach tip from finger.
        If there is not such finger, no error is raised.
        This is to be compatible with single and multi-finger robots.
        :param finger_id: ID of finger to drop tip from.
        """
        try:
            tips = self.context.robot.get_attached_tips()
            tool = ["tool1", "tool2"][finger_id]
            if tool in tips and tips[tool] is not None:
                self.context.robot.detach_tip(finger_id)
        except RequestError as e:
            # Ignore this specific error.
            if e.message != "Tip detach error: no such tool.":
                raise e

