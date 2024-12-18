
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTPhysicalButtonClient(TnTClientObject):
    """
    TnT Compatible Button resource
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "physical_buttons", name)
        
    def remove(self):
        """
        Remove the resource.
        After the resource has been removed, the client object is no longer valid.
        """
        return self._DELETE('', {})
    
    @property
    def approach_position(self):
        """
        Robot position where button can be approached with linear movement.
        """
        return self.get_property('approach_position')
        
    @approach_position.setter
    def approach_position(self, value):
        """
        Robot position where button can be approached with linear movement.
        """
        self.set_property('approach_position', value)
        
    @property
    def jump_height(self):
        """
        Height from approach position where robot can safely move over the approach position in the button's parent context.
        """
        return self.get_property('jump_height')
        
    @jump_height.setter
    def jump_height(self, value):
        """
        Height from approach position where robot can safely move over the approach position in the button's parent context.
        """
        self.set_property('jump_height', value)
        
    @property
    def pressed_position(self):
        """
        Robot position where the button is pressed down by the robot.
        """
        return self.get_property('pressed_position')
        
    @pressed_position.setter
    def pressed_position(self, value):
        """
        Robot position where the button is pressed down by the robot.
        """
        self.set_property('pressed_position', value)
        
