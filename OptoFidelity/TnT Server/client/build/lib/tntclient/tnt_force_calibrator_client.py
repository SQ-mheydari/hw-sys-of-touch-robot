
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTForceCalibratorClient(TnTClientObject):
    """
    Node for voice coil calibration functionality
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, None, name)
        
    def calibrate(self, axis_name=None, press_duration=None):    
        """
        Perform force calibration synchronously.
        :param axis_name: Name of axis to calibrate for force. None to use the default.
        :param press_duration: Press duration during calibration. If None, then default configured value is used.
        :return: Dict which contains finished force calibration.
        """
        params = {
        }
        
        if axis_name is not None:
            params['axis_name'] = axis_name
        if press_duration is not None:
            params['press_duration'] = press_duration
        
        return self._PUT('calibrate', params)
        
    def save_calibration(self, calibration_id):    
        """
        Saves the corresponding calibration data to the server configuration file
        :param calibration_id: Calibration uuid
        :return: None
        """
        params = {
            'calibration_id': calibration_id,
        }
        
        
        return self._PUT('save_calibration', params)
        
