"""
API tests used for testing generated TnT Client.
Call each method and property and make sure the calls are successful. Check that parameter values that
end up in server side are correct and return values passed to client side are correct.

Requirements: TnT Client
"""
try:
    from tntclient.tnt_client import TnTClient, TnTDutPoint
    from tntclient.tnt_dut_positioning_client import TnTDUTPositioningClient
    from tntclient.tnt_surface_probe_client import TnTSurfaceProbeClient
except ImportError:
    print("TnT Client not found!")

try:
    from tntclient.tnt_hsup_client import *
except ImportError:
    print("HSUP Client not found. Can't run HSUP API tests.")

import math
import numpy as np
import io
import threading

try:
    import scipy.io.wavfile as wav
except ImportError:
    print("wav package not found!")


def xyz_to_frame(x, y, z):
    m = np.matrix(np.eye(4))
    m.A1[3] = float(x)
    m.A1[7] = float(y)
    m.A1[11] = float(z)
    return m


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


def test_audio_analyzer():
    """
    Test audio analyzer by trying to find frequency peaks from generated audio.
    """
    tntclient = TnTClient()

    freq = 1000
    sample_rate = 44100
    duration = 1.0
    wav_bytes = to_wav(create_sine_wave(freq, duration, 0.8, sample_rate), sample_rate)

    audioanalyzer = tntclient.audio_analyzer("audio_analyzer")

    result = audioanalyzer.find_frequency_peaks(wav_bytes)

    result_ref = [[1000.1133915409911, 3000.3401746229733, 5000.566957704956, 7000.793740786938, 3800.4308878557663], [13105.727696698583, 0.1251570566221291, 0.059840390389004544, 0.054344623770654646, 0.04972937311367424]]
    assert np.allclose(result[0], result_ref[0])
    assert np.allclose(result[1], result_ref[1])


def test_camera():
    """
    Baseic camera API tests for taking stills and initializing stream.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    camera = tntclient.camera("Camera1")

    # Test taking still image.
    camera.open()
    camera.close()
    image = camera.take_still()
    image = camera.take_still("png", 640, 480, 1.0, True, 0.5, 0.1)

    # Test setting camera parameters.
    camera.set_parameters({"exposure": 1.0, "gain": 0.4})
    camera.set_parameter("exposure", 5000.0)  # In this API exposure is in microseconds.
    result = camera.get_parameters({"exposure": None})
    print(result)  # This might not be exactly the set value because camera has some limitations.
    result = camera.get_parameter("exposure")
    print(result)
    camera.set_parameters({"exposure": 2.0})
    camera.set_parameter("exposure", 5000.0)

    # Test streaming.
    camera.start_continuous()
    camera.stop_continuous()
    camera.start_continuous(640, 480, 1.0, True, 0.5, 0.1, 0.8, 'linear', 'SW')
    camera.stop_continuous()

    # Test getting focus height.
    result = camera.focus_height()
    print(result)


def test_camera_ocr_and_icon_detection(dut_name, icon_name=None, language=None, exposure=0.1, gain=0):
    """
    Test OCR and icon detection via camera API.
    :param dut_name: Name of DUT where text and icon should be visible.
    :param icon_name: Name of icon to detect from DUT.
    :param language: Language used to find text on the DUT.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    camera = tntclient.camera("Camera1")

    dut = tntclient.dut(dut_name)

    dut.jump(0, 0, 10)

    # Move camera focus to a position on DUT.
    camera.move(dut.width / 2, dut.height / 2, 0, dut_name)

    if icon_name is not None:
        results = camera.detect_icon(icon_name, confidence=0.9, context=dut_name, exposure=exposure, gain=gain)

        for result in results:
            print("confidence: {}, center_x: {}, center_y: {}".format(result["confidence"], result["center_x"], result["center_y"]))

    if language is not None:
        results = camera.read_text(dut_name, language=language, exposure=exposure, gain=gain)

        for result in results:
            print("text: {}".format(result["text"]))


