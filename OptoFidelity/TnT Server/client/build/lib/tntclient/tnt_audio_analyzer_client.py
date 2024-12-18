
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTAudioAnalyzerClient(TnTClientObject):
    """
    Analyzer for analyzing audio signals.
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "analyzers", name)
        
    def find_frequency_peaks(self, value):    
        """
        Find frequency peaks in given time-domain audio sampling.
        :param value: sound in wav formatted bytes (same as NodeMicrophone format). (The name of this parameter
        is dictated by client REST api functions and cannot be refactored)
        :return: a list containing a list of frequencies (Hz) and a list of corresponding spectral intensities.
        """
        
        return self._PUT('find_frequency_peaks', parameters=None, content_type='audio/x-wav', content=value)
        
