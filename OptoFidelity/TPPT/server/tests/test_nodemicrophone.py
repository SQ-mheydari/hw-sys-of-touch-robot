from tntserver.Nodes.NodeMicrophone import *
import pytest


@json_out
def to_jsonout(data_input):
    """
    Changes input to @json_out function format
    :param data_input: data to be converted
    :return: input in @json_out format tuple
    """
    return data_input


# The duration of the test recording
RECORD_DURATION = 1  # s
RECORD_TIMEOUT_DURATION = 0.2  # s

# Recording parameters. The values are given in this scope because they are needed
# also in PyaudioStub class. These need to be the same as NodeMicrophone default values
DEFAULT_MARGIN = 1024  # samples
DEFAULT_CHUNK_SIZE = 1024  # samples
DEFAULT_RATE = 44100
DEFAULT_CHANNELS = 1


class Stream:
    """
    Stub for stream
    """

    def __init__(self, stream_callback, test_timeout):
        """
        Init function
        :param stream_callback: the callback function for stream
        :param timeout: if False we are testing recording function,
        if True we are testing timeout function
        """

        self._time_info = None  # dummy value for callback function
        self._status = None  # dummy value for callback function

        self._stream_callback = stream_callback
        self._is_active = False
        self._test_timeout = test_timeout

    def start_stream(self):
        """
        Stub for starting stream. Runs the callback function with properly sized data chunks
        """

        # The record duration depends on if we are testing timeout or not
        if not self._test_timeout:
            duration = RECORD_DURATION
        else:
            duration = RECORD_TIMEOUT_DURATION

        # Calculating how may samples we need to add to make the stream "full"
        record_samples_len = int(DEFAULT_MARGIN + DEFAULT_RATE * duration * DEFAULT_CHANNELS)
        stream_samples_len = int(np.ceil(record_samples_len / DEFAULT_CHUNK_SIZE) * DEFAULT_CHUNK_SIZE)
        chunk_fill = stream_samples_len - record_samples_len

        buffer = create_wave_input(duration, chunk_fill, remove_margin=False)

        self._is_active = True
        start_offset = 0

        # Feeding the data to callback function in correct data chunks
        for i in range(stream_samples_len):
            end_offset = (i + 1) * DEFAULT_CHUNK_SIZE
            self._stream_callback(buffer[start_offset:end_offset], DEFAULT_CHUNK_SIZE, self._time_info, self._status)
            start_offset = end_offset

        # If we are testing timeout we need to have internal state as if the recording hasn't finished
        if not self._test_timeout:
            self._is_active = False
        else:
            self._is_active = True

    def stop_stream(self):
        """
        Stub for stop_stream
        """
        pass

    def is_active(self):
        """
        Stub for is_active
        """
        return self._is_active

    def close(self):
        """
        Stub for close
        """
        pass


class PyaudioStub:
    """
    Stub for Pyaudio class
    """

    def __init__(self):
        # NOTE! _input_devices and _input_device_list need to contain the same input devices!
        self._input_devices = [{"name": "Input device: test_input",
                                "maxInputChannels": 2,
                                "defaultSampleRate": 33100},
                               {"name": "Input device: bose",
                                "maxInputChannels": 2,
                                "defaultSampleRate": 44100},
                               {"name": "Output device: speaker",
                                "maxOutputChannels": 2,
                                "defaultSampleRate": 44100}
                               ]
        self._input_device_list = ["Input device: test_input", "Input device: bose"]

        self.paContinue = None  # Dummy value
        self.paComplete = None  # Dummy value

        self.test_timeout = False

    def open(self, format, channels, rate, input, frames_per_buffer,
             input_device_index, stream_callback):
        """
        Stub for stream.open()
        :param format: not used
        :param channels: not used
        :param rate: not used
        :param input: not used
        :param frames_per_buffer: not used
        :param input_device_index: not used
        :param stream_callback: stream callback function
        :return: Stream stub
        """
        # Checking that values are correct even though we are not using them
        assert format == pyaudio.paInt16
        assert channels == DEFAULT_CHANNELS
        assert rate == DEFAULT_RATE
        assert input
        assert frames_per_buffer == DEFAULT_CHUNK_SIZE
        assert isinstance(input_device_index, int)

        return Stream(stream_callback, self.test_timeout)

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

    def terminate(self):
        """
        stub version of pyaudio terminate()
        """
        pass