def test_dut_corners():
    """
    Test creating a new DUT and setting corners via API.
    The DUT is removed at the end of the test.
    """
    tntclient = TnTClient()

    # New dut is created for test so no existing duts are modified.
    dut = tntclient.add_dut('api_test_dut')

    dut.tl = {'z': -50.0, 'y': 200.0, 'x': 100.0}
    dut.tr = {'z': -50.0, 'y': 200.0, 'x': 150.0}
    dut.bl = {'y': 300.0, 'x': 100.0, 'z': -50.0}

    assert np.isclose(dut.width, 50)
    assert np.isclose(dut.height, 100)
    pos = dut.position
    assert pos["bottom_left"] == {'y': 300.0, 'x': 100.0, 'z': -50.0}
    assert pos["top_left"] == {'z': -50.0, 'y': 200.0, 'x': 100.0}
    assert pos["bottom_right"] == {'z': -50.0, 'y': 300.0, 'x': 150.0}
    assert pos["top_right"] == {'z': -50.0, 'y': 200.0, 'x': 150.0}

    assert dut.top_left == {'z': -50.0, 'y': 200.0, 'x': 100.0}
    assert dut.tl == {'z': -50.0, 'y': 200.0, 'x': 100.0}

    assert dut.top_right == {'z': -50.0, 'y': 200.0, 'x': 150.0}
    assert dut.tr == {'z': -50.0, 'y': 200.0, 'x': 150.0}

    assert dut.bottom_left == {'y': 300.0, 'x': 100.0, 'z': -50.0}
    assert dut.bl == {'y': 300.0, 'x': 100.0, 'z': -50.0}

    assert dut.bottom_right == {'z': -50.0, 'y': 300.0, 'x': 150.0}
    assert dut.br == {'z': -50.0, 'y': 300.0, 'x': 150.0}

    # Move left side 50 mm left.
    dut.tl = {'z': -50.0, 'y': 200.0, 'x': 50.0}
    dut.bl = {'y': 300.0, 'x': 50.0, 'z': -50.0}

    assert dut.top_left == {'z': -50.0, 'y': 200.0, 'x': 50.0}
    assert dut.bottom_left == {'y': 300.0, 'x': 50.0, 'z': -50.0}

    # Move Top 50 mm up.
    dut.tl = {'z': -50.0, 'y': 150.0, 'x': 50.0}
    dut.tr = {'z': -50.0, 'y': 150.0, 'x': 150.0}

    assert dut.top_left == {'z': -50.0, 'y': 150.0, 'x': 50.0}
    assert dut.top_right == {'z': -50.0, 'y': 150.0, 'x': 150.0}

    assert np.allclose(dut.orientation['i'], [1, 0, 0])
    assert np.allclose(dut.orientation['j'], [0, 1, 0])
    assert np.allclose(dut.orientation['k'], [0, 0, 1])

    assert np.isclose(dut.base_distance, 10)
    dut.remove()


