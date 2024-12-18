
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTFutekClient(TnTClientObject):
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, None, name)
        
    def forcevalue(self, ):    
        """
        Returns force sensor reading in grams
        """
        params = {
        }
        
        
        return self._GET('forcevalue', params)
        
    def tare(self, window_size=50, gram_diff=0.1, timeout_s=5):    
        """
        Tare sensor based on given parameters.
        :param window_size: How many samples to take when accounting if force is stabilized
        :param gram_diff: How many gram difference is allowed for samples
        :param timeout_s: How many seconds to try before giving up
        """
        params = {
            'window_size': window_size,
            'gram_diff': gram_diff,
            'timeout_s': timeout_s,
        }
        
        
        return self._PUT('tare', params)
        
