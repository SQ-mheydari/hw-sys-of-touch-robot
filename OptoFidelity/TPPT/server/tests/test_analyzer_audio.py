from tntserver.drivers.analyzers.Audio import *
from tntserver.Nodes.TnT.Analyzer import Analyzer
import json
import pytest


REL_FREQUENCY_MARGIN = 0.01


def to_wav(data_1, samplerate, data_2 = None):
    """
    Converts data array to .wav format. If there are two arrays,
    creates stereo wav.
    :param data_1: numpy.ndarray
    :param samplerate: samplerate of the data (Hz)
    :param data_2: numpy.ndarray, used for stereo sound as channel 2
    :return: data array in .wav format
    """
    if data_2 is None:
        data = data_1
    else: # stereo audio
        data = np.vstack((data_1, data_2)).T

    b = io.BytesIO()
    wav.write(b, samplerate, data)

    return bytes(b.getbuffer())


def test_create_sine_wave():
    """
    Test creating a sine wave.
    """
    samples = create_sine_wave(2.0, 1.0, 1.0, 10)
    reference = [0, 31163, 19259, -19259, -31163, 0, 31163, 19259, -19259, -31163]
    assert np.allclose(samples, reference)


def test_find_frequency_peaks():
    """
    Test obtaining frequency of sinusoidal wave with background noise.
    """
    # Test close to human hearing range of signals.
    for freq in [20, 1000, 20000]:
        sample_rate = 44100
        duration = 1.0

        noise_level = 0.5  # In range [0, 1].

        samples = create_sine_wave(freq, duration, 1 - noise_level, sample_rate)

        samples += create_noise(duration, noise_level, sample_rate)

        samples_fft = windowed_fft(samples, sample_rate, [20, 20000])
        frequencies, intensities = find_frequency_peaks(samples_fft, sample_rate)

        #wavfile.write("sound{}.wav".format(freq), 44100, samples)
        #print(frequencies)

        # Make sure the frequency is the first in list.
        assert abs(freq - frequencies[0]) < freq * REL_FREQUENCY_MARGIN

        # Make sure the first frequency has significantly bigger intensity than that due to noise.
        # Appropriate intensity threshold depends on noise_level.
        for intensity in intensities[1:]:
            assert intensities[0] > intensity * 2


def test_windowing():
    """
    Test signal window that is longer than duration.
    """
    # Test close to human hearing range of signals.
    for freq in [20, 1000, 20000]:
        sample_rate = 44100
        duration = 1.0

        noise_level = 0.5  # In range [0, 1].

        samples = create_sine_wave(freq, duration, 1 - noise_level, sample_rate)

        samples += create_noise(duration, noise_level, sample_rate)

        samples_fft = windowed_fft(samples, sample_rate, [20, 20000], window_len=2.0)
        frequencies, intensities = find_frequency_peaks(samples_fft, sample_rate)

        # Make sure the frequency is the first in list.
        assert abs(freq - frequencies[0]) < freq * REL_FREQUENCY_MARGIN

        # Make sure the first frequency has significantly bigger intensity than that due to noise.
        # Appropriate intensity threshold depends on noise_level.
        for intensity in intensities[1:]:
            assert intensities[0] > intensity * 2


def test_find_frequency_peaks2():
    """
    Test obtaining frequency of sinusoidal wave with background noise.
    In this case the sine wave covers only the middle part of the audio clip.
    """
    # Test close to human hearing range of signals.
    for freq in [20, 1000, 20000]:

        sample_rate = 44100
        duration = 1.0

        noise_level = 0.1  # In range [0, 1].

        samples = create_sine_wave(freq, duration, 1 - noise_level, sample_rate)

        noise = create_noise(duration, noise_level, sample_rate)
        noise = np.array(noise, dtype=np.int16)

        samples += noise

        samples = np.append(noise, samples)
        samples = np.append(samples, noise)

        samples_fft = windowed_fft(samples, sample_rate, [20, 20000])
        frequencies, intensities = find_frequency_peaks(samples_fft, sample_rate)

        # wavfile.write("sound.wav", 44100, samples)
        # print(frequencies)

        # Make sure the frequency is the first in list.
        assert abs(freq - frequencies[0]) < freq * REL_FREQUENCY_MARGIN

        # Make sure the first frequency has significantly bigger intensity than that due to noise.
        # Appropriate intensity threshold depends on noise_level.
        for intensity in intensities[1:]:
            assert intensities[0] > intensity * 5