def test_basic_gestures(dut_name, z=10):
    """
    Perform basic gestures on DUT.
    :param dut_name: Name of DUT.
    :param z: Height above DUT in mm.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    dut = tntclient.dut(dut_name)

    cx = dut.width / 2
    cy = dut.height / 2

    # Jump over top left corner of DUT at height z mm.
    dut.jump(x=0, y=0, z=z)

    # Make sure position matches real position.
    position = dut.get_robot_position()["effective"]
    print("x: {}, y: {}, z:{}".format(position["x"], position["y"], position["z"]))

    # Move over DUT center at height z mm.
    dut.move(x=cx, y=cy, z=z)

    # Move down to touch DUT surface. Spring / Voicecoil should not flex if DUT is planar.
    dut.move(x=cx, y=cy, z=0)

    # Move up.
    dut.move(x=cx, y=cy, z=z)

    # Tap DUT corners. Make sure by visual inspection that tip center accurately taps the corners.
    dut.tap(x=0, y=0, duration=1.0)
    dut.tap(x=dut.width, y=0, duration=1.0)
    dut.tap(x=dut.width, y=dut.height, duration=1.0)
    dut.tap(x=0, y=dut.height, duration=1.0)

    # Perform watchdog tap at the center of DUT.
    dut.watchdog_tap(x=cx, y=cy, duration=1.0)

    # Perform double tap at the center of DUT. Make sure that the duration and interval are approximately correct.
    dut.double_tap(x=cx, y=cy, duration=1.0, interval=3.0)

    # Tap DUT corners with multitap.
    dut.multi_tap([TnTDutPoint(0, 0, 0), TnTDutPoint(dut.width, 0, 0),
                   TnTDutPoint(dut.width, dut.height, 0), TnTDutPoint(0, dut.height, 0)], lift=z, clearance=0)

    # Perform path gesture around DUT.
    dut.path([TnTDutPoint(0, 0, z), TnTDutPoint(0, 0, 0), TnTDutPoint(dut.width, 0, 0),
              TnTDutPoint(dut.width, dut.height, 0), TnTDutPoint(0, dut.height, 0),
              TnTDutPoint(0, 0, 0), TnTDutPoint(0, 0, z)])

    # Swipe DUT diagonally from corner to corner.
    dut.swipe(x1=0, y1=0, x2=dut.width, y2=dut.height, radius=6)
    dut.swipe(x1=dut.width, y1=0, x2=0, y2=dut.height, radius=6)

    # Drag DUT horizontally and vertically.
    dut.drag(x1=0, y1=cy, x2=dut.width, y2=cy, z=z)
    dut.drag(x1=cx, y1=0, x2=cx, y2=dut.height, z=z)

    # Perform circle at the center of the DUT.
    r = min(dut.width, dut.height) / 3
    dut.circle(x=cx, y=cy, r=r, z=z, clearance=0)


def test_synchro_gestures(dut_name, z=10):
    """
    Perform synchro gestures on DUT. Only for synchro finger robot.
    :param dut_name: Name of DUT.
    :param z: Height above DUT in mm.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    dut = tntclient.dut(dut_name)

    # If testing synchro robot the 2nd finger should also be attached
    # Check tips
    tips = robot.get_attached_tips()

    if tips['tool1'] is None:
        raise Exception("tool1 has no tip attached")
    if 'tool2' in tips.keys():
        if tips['tool2'] is None:
            raise Exception("tool2 has no tip attached")

    cx = dut.width / 2
    cy = dut.height / 2

    d = min(dut.width, dut.height)

    # Synchro max separation is slightly over 100 mm.
    d = min(d, 100)

    dut.jump(0, 0, 10)

    # Perform horizontal pinch at the center of DUT.
    dut.pinch(x=cx, y=cy, d1=d/2, d2=d, azimuth=0, z=z)

    # Perform drumroll at the center of DUT.
    dut.drumroll(x=cx, y=cy, azimuth=0, separation=d/2, tap_count=6, tap_duration=4.0)

    # Perform compass at the center of DUT. Tool should rotate 90 degrees counter-clockwise.
    dut.compass(x=cx, y=cy, azimuth1=0, azimuth2=90, separation=d/2, z=z)

    # Perform compass tap at the center of DUT.
    dut.compass_tap(x=cx, y=cy, azimuth1=0, azimuth2=90, separation=d/2, tap_azimuth_step=30, z=z, tap_with_stationary_finger=False)
    dut.compass_tap(x=cx, y=cy, azimuth1=0, azimuth2=90, separation=d/2, tap_azimuth_step=30, z=z, tap_with_stationary_finger=True)

    # Perform touch and tap at the center of DUT.
    dut.touch_and_tap(touch_x=0, touch_y=cy, tap_x=d/2, tap_y=cy-d/2, z=z, number_of_taps=2)

    # Perform horizontal line tap tapping two times.
    dut.line_tap(x1=0, y1=cy, x2=dut.width, y2=cy, tap_distances=[dut.width/3, 2*dut.width/3], z=z)

    # Perform rotate at the center of DUT.
    dut.rotate(x=cx, y=cy, azimuth1=0, azimuth2=170, separation=d/2, z=z)

    # Perform touch and drag so that one finger touches the center of left side and the second finder performs vertical drag.
    dut.touch_and_drag(x0=0, y0=cy, x1=d/2, y1=cy-d/2, x2=d/2, y2=cy+d/2, z=z)

    # Perform horizontal fast swipe.
    dut.fast_swipe(x1=0, y1=cy, x2=dut.width, y2=cy, separation1=d/2, separation2=d, speed=250, acceleration=500, radius=6)


