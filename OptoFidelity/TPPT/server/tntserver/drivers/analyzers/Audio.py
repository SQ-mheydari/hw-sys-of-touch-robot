import numpy as np
import scipy.signal
from scipy.fftpack import fft
import math
import scipy.io.wavfile as wav
import io
import logging

log = logging.getLogger(__name__)

# Maximum audio sample value when using 16-bit sampling.
MAX_SAMPLE_VALUE_16BIT = 32767


def create_sine_wave(freq, duration, volume, sample_rate):
    """
    Create sampled sine wave as array of 16-bit integers.
    The results can be saved to WAV file using scipy.io.wavfile: wav.write("sound.wav", 44100, samples)
    :param freq: Frequency (Hz).
    :param duration: Duration of the wave (s).
    :param volume: Sound volume (in [0, 1]).
    :param sample_rate: Rate at which to sample the wave (Hz).
    :return: Sampled sine wave as numpy array.
    """
    assert isinstance(freq, (int, float))
    assert freq > 0
    assert isinstance(duration, (int, float))
    assert duration >= 0
    assert isinstance(volume, (int, float))
    assert 0.0 <= volume <= 1.0
    assert isinstance(sample_rate, (int, float))
    assert sample_rate > 0

    num_samples = int(round(duration * sample_rate))

    angular_freq = 2 * math.pi * freq

    samples = volume * MAX_SAMPLE_VALUE_16BIT * np.sin([i * angular_freq / sample_rate for i in range(num_samples)])

    return np.array(samples, dtype=np.int16)


def create_noise(duration, volume, sample_rate):
    """
    Create noise sampling.
    :param duration:Duration of the noise (s).
    :param volume: Sound volume (in [0, 1]).
    :param sample_rate: Rate at which to sample the noise (Hz).
    :return: Sampled noise as numpy array.
    """
    assert isinstance(duration, (int, float))
    assert duration >= 0
    assert isinstance(volume, (int, float))
    assert 0.0 <= volume <= 1.0
    assert isinstance(sample_rate, (int, float))
    assert sample_rate > 0

    num_samples = int(round(duration * sample_rate))

    return np.random.random_integers(-volume * MAX_SAMPLE_VALUE_16BIT,
                                     volume * MAX_SAMPLE_VALUE_16BIT, size=(num_samples,))


def calculate_fft(data: np.ndarray) -> np.ndarray:
    """
    Applies Hanning window and calculates the FFT of given data.
    Copied from Fusion library.
    :param data: Array of samples to apply FFT to.
    :return: Scaled absolute values of FFT corresponding to non-negative frequencies.
    """
    # Number of sample points
    N = len(data)

    # TODO: Should this pad to nearest power of two instead?
    if N % 2 != 0:
        data = data[:-1]
        N = len(data)

    # Apply Hanning window to entire data.
    hanning = np.hanning(N)
    data = np.multiply(hanning, data)

    # Compute FFT.
    yf = fft(data)

    # Make sure slice index is rounded to nearest number divisible by 2.
    # TODO: Improve commenting.
    # Seems that the rounding does not quite behave like is commented. I think also positive frequenceis are selected.
    # Why multiplication by 2 / N and abs()?
    yf = 2.0 / N * np.abs(yf[:int(2 * round((N / 2) / 2.))])

    return yf


def windowed_fft(signal: np.ndarray, samplerate: int, band_pass_range=None, window_len: float = 0.4) -> np.ndarray:
    """
    Calculates the FFT in short segments and filters the segments. This
    gives a more reliable results due to the continuous signal assumption.
    Adapted from Fusion library. Also applies band pass filter to the signal before FFT.
    :param signal: Array of samples of a signal.
    :param samplerate: signal sampling rate (Hz).
    :param band_pass_range: If not none, then list [min_frequency, max_frequency] used for band-pass filter.
    :param window_len: Time-domain window length (s). If zero then no windowing is used.
    :return: Mean of FFTs from each window.
    """
    # Filter first
    nyq = samplerate / 2

    if band_pass_range is not None:
        fstart = int(band_pass_range[0])
        fstop = int(band_pass_range[1])
        # "band" means bandpass, use "bandstop" for bandstop
        b, a = scipy.signal.butter(3, [fstart / nyq, fstop / nyq], 'band', analog=False)
        signal = scipy.signal.filtfilt(b, a, signal)

    # TODO: Why custom made windowing?
    # It seems that this divides the spectrum into overlapping windows where
    # calculate_fft() then applies Hanning windowing.
    # Consider using scipy stft() to apply sliding window.
    if window_len > 0:
        signal_duration = signal.size / samplerate

        if signal_duration < window_len:
            window_len = signal_duration

        len_segment = int(samplerate * window_len)  # Number of samples in one temporal window.
        num_segment = int(
            len(signal) / len_segment)  # Number of windows that can fit within the entire signal without overlap.

        if num_segment <= 0:
            num_segment = 1

        # Crop the signal so the length always matches when segmenting
        signal = signal[:num_segment * len_segment]

        # 50% overlap
        overlap = int(len_segment / 2)
        # Dividing signal in overlapping segments
        segments = [signal[i:i + len_segment]
                    for i in range(0, len(signal)-overlap, len_segment - overlap)]
        final = [None] * len(segments)

        for idx, seg in enumerate(segments):
            final[idx] = calculate_fft(seg)

        # Finding the max values found in any of the windows
        fft_result = np.max(final, axis=0)
    else:
        fft_result = calculate_fft(signal)

    return fft_result


