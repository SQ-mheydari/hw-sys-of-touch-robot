import scipy.io.wavfile as wav
import wave
import os

from tntserver.Nodes.Node import *

log = logging.getLogger(__name__)

try:
    import pyaudio
except ImportError:
    pyaudio = None  # pyaudio not available. Don't report error until pyaudio is attempted to be used.

'''
Configuration through yaml (change device_name to your own device):

- name: speaker1
  cls: NodeSpeaker
  parent: speakers
  connection: speakers
  arguments:
    device_name: jabra
    chunk_size: 1024

- name: speakers
  cls: NodeSpeakers
  parent: ws
  connection: ws

--------------------------------
For testing one can call the following GET request, it should return list of devices:
GET 127.0.0.1:8000/tnt/workspaces/ws/speakers/speaker1/list_playback_devices

Also, if you have some .wav files in data/audio, you can try playing them with:
PUT 127.0.0.1:8000/tnt/workspaces/ws/speakers/speaker1/play_wav_file

In the PUT body you should have:
{
	"filename": <audio_file_name>
}

'''

class NodeSpeaker(Node):
    """
    Node for playing wav files from /data/audio folder with given device
    """
    def __init__(self, name, **kwargs):
        """
        Init function of the class
        :param name: name of the node
        """
        super().__init__(name)
        # For unit testing we need to be able to replace the actual pyaudio with our own dummy implementation
        self._pyaudio_class = pyaudio.PyAudio if pyaudio is not None else None
        self._chunk_size = 1024 # size of data chunk, samples

    def _init(self, device_name, chunk_size=None, **kwargs):
        """
        Another init function that's run when nodes are initialized
        :param device_name: name of the audio playback device
        :param chunk_size: size of the data chunk, samples
        """
        assert isinstance(device_name, str)
        self._device_name = device_name

        if chunk_size is not None:
            assert isinstance(chunk_size, int) and chunk_size >= 1
            self._chunk_size = chunk_size

        # Folder where the audio (wav) files are located. We don't
        # want to create folders if we are only testing
        self._audio_folder_path = self._init_data_folder()

        # For unit testing we need to be able to get
        # pyaudio class object out from object of this class
        self._p_object = None

    @staticmethod
    def _init_data_folder():
        """
        Ensures that data/audio folder exists and returns it
        :return: path to data/audio
        """
        try:
            path = os.path.join('data', 'audio')
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            raise OSError("Could not initialize audio folder: " + str(e))

        return path

    def _get_device_id(self):
        """
        Looks for the given audio device with output channels and if a near
        match containing all the given words in the input str <device_name> is
        found, returns the index of the device.
        :return dev_id: the id of the device with self.device_name as name
        """
        
        assert isinstance(self._device_name, str), "Device name needs to be set for audio recorder"

        devname = self._device_name.lower()
        dev_id = None
        p = self._pyaudio_class()

        try:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)

                if info.get('maxOutputChannels', 0) > 0:
                    name = info.get('name').lower()
                    log.debug("Found device: {}".format(name))
                    if devname in name:
                        log.debug("Selected device {}: {}".format(name, info))
                        dev_id = i
        finally:
            p.terminate()

        if dev_id is not None:
            return dev_id
        else:
            raise Exception('Device with name {} not found'.format(self._device_name))

    def _play_wav_file(self, filename: str, device_id):
        """
        Plays .wav file with given name.
        :param filename: filename of the .wav file
        :param device_id: id of the speaker device
        """
        assert isinstance(filename, str), "Filename must be a string"

        # If filename is given without the type extension, we add it
        if not filename.lower().endswith(".wav"):
            filename += ".wav"

        try:
            wf = wave.open(os.path.join(self._audio_folder_path, filename), 'rb')
        except IOError as e:
            raise IOError("Unable to read sound file: " + str(e))

        # Instantiate PyAudio.
        p = self._pyaudio_class()

        # If we are running unit tests we need to be able to get the p object
        self._p_object = p

        try:
            # Open stream.
            log.debug('NodeSpeaker, opening audio device with id {}'.format(device_id))
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True,
                            output_device_index=device_id)

            data = wf.readframes(self._chunk_size)

            while data:
                # TODO should we add volume control?
                stream.write(data)
                data = wf.readframes(self._chunk_size)

            # Stop stream.
            stream.stop_stream()
            stream.close()
        except Exception as e:
            raise Exception("NodeSpeaker: stream open or read failed: " + str(e))
        finally:
            # Close PyAudio.
            p.terminate()

    def play_wav_file(self, filename: str):
        """
        Play wav file with given filename
        :param filename: filename of .wav (can include ".wav" or not at the end)
        :return: "ok" if everything goes smoothly, otherwise the error message
        """
        assert isinstance(filename, str), "Filename must be a string"
        try:
            # Device id is refreshed/initialized before every playback event
            device_id = self._get_device_id()
            self._play_wav_file(filename, device_id)
        except Exception as e:
            raise Exception("Failed to play file {}: {}".format(filename, str(e)))

    @json_out
    def put_play_wav_file(self, filename: str):
        """
        Play wav file of given filename
        :param filename: name of the audio file
        :return: "ok" for a http response
        """
        assert isinstance(filename, str), "Filename must be a string"

        self.play_wav_file(filename)

        return "ok"

    @json_out
    def get_list_playback_devices(self):
        """
        Lists all the found playback devices
        :return: Names in a list
        """
        p = self._pyaudio_class()
        try:
            device_names = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)

                if info.get('maxOutputChannels', 0) > 0:
                    name = info.get('name')
                    device_names.append(name)
        finally:
            p.terminate()

        return device_names

    @property
    def device_name(self):
        """
        Name of the speaker device. This is used to choose the
        correct output device from all the devices seen by the system.
        """
        return self._device_name

    @device_name.setter
    def device_name(self, value):
        """
        Device name setter
        :param value: new device name
        """
        if isinstance(value, str):
            self._device_name = value
        else:
            raise Exception("NodeSpeaker: device name must be string")

    @property
    def chunk_size(self):
        """
        The patch size of sample processing
        """
        return self._chunk_size

    @chunk_size.setter
    def chunk_size(self, value):
        """
        Chunk size setter
        :param value: new chunk size
        """
        if isinstance(value, int) and value >= 1:
            self._chunk_size = value
        else:
            raise Exception("NodeSpeaker: chunk size must be an integer that's greater than zero")



