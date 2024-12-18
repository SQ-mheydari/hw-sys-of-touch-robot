
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTMicrophoneClient(TnTClientObject):
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "detectors", name)
        
    def device_default_sample_rate(self, ):    
        """
        The default sample rate of the microphone
        :return: default sample rate
        """
        params = {
        }
        
        
        return self._GET('device_default_sample_rate', params)
        
    def get_latest_recording(self, ):    
        """
        Fetch the latest recording
        ---------------------------------------------------
        To save audio to a file one can use the following python commands:
        f = open("test.wav", 'wb')
        f.write(microphone.record_audio(3))
        f.close()
        ---------------------------------------------------
        :return: .wav formatted bytes
        """
        params = {
        }
        
        
        return self._GET('latest_recording', params)
        
    def list_recording_devices(self, ):    
        """
        List all the recording devices found in the system
        :return: Names in a list
        """
        params = {
        }
        
        
        return self._GET('list_recording_devices', params)
        
    def record_audio(self, record_duration):    
        """
        Records audio for the given duration in seconds.
        ---------------------------------------------------
        To save audio to a file one can use the following python commands:
        f = open("test.wav", 'wb')
        f.write(microphone.record_audio(3))
        f.close()
        ---------------------------------------------------
        :param record_duration: duration of the record (s)
        :return: .wav formatted bytes
        """
        params = {
            'record_duration': record_duration,
        }
        
        
        return self._PUT('record_audio', params)
        
    @property
    def chunk_size(self):
        """
        The chunk_size size of sample processing.
        """
        return self.get_property('chunk_size')
        
    @chunk_size.setter
    def chunk_size(self, value):
        """
        The chunk_size size of sample processing.
        """
        self.set_property('chunk_size', value)
        
    @property
    def device_name(self):
        """
        Name of the microphone device. This is used to choose the
        correct input device from all the devices seen by the system.
        """
        return self.get_property('device_name')
        
    @device_name.setter
    def device_name(self, value):
        """
        Name of the microphone device. This is used to choose the
        correct input device from all the devices seen by the system.
        """
        self.set_property('device_name', value)
        
    @property
    def margin(self):
        """
        Amount of samples ignored from the beginning of the record to
        avoid microphone startup noise interference.
        """
        return self.get_property('margin')
        
    @margin.setter
    def margin(self, value):
        """
        Amount of samples ignored from the beginning of the record to
        avoid microphone startup noise interference.
        """
        self.set_property('margin', value)
        
    @property
    def rate(self):
        """
        Recording data rate (samples/second).
        """
        return self.get_property('rate')
        
    @rate.setter
    def rate(self, value):
        """
        Recording data rate (samples/second).
        """
        self.set_property('rate', value)
        
    @property
    def timeout_buffer(self):
        """
        Amount of time waited after recording before timeout, in seconds.
        """
        return self.get_property('timeout_buffer')
        
    @timeout_buffer.setter
    def timeout_buffer(self, value):
        """
        Amount of time waited after recording before timeout, in seconds.
        """
        self.set_property('timeout_buffer', value)
        