class ForceMeasurement:
    def __init__(self):
        """

        :param robot: Robot Node.
        :param axis_force_grams: Force to apply in grams as dictionary e.g. {"axis1": force1, "axis2": force2}.
        """
        tntclient = TnTClient()

        self._event = threading.Event()
        self._futek = tntclient.futek("futek")
        self._thread = None

    def __enter__(self):
        self._futek.tare()

        def print_force():
            while not self._event.is_set():
                 print(self._futek.forcevalue())

        self._thread = threading.Thread(target=print_force)
        self._thread.start()

    def __exit__(self, *args, **kwargs):
        self._event.set()
        self._thread.join()


def test_force_gestures(dut_name, force=300, z=10):
    """
    Perform force gestures on DUT. Force must have been calibrated.
    There must be Futek sensor in server.
    :param dut_name: Name of DUT. This should be a Futek sensor positioned to that top left is the center of the sensor.
    :param force: Force in grams.
    :param z: Height over DUT in mm.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    dut = tntclient.dut(dut_name)

    cx = dut.width / 2
    cy = dut.height / 2

    # Perform press at DUT center. Make sure the printed force values are within 1 % of the target force.
    with ForceMeasurement():
        dut.press(x=cx, y=cy, z=z, force=force)

    # Perform horizontal drag force. Make sure the printed force values are within 1 % of the target force.
    with ForceMeasurement():
        dut.drag_force(x1=0, y1=cy, x2=dut.width, y2=cy, z=z, force=force)


def test_dut_svg(dut_name):
    """
    Test DUT SVG functions. Only if DUT has SVG defined.
    :param dut_name: Name of DUT.
    """
    tntclient = TnTClient()

    dut = tntclient.dut(dut_name)

    result = dut.info()
    print(result)

    result = dut.touches()
    print(result)

    result = dut.filter_points([(10, 20), (30, 40)], "test_region", 2.0)
    print(result)

    result = dut.filter_lines([[10, 20, 30, 40], [50, 60, 70, 80]], "test_region", 2.0)
    print(result)

    result = dut.region_contour("test_region", 10)
    print(result)

    result = dut.svg_data()
    print(result)


def test_dut_physical_button(dut_name, physical_button_name):
    """
    Test pressing physical button on DUT.
    :param dut_name: Name of DUT.
    :param physical_button_name: Name of physical button.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    dut = tntclient.dut(dut_name)

    buttons = dut.list_buttons()
    print(buttons)

    assert physical_button_name in buttons

    robot.press_physical_button(physical_button_name, duration=1.0)