def get_frequency_vector(data, rate):
    """
    Creates a list of frequencies from the given FFT with the
    correct resolution
    Copied from Fusion library.
    :param data: Result of FFT.
    :param rate: Sampling rate (Hz).
    :return: Array of frequencies.
    """
    # Dominant frequencies are at indices of bins with the
    # greatest magnitude
    T = 1 / rate  # Samples per second
    N = len(data)

    # resolution = rate / (2 * N)  # Bin width
    # print("Frequency resolution is " + str(resolution) + " Hz")

    frequencies = np.linspace(0.0, 1.0 / (2.0 * T), N)

    return frequencies


def find_frequency_peaks(data: np.ndarray, rate: int, num_peaks: int = 5, window_size: int = 7):
    """
    Find dominant frequencies by finding peaks in FFT data.
    Copied from Fusion library.
    :param data: Result of FFT as returned by windowed_fft().
    :param rate: Sampling rate in (Hz).
    :param num_peaks: The number of peaks that should be searched for.
    :param window_size: Length of the frequency buffer in which a peak must be the largest value.
    :return: List of dominant frequencies and list of the corresponding intensities.
    """

    frequencies = get_frequency_vector(data, rate)
    peak_ind = []
    indices = data.argsort()[::-1]
    scope = int(window_size / 2)

    # Slide a window over the spectrum.
    # If the value in index is the largest inside the window, it is a true peak.
    for index in indices:
        subset = data[index - scope:index + scope + 1]

        if len(subset) > 0 and math.isclose(np.amax(subset), data[index], abs_tol=0.0005):
            peak_ind.append(int(index))

        if len(peak_ind) is num_peaks:
            break

    # for i in range(len(peak_ind)):
    #     print(str(i + 1) + ". Index: " + str(peak_ind[i]) +
    #           ", frequency: " + str(frequencies[peak_ind[i]]) +
    #           " Hz, value: " + str(data[peak_ind[i]]))

    return [[frequencies[i] for i in peak_ind], [data[i] for i in peak_ind]]


class Audio:
    """
    Analyzer for analyzing audio signals.
    """

    def __init__(self, **kwargs):
        # Currently this analyzer has not state.
        pass

    def find_frequency_peaks(self, value, **kwargs):
        """
        Find frequency peaks in given time-domain audio sampling.
        :param value: sound in wav formatted bytes (same as NodeMicrophone format). (The name of this parameter
        is dictated by client REST api functions and cannot be refactored)
        :return: a list containing a list of frequencies (Hz) and a list of corresponding spectral intensities.
        """
        # Getting samples from bytes
        try:
            sample_rate, samples = wav.read(io.BytesIO(value))
        except Exception as e:
            raise Exception("Audio analyzer: cannot read wav bytes: " + str(e))

        # The assumption is that we are working with 16-bit integers
        if samples.dtype != np.int16:
            raise TypeError("Audio analyzer: wav data type is not int16 but {}".format(samples.dtype.name))

        # If there are more than one channel in wav, we'll use only the first to analysis
        if len(samples.shape) > 1 and samples.shape[1] > 1:
            samples = samples[:, 0]
            log.warning("Audio analyzer: .wav data has more than one channel, only using the first one")

        num_peaks = kwargs.get("num_peaks", 5)
        peak_find_freq_window_size = kwargs.get("peak_find_freq_window_size", 7)
        fft_temporal_window_length = kwargs.get("fft_temporal_window_length", 0.4)
        band_pass_range = kwargs.get("band_pass_range", [80, 16500])

        samples_fft = windowed_fft(np.array(samples), sample_rate, band_pass_range, fft_temporal_window_length)

        return find_frequency_peaks(samples_fft, sample_rate, num_peaks, peak_find_freq_window_size)
