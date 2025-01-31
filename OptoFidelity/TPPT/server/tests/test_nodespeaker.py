from tntserver.Nodes.NodeSpeaker import *
import pytest
import math
import scipy.io.wavfile as wav
import uuid

DEFAULT_SAMPLE_RATE = 44100


def create_sine_wave(freq, duration, volume):
    """
    Create sampled sine wave as array of 16-bit integers
    :param freq: Frequency (Hz)
    :param duration: Duration of the wave (s)
    :param volume: Sound volume (in [0, 1])
    :param sample_rate: Rate at which to sample the wave (Hz)
    :return: Sampled sine wave as numpy array
    """

    # Maximum audio sample value when using 16-bit sampling.
    max_sample_value_16bit = 32767
    num_samples = int(round(duration * DEFAULT_SAMPLE_RATE))
    angular_freq = 2 * math.pi * freq
    samples = volume * max_sample_value_16bit * np.sin(
        [i * angular_freq / DEFAULT_SAMPLE_RATE for i in range(num_samples)])

    return np.array(samples, dtype=np.int16)


@json_out
def to_jsonout(data_input):
    """
    Changes input to @json_out function format
    :param data_input: data to be converted
    :return: input in @json_out format tuple
    """
    return data_input


class Stream:
    """
    Stub for data Stream
    """

    def __init__(self):
        self.data = b''  # the data that goes to the speaker

    def write(self, data):
        """
        Stub for write
        :param data: data to be written to stream
        """
        self.data += data

    def stop_stream(self):
        """
        Stop stream stub
        """
        pass

    def close(self):
        """
        Close stub
        """
        pass


class PyaudioStub:
    """
    Stub for Pyaudio class
    """

    def __init__(self):
        # NOTE! _input_devices and _input_device_list need to contain the same input devices!
        self._input_devices = [{"name": "Output device: test_output",
                                "maxInputChannels": 0,
                                "maxOutputChannels": 2},
                               {"name": "Output device: bose",
                                "maxInputChannels": 0,
                                "maxOutputChannels": 2},
                               {"name": "Input device: microphone",
                                "maxOutputChannels": 0,
                                "maxInputChannels": 2,
                                "defaultSampleRate": 44100}
                               ]
        self._input_device_list = ["Output device: test_output", "Output device: bose"]
        self.stream = None

    def terminate(self):
        """
        stub version of pyaudio terminate()
        """
        pass

    def get_device_count(self):
        """
        stub version of pyaudio get_device_count()
        """
        return len(self._input_devices)

    def get_device_info_by_index(self, index):
        """
        stub version of pyaudio get_device_info_by_index()
        """
        return self._input_devices[index]

    def open(self, format, channels, rate, output, output_device_index):
        """
        Stub for opening stream
        :param format: not used
        :param channels: not used
        :param rate: not used
        :param output: not used
        :param output_device_index: not used
        :return: stream stub object
        """
        self.stream = Stream()
        return self.stream

    def get_format_from_width(self, *args):
        """
        get_format_from_width stub
        """
        pass


def init_speaker(device_name=None):
    """
    Initialize audioplayback object and replace pyaudio class with
    stub version of pyaudio
    :param device_name: name of the device, if not given "test_output" is used
    :return: NodeSpeaker object that is good for testing
    """

    # init speaker
    speaker = NodeSpeaker("nodeaudioplayback")
    if device_name is None:
        speaker._init("test_output", test=True)
    else:
        speaker._init(device_name, test=True)

    speaker._pyaudio_class = PyaudioStub
    speaker._audio_folder_path = ""

    return speaker


def test_play_wav_file():
    """
    Test _play_wav_file by creating a temporary .wav file a playing it with testing stubs
    """
    speaker = init_speaker()

    # Creating a sine wave and saving it to wav with unique filename
    samples_orig = create_sine_wave(freq=100, duration=3, volume=0.5)
    filename = str(uuid.uuid4()) + ".wav"
    wav.write(filename, DEFAULT_SAMPLE_RATE, samples_orig)

    # Running the play function
    speaker._play_wav_file(filename, 1)

    # Removing the temporary file
    try:
        os.remove(filename)
    except OSError:
        raise OSError("Failed to remove temorary .wav file: " + filename)

    # Comparing input and output
    bytes_from_code = speaker._p_object.stream.data
    assert samples_orig.tobytes() == bytes_from_code


def test_init_error():
    """
    Test that init function fails if device_name is not given correctly
    """
    speaker = NodeSpeaker("nodeaudioplayback")
    with pytest.raises(Exception):
        speaker._init()
    with pytest.raises(Exception):
        speaker._init(1234)


def test_get_list_playback_devices():
    """
    Test get_list_recording_devices
    """
    speaker = init_speaker()
    devices_from_code = speaker.get_list_playback_devices()
    devices_ref = to_jsonout(speaker._pyaudio_class()._input_device_list)

    assert devices_from_code == devices_ref


def test_play_wav_file_error():
    """
    Test assertion error of play wav file
    """
    speaker = init_speaker()
    with pytest.raises(Exception):
        speaker.play_wav_file(filename=1223)


def test_device_name_property():
    """
    Test device_name setter, getter and type check
    """
    speaker = init_speaker()
    new_name_str = "test_output_2"
    new_name_int = 1234

    # Ensuring we are not testing with default value
    assert new_name_str != speaker._device_name

    # test setters and getters
    speaker.device_name = new_name_str
    assert speaker._device_name == new_name_str
    assert speaker.device_name == new_name_str

    # test wrong type exceptions
    with pytest.raises(Exception):
        speaker.device_name = new_name_int
    with pytest.raises(Exception):
        speaker.device_name = None


def test_chunk_size_property():
    """
    Test chunk_size setter, getter and type check
    """
    speaker = init_speaker()
    new_chunk_size_int = 3
    new_chunk_size_float = 3.5
    new_chunk_size_str = "not_int"
    new_chunk_size_one = 1
    new_chunk_size_zero = 0
    new_chunk_size_negative = -3

    # Ensuring we are not testing with default values
    assert not np.isclose(new_chunk_size_int, speaker._chunk_size)
    assert not np.isclose(new_chunk_size_float, speaker._chunk_size)

    # test setters and getters
    speaker.chunk_size = new_chunk_size_int
    assert speaker._chunk_size == new_chunk_size_int
    assert speaker.chunk_size == new_chunk_size_int
    # boundary value
    speaker.chunk_size = new_chunk_size_one
    assert speaker._chunk_size == new_chunk_size_one
    assert speaker.chunk_size == new_chunk_size_one

    # test wrong type exceptions
    with pytest.raises(Exception):
        speaker.chunk_size = new_chunk_size_float
    with pytest.raises(Exception):
        speaker.chunk_size = new_chunk_size_str
    with pytest.raises(Exception):
        speaker.chunk_size = new_chunk_size_zero
    with pytest.raises(Exception):
        speaker.chunk_size = new_chunk_size_negative
    with pytest.raises(Exception):
        speaker.chunk_size = None