def test_dut_ocr_and_icon_detection(dut_name, icon_name=None, text=None, language="English", exposure=0.1, gain=0):
    """
    Test OCR and icon detection on DUT. Tries to find icon and text and tap at the center of the result.
    :param dut_name: Name of DUT.
    :param icon_name: Name of icon.
    :param text: Text to find.
    :param language: OCR language.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    dut = tntclient.dut(dut_name)

    # Take a screenshot and make sure we get its name as result.
    # Check that a PNG image was created under TnT Server/data/images by that name.
    screenshot_name = dut.screenshot("Camera1", exposure=exposure, gain=gain)
    print(screenshot_name)

    # Test accessing image.
    img = tntclient.image(screenshot_name)

    print(img.width)
    print(img.height)
    print(img.png())
    print(img.jpeg())

    if icon_name is not None:
        results = dut.find_objects(icon_name, min_score=0.8, exposure=exposure, gain=gain)

        for result in results["results"]:
            print("score: {}, centerX: {}, centerY: {}".format(result["score"], result["centerX"], result["centerY"]))

        result = results["results"][0]

        dut.tap(result["centerX"], result["centerY"], duration=1.0)

    if text is not None:
        results = dut.search_text(text, language=language, min_score=0.8, exposure=exposure, gain=gain)

        for result in results["results"]:
            print("text: {}, centerX: {}, centerY: {}".format(result["text"], result["centerX"], result["centerY"]))

        result = results["results"][0]

        dut.tap(result["centerX"], result["centerY"], duration=1.0)


def test_dut_show_image(dut_name, image_path):
    """
    Test displaying an image on DUT. Requires that there is TCP connection to the DUT OptoTouch app.
    :param dut_name: Name of DUT.
    :param image_path: Path to image file (PNG).
    """
    tntclient = TnTClient()

    dut = tntclient.dut(dut_name)

    with open(image_path, "rb") as file:
        im_data = file.read()

    dut.show_image(im_data)


def test_dut_positioning(dut_name, exposure, gain):
    """
    Test DUT positioning via API.
    Uses existing DUT as starting point but creates a new DOT that is removed at the end.
    Requires TCP connection to DUT which must have OptoTouch application in testing mode.
    The application DUT name must be "apitestdut".
    :param dut_name: Name of existing DUT to use as starting point.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    dut = tntclient.dut(dut_name)

    # Make sure the DUT application name field matches this value and that the app is in measure mode.
    new_dut_name = "apitestdut"
    new_dut = tntclient.add_dut(new_dut_name)

    camera_name = "Camera1"

    # Scaling factor for display, pixels per millimeter.
    # This can be a rough estimate obtained by measuring panel width with ruler.
    display_ppmm = 16.5

    # Number of markers to use in positioning (minimum is 4).
    N_markers = 5

    # Move to position where DUT center is at camera focus.
    dut.jump(0, 0, 10)
    camera = tntclient.camera(camera_name)
    camera.move(dut.width / 2, dut.height / 2, 0, dut_name)

    dutpositioning = TnTDUTPositioningClient("dutpositioning")

    # Perform automatic positioning.
    dutpositioning.start_xyz_positioning(dut_name=new_dut_name, camera_name=camera_name, camera_exposure=exposure,
                                         camera_gain=gain, display_ppmm=display_ppmm,
                                         position_image_params=None, n_markers=N_markers, show_positioning_image=True)

    # Tap the DUT corners
    new_dut.tap(x=0, y=0)
    new_dut.tap(x=new_dut.width, y=0)
    new_dut.tap(x=new_dut.width, y=new_dut.height)
    new_dut.tap(x=0, y=new_dut.height)

    # Remove the DUT.
    new_dut.remove()


def test_hsup():
    """
    Test HSUP via API.
    Note: this only tests the API calls but making correct measurements would need more instructions.
    """

    wd = TnTHsupWatchdogClient()

    wd.start(settings_path="camera_settings_wd.yaml")
    results = wd.get_results()
    print(results)
    result = wd.get_status()
    print(result)

    spa = TnTHsupSpaClient()

    spa.start(settings_path="camera_settings_spa.yaml")
    results = spa.get_results()
    print(results)
    result = spa.get_status()
    print(result)

    p2i = TnTHsupP2IClient()

    p2i.start(settings_path="camera_settings_p2i.yaml")
    results = p2i.get_results()
    print(results)
    result = p2i.get_status()
    print(result)


