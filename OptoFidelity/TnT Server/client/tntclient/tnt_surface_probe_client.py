
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTSurfaceProbeClient(TnTClientObject):
    """
    This class controls a surface probing sequence for the given robot.
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, None, name)
        
    def abort(self, ):    
        """
        Aborts currently running surface probing.
        """
        params = {
        }
        
        
        return self._PUT('abort', params)
        
    def probe_z_surface(self, return_to_start=True, tool_name='tool1'):    
        """
        Starts automatic DUT surface z height probing sequence. Robot will move to negative direction along the robot
        coordinate system Z-axis in steps. Once the surface touch has been detected, the robot either stays at the
        found surface location or moves back up. Function will block during the probing sequence.
        :param return_to_start: If True, return to start position when surface is found.
        :param tool_name: Name of the tool to use for surface probing.
        Otherwise move effective position to found surface.
        :return: Detected surface position.
        """
        params = {
            'return_to_start': return_to_start,
            'tool_name': tool_name,
        }
        
        
        return self._PUT('probe_z_surface', params)
        