def test_find_frequency_peaks3():
    """
    Test that multiple frequencies are resolved from superimposed signals.
    """
    sine_freqs = [500, 2000, 10000]
    sine_volumes = [0.3, 0.2, 0.1]

    sample_rate = 44100
    duration = 1.0

    # Create zero wave as base sampling.
    samples = create_sine_wave(1, duration, 0, sample_rate)

    # Superimpose sine waves.
    for i, freq in enumerate(sine_freqs):
        samples += create_sine_wave(freq, duration, sine_volumes[i], sample_rate)

    samples_fft = windowed_fft(samples, sample_rate, [20, 20000])
    frequencies, intensities = find_frequency_peaks(samples_fft, sample_rate)

    # Make sure the frequencies are found in correct order.
    for i, freq in enumerate(sine_freqs):
        assert abs(freq - frequencies[i]) < freq * REL_FREQUENCY_MARGIN

    # Make sure the first frequencies have significantly bigger intensity than the rest.
    # Appropriate intensity threshold is somewhat arbitrary as there is no noise in this test.
    for i, freq in enumerate(sine_freqs):
        for intensity in intensities[len(sine_freqs):]:
            assert intensities[i] > intensity * 5


def test_audio_analyzer_node():
    """
    Test Analyzer node that has Audio driver.
    """
    analyzer = Analyzer("Audio analyzer")
    analyzer._init(driver="Audio")

    freq = 1000
    sample_rate = 44100
    duration = 1.0

    wav_bytes = to_wav(create_sine_wave(freq, duration, 0.8, sample_rate), sample_rate)

    # Analyzer nodes expose REST API via handle_path method.
    frequencies_json = analyzer.handle_path("put", "find_frequency_peaks", value=wav_bytes)
    frequencies = json.loads(frequencies_json[1].decode("utf-8"))

    assert len(frequencies[0]) == 5
    assert abs(freq - frequencies[0][0]) < freq * REL_FREQUENCY_MARGIN

    # Test num_peaks parameter.
    frequencies_json = analyzer.handle_path("put", "find_frequency_peaks", value=wav_bytes, num_peaks=1)
    frequencies = json.loads(frequencies_json[1].decode("utf-8"))

    assert len(frequencies[0]) == 1
    assert abs(freq - frequencies[0][0]) < freq * REL_FREQUENCY_MARGIN

    # Test peak_find_freq_window_size parameter.
    frequencies_json = analyzer.handle_path("put", "find_frequency_peaks", value=wav_bytes,
                                            peak_find_freq_window_size=10)
    frequencies = json.loads(frequencies_json[1].decode("utf-8"))

    assert abs(freq - frequencies[0][0]) < freq * REL_FREQUENCY_MARGIN

    # Test fft_temporal_window_length parameter.
    frequencies_json = analyzer.handle_path("put", "find_frequency_peaks", value=wav_bytes,
                                            fft_temporal_window_length=0.5)
    frequencies = json.loads(frequencies_json[1].decode("utf-8"))

    assert abs(freq - frequencies[0][0]) < freq * REL_FREQUENCY_MARGIN

    # Test band_pass_range parameter. Test band that contains the signal.
    frequencies_json = analyzer.handle_path("put", "find_frequency_peaks", value=wav_bytes,
                                            band_pass_range=[500, 1500])
    frequencies = json.loads(frequencies_json[1].decode("utf-8"))

    assert abs(freq - frequencies[0][0]) < freq * REL_FREQUENCY_MARGIN

    # Test band_pass_range parameter. Test band that does not contain the signal.
    frequencies_json = analyzer.handle_path("put", "find_frequency_peaks", value=wav_bytes,
                                            band_pass_range=[50, 100])
    frequencies = json.loads(frequencies_json[1].decode("utf-8"))

    assert abs(freq - frequencies[0][0]) > freq * REL_FREQUENCY_MARGIN

def test_two_channels():
    """
    Test that if audio has two channels, only the first one is analyzed
    """
    analyzer = Analyzer("Audio analyzer")
    analyzer._init(driver="Audio")
    freq_1 = 100
    freq_2 = 367
    duration = 1
    volume = 0.8
    sample_rate = 44100

    data_1 = create_sine_wave(freq_1, duration, volume, sample_rate)
    data_2 = create_sine_wave(freq_2, duration, volume, sample_rate)
    wav_bytes = to_wav(data_1=data_1, data_2=data_2, samplerate=sample_rate)

    frequencies_json = analyzer.handle_path("put", "find_frequency_peaks", value=wav_bytes)
    frequencies = json.loads(frequencies_json[1].decode("utf-8"))

    assert len(frequencies[0]) == 5
    assert abs(freq_1 - frequencies[0][0]) < freq_1 * REL_FREQUENCY_MARGIN

def test_data_type_error():
    """
    Test that TypeError is raised if wrong datatype is used for data array
    """
    analyzer = Analyzer("Audio analyzer")
    analyzer._init(driver="Audio")
    freq = 100
    duration = 1
    volume = 0.8
    sample_rate = 44100

    data_arr = create_sine_wave(freq, duration, volume, sample_rate)
    data_arr = data_arr.astype("int32")
    wav_bytes = to_wav(data_arr, sample_rate)

    with pytest.raises(TypeError):
        _ = analyzer.handle_path("put", "find_frequency_peaks", value=wav_bytes)