def test_microphone(microphone_device_name):
    """
    Test microphone if it has been configured.
    """
    tntclient = TnTClient()

    mic = tntclient.microphone("microphone1")

    result = mic.list_recording_devices()
    print(result)

    result = mic.record_audio(record_duration=2)
    print(result)

    result = mic.get_latest_recording()
    print(result)

    result = mic.device_default_sample_rate()
    print(result)

    mic.device_name = microphone_device_name
    print(mic.device_name)

    mic.margin = 3
    print(mic.margin)

    mic.rate = 10000
    print(mic.rate)

    mic.chunk_size = 100
    print(mic.chunk_size)

    mic.timeout_buffer = 200
    print(mic.timeout_buffer)


def test_motherboard(motherboard_parameter_name):
    """
    Test setting motherboard output state. Only if IO has been configured.
    """
    tntclient = TnTClient()
    mb = tntclient.motherboard("Motherboard1")

    mb.set_output_state(name_or_number=motherboard_parameter_name, state=1)


def test_physical_button():
    """
    Test creating a physical button via API.
    """
    tntclient = TnTClient()

    btn = tntclient.add_physical_button("api_test_button")

    btn.approach_position = xyz_to_frame(1, 2, 3).tolist()
    print(btn.approach_position)

    btn.pressed_position = xyz_to_frame(1, 2, 3).tolist()
    print(btn.pressed_position)

    btn.jump_height = 30
    print(btn.jump_height)

    btn.remove()


def print_position():
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    result = robot.get_position()
    pos = result["effective"]
    print("x: {}, y: {}, z: {}".format(pos["x"], pos["y"], pos["z"]))


def test_robot(x1, y1, x2, y2, z):
    """
    Test robot movements.
    Given volume must be safe for robot to move.
    :param x1: Lower x limit.
    :param y1: Lower y limit.
    :param x2: Higher x limit.
    :param y2: Higher y limit.
    :param z: Z value.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.go_home()
    robot.reset_robot_error()

    # Check home position
    print_position()

    robot.set_speed(20, 200)

    result = robot.get_speed()
    print(result)

    # Move to corners of given volume.
    robot.move(x1, y1, z)
    print_position()

    robot.move(x2, y1, z)
    print_position()

    robot.move(x2, y2, z)
    print_position()

    robot.move(x1, y2, z)
    print_position()

    # Move to xy center location.
    robot.move((x1 + x2) / 2, (y1 + y2) / 2, z)

    # Move relative in x direction.
    robot.move_relative(x=(x2 - x1) / 4)

    # Move relative in y direction.
    robot.move_relative(y=(y2 - y1) / 4)


def test_synchro_robot():
    """
    Test sychro robot API.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.go_home()

    robot.set_speed(20, 200)

    robot.move_relative(x=50, y=50)

    robot.set_finger_separation(40)

    result = robot.get_finger_separation()
    print(result)


def test_changing_tips(tip_name):
    """
    Test changing tip.
    :param tip_name: Name of tip. This must have proper slot positions defined via UI.
    """
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    # Detach tip if currently attached.
    robot.detach_tip(tool_name="tool1")

    # Attach tip.
    robot.attach_tip(tip_name, tool_name="tool1")

    # Detach tip.
    robot.detach_tip(tool_name="tool1")

    # Attach tip again.
    robot.attach_tip(tip_name, tool_name="tool1")


def test_speaker(speaker_name, wav_file_name, speaker_device_name):
    """
    Test speaker.
    :param speaker_name: Name of speaker.
    :param wav_file_name: Path to wav file to load.
    :param speaker_device_name: Name of speaker device.
    """
    tntclient = TnTClient()
    speaker = tntclient.speaker(speaker_name)

    result = speaker.list_playback_devices()
    print(result)

    speaker.play_wav_file(wav_file_name)

    speaker.device_name = speaker_device_name
    print(speaker.device_name)

    speaker.chunk_size = 100
    print(speaker.chunk_size)