class PyaudioStubTimeOut(PyaudioStub):

    def __init__(self):
        super().__init__()
        self.test_timeout = True

    def open(self, format, channels, rate, input, frames_per_buffer,
             input_device_index, stream_callback):
        """
        Stub for stream.open()
        :param format: not used
        :param channels: not used
        :param rate: not used
        :param input: not used
        :param frames_per_buffer: not used
        :param input_device_index: not used
        :param stream_callback: stream callback function
        :return: Stream stub
        """
        # Checking that values are correct even though we are not using them
        assert format == pyaudio.paInt16
        assert channels == DEFAULT_CHANNELS
        assert rate == DEFAULT_RATE
        assert input
        assert frames_per_buffer == DEFAULT_CHUNK_SIZE
        assert isinstance(input_device_index, int)

        return Stream(stream_callback, self.test_timeout)


def create_wave_input(record_duration, chunk_fill=0, remove_margin=False):
    """
    Creates sinusoidal signal to mimic audio recording
    :param chunk_fill: amount of samples that are added to the actual recording size
    :param remove_margin: if True the DEFAULT_MARGIN is removed from the beginning of the
    array if False it is included
    :return: one-dimensional array of np.int16 values
    """
    amplitude = 30
    arr_len = int(DEFAULT_MARGIN + DEFAULT_RATE * record_duration * DEFAULT_CHANNELS + chunk_fill)
    array = np.zeros([arr_len], dtype=np.int16)
    for i in range(arr_len):
        next_value = np.int16(np.sin(np.pi * i / 1000) * amplitude)
        array[i] = next_value

    if remove_margin:
        return array[DEFAULT_MARGIN:]
    else:
        return array


def init_recorder(device_name=None, test_timeout=False):
    """
    Initialize audiorecorder object and replace pyaudio class with
    stub version of pyaudio
    :param device_name: name of the device, if not given "test_input" is used
    :return: NodeMicrophone object that is good for testing
    """
    recorder = NodeMicrophone("nodeaudiorecorder")
    if device_name is None:
        recorder._init("test_input")
    else:
        recorder._init(device_name)
    if not test_timeout:
        recorder._pyaudio_class = PyaudioStub
    else:  # we are testing timeout
        recorder._pyaudio_class = PyaudioStubTimeOut

    return recorder


def test_init_error():
    """
    Test that init function fails if device_name not given correctly
    """
    recorder = NodeMicrophone("nodeaudiorecorder")
    with pytest.raises(Exception):
        recorder._init()
    with pytest.raises(Exception):
        recorder._init(1234)


def test_default_values():
    """
    Test initilization and check that default values are ok
    """
    recorder = init_recorder()
    assert recorder._margin == DEFAULT_MARGIN
    assert recorder._rate == DEFAULT_RATE
    assert recorder._chunk_size == DEFAULT_CHUNK_SIZE
    assert recorder._channels == DEFAULT_CHANNELS
    assert recorder._timeout_buffer == 3


def test_get_list_recording_devices():
    """
    Test get_list_recording_devices
    """
    recorder = init_recorder()
    devices_from_code = recorder.get_list_recording_devices()
    devices_ref = to_jsonout(recorder._pyaudio_class()._input_device_list)

    assert devices_from_code == devices_ref


def test_get_device_default_sample_rate():
    """
    Test get_device_defaul_sample_rate
    """
    recorder = init_recorder()
    sample_rate_from_code = recorder.get_device_default_sample_rate()
    sample_rate_ref = to_jsonout(recorder._pyaudio_class()._input_devices[0]["defaultSampleRate"])

    assert sample_rate_from_code == sample_rate_ref


@pytest.mark.skipif(pyaudio is None, reason="pyaudio not installed")
def test_record_audio():
    """
    test record_audio with a sinusoidal wave and default parameters
    """
    recorder = init_recorder()
    wave_ref = to_wav(create_wave_input(RECORD_DURATION, remove_margin=True), DEFAULT_RATE)
    recorder.record_audio(RECORD_DURATION)
    wave_from_code = recorder.latest_recording

    assert len(wave_ref) == len(wave_from_code)
    assert wave_ref == wave_from_code


def test_timeout():
    recorder = init_recorder(test_timeout=True)
    # changing the buffer value to make things faster
    recorder.timeout_buffer = 0  # s

    with pytest.raises(Exception):
        recorder.record_audio(RECORD_TIMEOUT_DURATION)


def test_device_name_property():
    """
    Test device_name setter, getter and type check
    """
    recorder = init_recorder()
    new_name_str = "test_input_2"
    new_name_int = 1234

    # Ensuring we are not testing with default value
    assert new_name_str != recorder._device_name

    # test setters and getters
    recorder.device_name = new_name_str
    assert recorder._device_name == new_name_str
    assert recorder.device_name == new_name_str

    # test wrong type exceptions
    with pytest.raises(Exception):
        recorder.device_name = new_name_int
    with pytest.raises(Exception):
        recorder.device_name = None


