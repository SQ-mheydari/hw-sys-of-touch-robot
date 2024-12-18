
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTMotherboardClient(TnTClientObject):
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "motherboards", name)
        
    def set_output_state(self, name_or_number, state):    
        """
        Set state of certain motherboard output.
        :param name_or_number: Configured alias or number of the output.
        :param state: 0 or 1.
        :return: Request output.
        """
        params = {
            'name_or_number': name_or_number,
            'state': state,
        }
        
        
        return self._PUT('output_state', params)
        