def test_surface_probe(dut_name, z=40.0):
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    robot.set_speed(20, 200)

    # Jump over to DUT where we can probe the surface.
    dut = tntclient.dut(dut_name)
    dut.jump(dut.width/2, dut.height/2, z)

    sp = TnTSurfaceProbeClient("surfaceprobe")

    # Probe surface.
    result = sp.probe_z_surface()
    probed_z = result[2][3]

    dut_z = (dut.bl["z"] + dut.tr["z"]) / 2

    # DUT z and probed z should be the same within at least 1 mm accuracy.
    print("DUT z: {}, probed z: {}".format(probed_z, dut_z))


def test_tip():
    """
    Test creating new tip via API.
    """
    tntclient = TnTClient()

    tip = tntclient.add_tip("api_test_tip")

    tip.slot_in = xyz_to_frame(10, 20, -30).tolist()
    print(tip.slot_in)

    tip.slot_out = xyz_to_frame(10, 20, -30).tolist()
    print(tip.slot_out)

    tip.diameter = 10
    print(tip.diameter)

    tip.length = 15
    print(tip.length)

    print(tip.is_multifinger)

    tip.num_tips = 4
    print(tip.num_tips)

    tip.tip_distance = 20
    print(tip.tip_distance)

    tip.separation = 40
    print(tip.separation)

    tip.first_finger_offset = 5
    print(tip.first_finger_offset)

    tip.remove()


def test_tnt_client():
    """
    Test various factory methods.
    """
    tntclient = TnTClient()

    # Just test that tntclient factory methods work without errors.
    print(tntclient.robots())
    print(tntclient.duts())
    print(tntclient.tips())
    print(tntclient.cameras())
    print(tntclient.physical_buttons())
    print(tntclient.detectors())
    print(tntclient.speakers())
    print(tntclient.images())
    print(tntclient.motherboards())
    print(tntclient.version())


if __name__ == "__main__":
    # Name of DUT that must have been positioned via UI before the tests.
    dut_name = "dut1"

    # Futek sensor positioned as DUT. Top left should be center of the censor and DUT size should be 1 mm x 1 mm.
    force_dut_name = "force"

    # Name of tip which must have correctly positioned slot.
    tip_name = "tip1"

    # Height above DUT in mm where robot can move.
    z = 10

    # Name of physical button that must have been created for the DUT.
    physical_button_name = "button1"

    # Parameters for HSUF testing.
    icon_name = "icon_chrome"
    text = "Chrome"
    language = "English"
    exposure = 0.05
    gain = 0
    
    # Step into each function and execute statements one by one in Pycharm.

    # Basic tests. These should be ran for each delivery.
    test_tnt_client()
    test_robot(x1=10, y1=10, x2=100, y2=100, z=-20)  # z should be reachable with current tip.
    test_camera()
    test_basic_gestures(dut_name=dut_name, z=z)
    test_changing_tips(tip_name=tip_name)
    test_surface_probe(dut_name=dut_name, z=40)  # Use z value where probing can be done.
    test_dut_positioning(dut_name=dut_name, exposure=exposure, gain=gain)
    test_dut_physical_button(dut_name=dut_name, physical_button_name=physical_button_name)

    test_dut_corners()
    test_tip()
    test_physical_button()

    # Tests if robot has force.
    test_force_gestures(dut_name=force_dut_name, force=300, z=z)

    # Tests for synchro finger robot.
    test_synchro_robot()
    test_synchro_gestures(dut_name=dut_name, z=z)

    # Tests if system has OCR and icon detection.
    test_dut_ocr_and_icon_detection(dut_name, icon_name=icon_name, text=text, language=language, exposure=exposure, gain=gain)
    test_camera_ocr_and_icon_detection(dut_name=dut_name, icon_name=icon_name, language=language, exposure=exposure, gain=gain)

    # Other tests that are run depending on the system.
    #test_speaker(speaker_name="", wav_file_name="", speaker_device_name="")
    #test_motherboard(motherboard_parameter_name="motherboard1")
    #test_microphone(microphone_device_name="microphone")
    #test_hsup(hsup_path="")
    #test_dut_show_image(dut_name=dut_name, image_path="")
    #test_dut_svg(dut_name=dut_name)
    #test_audio_analyzer()