def test_margin_property():
    """
    Test margin setter, getter and type check
    """
    recorder = init_recorder()
    new_margin_int = 2000
    new_margin_float = 245.56
    new_margin_str = "not_int"
    new_margin_zero = 0
    new_margin_negative = -3

    # Ensuring we are not testing with default values
    assert not np.isclose(new_margin_int, recorder._margin)
    assert not np.isclose(new_margin_float, recorder._margin)

    # test setters and getters
    recorder.margin = new_margin_int
    assert recorder._margin == new_margin_int
    assert recorder.margin == new_margin_int
    # boundary value
    recorder.margin = new_margin_zero
    assert recorder._margin == new_margin_zero
    assert recorder.margin == new_margin_zero

    # test wrong type exceptions
    with pytest.raises(Exception):
        recorder.margin = new_margin_str
    with pytest.raises(Exception):
        recorder.margin = new_margin_float
    with pytest.raises(Exception):
        recorder.margin = new_margin_negative
    with pytest.raises(Exception):
        recorder.margin = None


def test_rate_property():
    """
    Test rate setter, getter and type check
    """
    recorder = init_recorder()
    new_rate_int = 2000
    new_rate_float = 2000.45
    new_rate_str = "not_int_nor_float"
    new_rate_zero = 0
    new_rate_negative = -2000

    # Ensuring we are not testing with default values
    assert not np.isclose(new_rate_int, recorder._rate)
    assert not np.isclose(new_rate_float, recorder._rate)

    # test setters and getters
    recorder.rate = new_rate_int
    assert recorder._rate == new_rate_int
    assert recorder.rate == new_rate_int
    recorder.rate = new_rate_float
    assert recorder._rate == new_rate_float
    assert recorder.rate == new_rate_float
    # boundary value
    recorder.rate = new_rate_zero
    assert recorder._rate == new_rate_zero
    assert recorder.rate == new_rate_zero

    # test wrong type exceptions
    with pytest.raises(Exception):
        recorder.rate = new_rate_str
    with pytest.raises(Exception):
        recorder.rate = new_rate_negative
    with pytest.raises(Exception):
        recorder.rate = None


def test_chunk_size_property():
    """
    Test chunk_size setter, getter and type check
    """
    recorder = init_recorder()
    new_chunk_size_int = 3
    new_chunk_size_float = 3.5
    new_chunk_size_str = "not_int"
    new_chunk_size_one = 1
    new_chunk_size_zero = 0
    new_chunk_size_negative = -3

    # Ensuring we are not testing with default values
    assert not np.isclose(new_chunk_size_int, recorder._chunk_size)
    assert not np.isclose(new_chunk_size_float, recorder._chunk_size)

    # test setters and getters
    recorder.chunk_size = new_chunk_size_int
    assert recorder._chunk_size == new_chunk_size_int
    assert recorder.chunk_size == new_chunk_size_int
    # boundary value
    recorder.chunk_size = new_chunk_size_one
    assert recorder._chunk_size == new_chunk_size_one
    assert recorder.chunk_size == new_chunk_size_one

    # test wrong type exceptions
    with pytest.raises(Exception):
        recorder.chunk_size = new_chunk_size_float
    with pytest.raises(Exception):
        recorder.chunk_size = new_chunk_size_str
    with pytest.raises(Exception):
        recorder.chunk_size = new_chunk_size_zero
    with pytest.raises(Exception):
        recorder.chunk_size = new_chunk_size_negative
    with pytest.raises(Exception):
        recorder.chunk_size = None


def test_timeout_buffer_property():
    """
    Test timeout_buffer setter, getter and type check
    """
    recorder = init_recorder()
    new_timeout_buffer_int = 5
    new_timeout_buffer_float = 5.5
    new_timeout_buffer_str = "not_int_nor_float"
    new_timeout_buffer_zero = 0
    new_timeout_buffer_negative = -5

    # Ensuring we are not testing with default values
    assert not np.isclose(new_timeout_buffer_int, recorder._timeout_buffer)
    assert not np.isclose(new_timeout_buffer_float, recorder._timeout_buffer)

    # test setters and getters
    recorder.timeout_buffer = new_timeout_buffer_int
    assert recorder._timeout_buffer == new_timeout_buffer_int
    assert recorder.timeout_buffer == new_timeout_buffer_int
    recorder.timeout_buffer = new_timeout_buffer_float
    assert recorder._timeout_buffer == new_timeout_buffer_float
    assert recorder.timeout_buffer == new_timeout_buffer_float
    # boundary value
    recorder.timeout_buffer = new_timeout_buffer_zero
    assert recorder._timeout_buffer == new_timeout_buffer_zero
    assert recorder.timeout_buffer == new_timeout_buffer_zero

    # test wrong type exceptions
    with pytest.raises(Exception):
        recorder.timeout_buffer = new_timeout_buffer_str
    with pytest.raises(Exception):
        recorder.timeout_buffer = new_timeout_buffer_negative
    with pytest.raises(Exception):
        recorder.timeout_buffer = None
