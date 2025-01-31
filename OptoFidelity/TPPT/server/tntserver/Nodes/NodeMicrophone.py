
import time
import scipy.io.wavfile as wav
import io

from tntserver.Nodes.Node import *

log = logging.getLogger(__name__)

try:
    import pyaudio
except ImportError:
    pyaudio = None  # pyaudio not available. Don't report error until pyaudio is attempted to be used.

'''
Configuration through yaml (change device_name to your own device):

- name: microphone1
  cls: NodeMicrophone
  parent: detectors
  connection: detectors
  arguments:
    device_name: bose
    rate: 44100
    chunk_size: 1024
    timeout_buffer: 3
    
- name: detectors
  cls: TnT.Detectors
  parent: ws
  connection: ws

--------------------------------
For testing one can call the following PUT request, it should return a 3 second .wav
PUT 127.0.0.1:8000/tnt/workspaces/ws/sensors/microphone1/record_audio?duration=3

'''


def to_wav(data, samplerate):
    """
    Converts data array to .wav format
    :param data: numpy.ndarray
    :param samplerate: samplerate of the data (Hz)
    :return: data array in .wav format
    """
    b = io.BytesIO()
    wav.write(b, samplerate, data)
    return bytes(b.getbuffer())


class NodeMicrophone(Node):

    def __init__(self, name, **kwargs):
        """
        Init function of the class
        :param name: name of the node
        """
        super().__init__(name)

        self._device_name = None
        # Some samples need to be ignored from the beginning of the record to avoid
        # having interference from microphone startup noise interference
        self._margin = 1024  # amount of samples ignored from the beginning of record
        self._rate = 44100  # audio datarate samples/second
        self._chunk_size = 1024  # size of the chunks recording is handled in (samples)
        # We only support one channel and portaudio enables using one channel mode with
        # a multi-channel microphone
        self._channels = 1  # number of channels to be recorded
        self._timeout_buffer = 3  # s, amount of time waited after recording length before timeout
        # For unit testing we need to be able to replace the actual pyaudio with our own dummy implementation
        self._pyaudio_class = pyaudio.PyAudio if pyaudio is not None else None
        self._latest_recording = None  # the latest recorded audio

    def _init(self, device_name, rate=None, chunk_size=None, timeout_buffer=None, **kwargs):
        """
        Another init function that's run when nodes are initialized
        :param device_name: name of the audio recording device
        :param rate: audio datarate, samples/second
        :param chunk_size: size of the chunks recording is handled in (samples)
        :param timeout_buffer: amount of time waited after recording length before timeout, s
        """

        assert isinstance(device_name, str)
        self._device_name = device_name

        # certain parameters are good to be able to give already in configuration
        if rate is not None:
            assert isinstance(rate, (int, float)) and rate >= 0
            self._rate = rate

        if chunk_size is not None:
            assert isinstance(chunk_size, int) and chunk_size >= 1
            self._chunk_size = chunk_size

        if timeout_buffer is not None:
            assert isinstance(timeout_buffer, (int, float)) and timeout_buffer >= 0
            self._timeout_buffer = timeout_buffer

    def _get_device_id(self):
        """
        Looks for the given audio device with input channels and if a near
        match containing all the given words in the input str <device_name> is
        found, returns the index of the device.
        :return: id of the device that has self._device_name as name
        """

        assert isinstance(self._device_name, str), "Device name needs to be set for audio recorder"

        devname = self._device_name.lower()
        dev_id = None
        p = self._pyaudio_class()

        try:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)

                if info.get('maxInputChannels', 0) > 0:
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

    def _record_audio(self, duration, device_id):
        """
        Records audio for given duration with given device_id
        :param duration: the recording length in seconds
        :param device_id: the id number of the device that is recorded
        :return: samples in numpy.ndarray
        """
        p = self._pyaudio_class()

        # Generate a buffer for the recorded data
        arr_len = int(self._margin + self._rate * duration * self._channels)
        arr = np.zeros([arr_len], dtype=np.int16)

        # Offset is used as pointer in the array
        offset = 0

        # Callback is called form the input stream and it defines what to
        # do with the data. It is run in a separate thread
        def callback(in_data, frame_count, _time_info, _status):
            nonlocal offset
            chunk_end = offset + frame_count * self._channels
            state = pyaudio.paContinue
            # Checking if we have recorded long enough
            if chunk_end >= arr_len:
                chunk_end = arr_len
                state = pyaudio.paComplete

            _data = np.frombuffer(in_data, dtype=np.int16, count=chunk_end - offset)
            arr[offset:chunk_end] = _data

            offset += frame_count * self._channels
            return (None, state)

        try:
            # Starting the microphone listening
            stream = p.open(format=pyaudio.paInt16,
                            channels=self._channels,
                            rate=self._rate,
                            input=True,
                            frames_per_buffer=self._chunk_size,
                            input_device_index=device_id,
                            stream_callback=callback)

            stream.start_stream()
        except Exception as e:
            p.terminate()
            raise ("NodeMicrophone: stream open failed: " + str(e))

        # NOTE: Sometimes during testing I couldn't get my audio back on from bose headphones
        # so there might be something not working in closing stream and terminating processes
        # Let's keep our eyes open for this when testin with actual system

        # Timeout mechanism
        try:
            t0 = time.time()
            while stream.is_active():
                if (time.time() - t0) > (duration + self._timeout_buffer):
                    raise Exception('Recording timed out')
                time.sleep(0.1)
            log.info('Recorded for %s seconds' % str(time.time() - t0))
        finally:
            log.info('Stopping stream')
            stream.stop_stream()
            stream.close()
            p.terminate()

        return to_wav(arr[self._margin:], self._rate)

    def record_audio(self, duration):
        """
        Records audio for the given duration with device that is set up during
        initialization. Also checks the device id.
        :param duration: length of the recording (s)
        :return: samples in numpy.ndarray
        """
        try:
            # We check the device id before each recording
            # just in case the device list has changed
            device_id = self._get_device_id()
            self._latest_recording = self._record_audio(duration, device_id)
        except Exception as e:
            log.error("Recording audio failed!")
            raise e

    @property
    @private
    def latest_recording(self):
        """
        Latest recording getter
        :return: lastest recording
        """
        return self._latest_recording

    @wav_out
    def get_latest_recording(self):
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
        return self.latest_recording

    @wav_out
    def put_record_audio(self, record_duration):
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
        self.record_audio(record_duration)
        return self.latest_recording

    @json_out
    def get_list_recording_devices(self):
        """
        List all the recording devices found in the system
        :return: Names in a list
        """
        p = self._pyaudio_class()
        try:
            device_names = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)

                if info.get('maxInputChannels', 0) > 0:
                    name = info.get('name')
                    device_names.append(name)
        finally:
            p.terminate()

        return device_names

    @json_out
    def get_device_default_sample_rate(self):
        """
        The default sample rate of the microphone
        :return: default sample rate
        """
        device_id = self._get_device_id()
        p = self._pyaudio_class()
        try:
            info = p.get_device_info_by_index(device_id)
        finally:
            p.terminate()

        return info["defaultSampleRate"]

    @property
    def device_name(self):
        """
        Name of the microphone device. This is used to choose the
        correct input device from all the devices seen by the system.
        """
        return self._device_name

    @device_name.setter
    def device_name(self, value):
        """
        Name of the microphone device. This is used to choose the
        correct input device from all the devices seen by the system.
        """
        if isinstance(value, str):
            self._device_name = value
        else:
            raise Exception("NodeMicrophone: device name must be string")

    @property
    def margin(self):
        """
        Amount of samples ignored from the beginning of the record to
        avoid microphone startup noise interference.
        """
        return self._margin

    @margin.setter
    def margin(self, value):
        """
        Amount of samples ignored from the beginning of the record to
        avoid microphone startup noise interference.
        """
        if isinstance(value, int) and value >= 0:
            self._margin = value
        else:
            raise Exception("NodeMicrophone: margin must be a non-negative integer")

    @property
    def rate(self):
        """
        Recording data rate (samples/second).
        """
        return self._rate

    @rate.setter
    def rate(self, value):
        """
        Rate setter
        :param value: new rate
        """
        if isinstance(value, (int, float)) and value >= 0:
            self._rate = value
        else:
            raise Exception("NodeMicrophone: rate must be a non-negative integer")

    @property
    def chunk_size(self):
        """
        The chunk_size size of sample processing.
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
            raise Exception("NodeMicrophone: chunk size must be an integer that's greater than one")

    @property
    def timeout_buffer(self):
        """
        Amount of time waited after recording before timeout, in seconds.
        """
        return self._timeout_buffer

    @timeout_buffer.setter
    def timeout_buffer(self, value):
        """
        Timeout buffer setter
        :param value: new timeout buffer value
        """
        if isinstance(value, (int, float)) and value >= 0:
            self._timeout_buffer = value
        else:
            raise Exception("NodeMicrophone: timeout buffer must be a non-negative number")
