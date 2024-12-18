
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTSpeakerClient(TnTClientObject):
    """
    Node for playing wav files from /data/audio folder with given device
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "speakers", name)
        
    def list_playback_devices(self, ):    
        """
        Lists all the found playback devices
        :return: Names in a list
        """
        params = {
        }
        
        
        return self._GET('list_playback_devices', params)
        
    def play_wav_file(self, filename):    
        """
        Play wav file of given filename
        :param filename: name of the audio file
        :return: "ok" for a http response
        """
        params = {
            'filename': filename,
        }
        
        
        return self._PUT('play_wav_file', params)
        
    @property
    def chunk_size(self):
        """
        The patch size of sample processing
        """
        return self.get_property('chunk_size')
        
    @chunk_size.setter
    def chunk_size(self, value):
        """
        The patch size of sample processing
        """
        self.set_property('chunk_size', value)
        
    @property
    def device_name(self):
        """
        Name of the speaker device. This is used to choose the
        correct output device from all the devices seen by the system.
        """
        return self.get_property('device_name')
        
    @device_name.setter
    def device_name(self, value):
        """
        Name of the speaker device. This is used to choose the
        correct output device from all the devices seen by the system.
        """
        self.set_property('device_name', value)
        
