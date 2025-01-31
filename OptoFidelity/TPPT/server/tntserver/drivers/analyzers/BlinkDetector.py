import logging
from typing import List, Dict

import numpy as np
from scipy.signal import find_peaks

from tntserver.drivers.cameras.camera import CameraFrame

log = logging.getLogger(__name__)


class BlinkDetector:
    def __init__(self, max_frequency: float = 5.0, noise_threshold: float = 0.05, **kwargs):
        """
        Constructor.
        :param max_frequency: Maximum blinking frequency to be detected in Hz.
        :param noise_threshold: Minimum amplitude for detected signal in the frequency spectrum.
        """

        self.max_frequency = max_frequency
        self.noise_treshold = noise_threshold

    def analyze(self, frames: List[CameraFrame]):
        return self.detect_blink_frequency(frames)

    def detect_blink_frequency(self, frames: List[CameraFrame]) -> Dict:
        """
        Get the frequency of a blinking element from a video. The input should be cropped such that there is only one
        blinking element visible.
        :param frames: List of video frames.
        :return: A results dict with the items
            'blink_frequency': The blink frequency in Hz.
        """

        timestamps = np.array([frame.timestamp for frame in frames])
        sample_spacing = float(np.mean(np.diff(timestamps)))
        sampling_rate = 1.0 / sample_spacing

        # According to the sampling theorem, the detected frequency can be at most half the sampling rate.
        nyquist_frequency = 0.5 * sampling_rate
        if self.max_frequency > nyquist_frequency:
            log.warning(f"Max frequency set too high for video framerate, "
                        f"max detectable frequency is {nyquist_frequency:.2f} Hz.")

        bw_images = [frame.mono() for frame in frames]

        min_pixels = np.amin(bw_images, axis=0)
        max_pixels = np.amax(bw_images, axis=0)

        max_brightness = np.max(max_pixels)

        if max_brightness == 0:
            log.warning("Recorded video is blank.")
            return dict(blink_frequency=0.0)

        # Get the per-pixel brightness range relative to the brightest detected pixel.
        difference = (max_pixels - min_pixels) / max_brightness

        # The distribution follows a nice sigmoid curve.
        # We cut it off at the halfway point to get a rough mask for our icon.
        icon_mask = difference > 0.5

        blink_frequency = 0.0
        if np.sometrue(icon_mask):
            # Calculate the average brightness of the pixels in the icon relative to the brightest detected pixel.
            brightness = np.array([np.mean(image[icon_mask]) for image in bw_images]) / max_brightness

            # Center the mean on the x-axis, otherwise FFT will show a spike at 0 Hz.
            brightness -= np.mean(brightness)

            # Get the frequency spectrum, divided by sample length to get sample length independent amplitudes.
            fft = np.fft.rfft(brightness) / len(timestamps)
            frequency = np.fft.rfftfreq(len(timestamps), d=sample_spacing)

            # Cut the data off at the max frequency
            indices = frequency <= self.max_frequency
            fft = fft[indices]
            frequency = frequency[indices]

            # The values are complex so take the absolute value.
            amplitude = np.abs(fft)

            peaks, properties = find_peaks(amplitude)

            if len(peaks) > 0:
                highest_peak = peaks[np.argmax(amplitude[peaks])]
                peak_ampltidude = amplitude[highest_peak]
                if peak_ampltidude > self.noise_treshold:
                    blink_frequency = frequency[highest_peak]

        return dict(blink_frequency=blink_frequency)
