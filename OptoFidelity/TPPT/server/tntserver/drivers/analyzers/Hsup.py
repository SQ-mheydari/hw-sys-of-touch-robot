import os
import importlib
import threading
import queue
import time
import numpy as np
from tempfile import gettempdir

import ruamel.yaml as yaml

from hsup.analysis import HSUPImage, Result, DEFAULT_ANALYZED_IMAGES_PATH
from tntserver.drivers.analyzers import storagepool
from tntserver.Nodes.Node import Node
from tntserver.license import check_license_feature, LicenseError

# These are needed so that PyInstaller hidden import collector includes them into the build.
import hsup.watchdog
import hsup.spa
import hsup.p2i

import logging
log = logging.getLogger(__name__)

DEFAULT_ANALYSIS_INPUT_IMAGES_PATH = os.path.join(gettempdir(), "OptoFidelity", "hsup", "analysis_input_images")


class MeasurementError(Exception):
    """
    Exception class for measurement related errors
    """



class Hsup():
    """
    Class for performing Human Simulated User Performance (HSUP) analysis.
    """

    # Constants for camera trigger mode.
    HSUP_CAMERA_TRIGGER_MODE_AUTOMATIC = 'Automatic'
    HSUP_CAMERA_TRIGGER_MODE_MANUAL = 'Manual'

    def __init__(self, camera=None, triggersensor=None, videosensor=None, analysis=None, **kwargs):
        """
        Constructor.
        :param camera: Name of the camera node.
        :param videosensor: Name of the videosensor node.
        :param analysis: Analysis type.
        :param kwargs: Keyword arguments including 'analysis' for analysis type (watchdog, spa, p2i).
        """

        # Check license feature
        if not check_license_feature(analysis):
            raise LicenseError("{} feature is not enabled in license.".format(analysis))

        """ Camera name. """
        self._camera_name = camera
        """
        Camera is actually camera driver and we are using the driver directly to get access to
        yasler specific details. Ths truly is not a clean way of doing it but we should do major
        refactoring of whole camera libraries.
        """
        self._camera = Node.find(camera)._driver
        """ Sensor used for triggering one-time camera image capture. """
        self._triggersensor = Node.find(triggersensor)
        """ Video multimeter sensor used for triggering camera image capture based on display backlight. """
        self._videosensor = Node.find(videosensor)

        """ Directory for storing images taken with camera. """
        self._storage_directory = DEFAULT_ANALYSIS_INPUT_IMAGES_PATH
        """ Directory for storing images modified by analysis. """
        self._analysed_images_directory = DEFAULT_ANALYZED_IMAGES_PATH

        # Multiprocessing pool for analyzing images captured with camera.
        self._analysis_pool = None
        # Multiprocessing pool for storing images captured with camera.
        self._storagepool = None
        # Result object. Type is hsup.analysis.Result.
        self._results = None
        # Analysis type.
        self._analysis = analysis
        # Counter for the number of images taken so far.
        self._image_counter = 0
        # Parameters given for the measurement and stored to be returned together with the results.
        self._params = None
        # True if backlight sync is used.
        self._backlight_sync = False
        # Triggering mode for mesurement, 'Automatic' or 'Manual'.
        self._camera_trigger_mode = None
        # Timer for the measurement to trigger stopping it.
        self._measurement_timer = None
        # Event to signal stopping measurement before timeout and start computing results
        self.get_results_event = threading.Event()

    def start_measurement(self, settings_path=None, params={}):
        """
        Starts measurement sequence: analysis and storage processes are started up, camera settings are set and
        validated and camera capture is started.

        :param settings_path: Path to measurement and analysis settings file (alternative to individual parameters)
        :param params: Measurement parameters. This is a dictionary of camera and analysis parameters.

            Common analysis parameters are:
                timeout: Timeout in seconds for camera capture.
                n_oversampling: Amount of images to capture per trigger signal and to add up together in the analysis.
                camera_trigger_mode: Camera capture start is either 'Manual' or 'Automatic' from finger touch.
                display_backlight_sync: True if camera needs to sync frame capture to rolling backlight
        :return: Status reply
        """
        log.info("start_measurement settings_path={}, params={}".format(settings_path, params))

        camera_params = None
        analysis_params = None

        # Wait for possible previous measurement to finish
        while (self._analysis_pool is not None and self._analysis_pool.is_running()) or \
                (self._storagepool is not None and self._storagepool.is_running()):
            log.info("start_measurement waiting for previously started measurement to finish")
            time.sleep(1)

        if self._measurement_timer is not None:
            # If we are here, processing pools are no longer running. Thread join should be therefore quick.
            self._measurement_timer.join(timeout=2)
            if self._measurement_timer.is_alive():
                raise Exception("Error shutting down active measurement.")

        # Reset results and image counter.
        self._results = None
        self._image_counter = 0

        # If measurement parameters are given, use them. Otherwise take them from settings path.
        if not params and settings_path:
            params = self._load_settings(settings_path)
            log.info("start_measurement settings={}".format(params))

        if not params:
            raise Exception("No measurement parameters given. Aborting measurement.")
        else:
            self._params = params
            if "camera" in params:
                camera_params = params["camera"]
                if "frame_rate" in camera_params:
                    if camera_params["frame_rate"] == 0:
                        camera_params["frame_rate_enable"] = False
                        del camera_params["frame_rate"]
                    else:
                        camera_params["frame_rate_enable"] = True
            else:
                log.info("No camera parameters given. Using what is currently stored into the camera.")

            if "analysis" in params:
                analysis_params = params["analysis"]
            else:
                log.info("No analysis parameters given. Using default values.")

        timeout = analysis_params.get('timeout', 20.0)
        n_oversampling = analysis_params.get('n_oversampling', 1)
        self._camera_trigger_mode = analysis_params.get('camera_trigger_mode', self.HSUP_CAMERA_TRIGGER_MODE_MANUAL)
        self._backlight_sync = analysis_params.get('display_backlight_sync', False)

        # Timer must be higher than 0.0 so we are sure the operation stops.
        if timeout <= 0.0:
            raise Exception("Timeout must be higher than zero.")

        self._camera_configure(camera_params)

        # Set Pylon level image buffer to a high value to avoid missing frames in continuous capture.
        self._camera.set_parameters({'buffer_count': 1000})

        try:
            camera_trigger_type = self._determine_trigger_settings(n_oversampling=n_oversampling,
                                                                   mode=self._camera_trigger_mode)
        except MeasurementError as e:
            log.exception(e)
            raise Exception("Failed to set camera triggering for measurement. Aborting measurement. " + str(e))

        # Initialize multiprocessing pools. One process that stores data to diskcache,
        # and another process for analysis.
        self._storagepool = storagepool.StoragePool(diskcache_directory=self._storage_directory)
        self._storagepool.start()
        self._analysis_pool = storagepool.AnalysisPool(
            analysed_images_directory=self._analysed_images_directory,
            analysis=self._analysis,
            analysis_kwargs=analysis_params
        )
        self._analysis_pool.start()

        # Wait for process pools to start up
        log.info("Waiting for processing pools to initialize.")
        start_time = time.time()
        while not self._storagepool.is_started() and not self._analysis_pool.is_started():
            # Starting up process pools containing 3 processes takes normally a few (< 5) seconds. If we ever hit this
            # timeout, something is wrong and the system has become stuck. Value is selected to be well above the usual
            # required startup time.
            if time.time() - start_time > 20:
                self._stop_measurement()
                raise Exception("Failed to start measurement processing pools. Timeout exceeded.")
            time.sleep(0.01)
        log.info("Processing pools initialized and running.")

        self._camera.open()

        try:
            log.debug("Starting camera continuous capture with trigger_type {}.".format(camera_trigger_type))
            self._camera.start_continuous(callback=self._img_to_analysis, trigger_type=camera_trigger_type)
        except Exception as e:
            log.error("Unable to start camera capture: " + str(e))
            self._stop_measurement()
            raise Exception("Unable to start camera capture: " + str(e))
        else:
            self._measurement_timer = threading.Thread(target=self._thread_runner, args=(timeout, ))
            self.get_results_event.clear()
            self._measurement_timer.start()

    def _thread_runner(self, timeout):
        """
        Timer function which stops on-going measurement either after timeout has elapsed or when results are requested
        while measurement is still running.
        :param timeout: Timeout value for measurement, i.e. maximum measurement time.
        """
        t = time.time()

        # Wait in loop until timeout elapses or event is set.
        while time.time() - t < timeout:
            time.sleep(0.1)

            # results() will set this event to indicate measurement should stop.
            if self.get_results_event.is_set():
                break

        self._stop_measurement()

    def _stop_measurement(self):
        """
        Stop camera capture and wait for analysis to finish processing and storing images. Function will block until
        analysis is finished when it is used to stop an active measurement.
        """
        log.info("Called stop_measurement.")

        if self._measurement_timer is None and self._analysis_pool is None and self._storagepool is None:
            log.warning("stop_measurement called with no active measurement")
            return

        self._camera.stop_continuous()

        # Clear the internal queue of the camera driver after stopping capture.
        while True:
            try:
                self._camera.get_image_from_buffer(timeout=1)
            except queue.Empty:
                log.debug("Camera internal queue cleared.")
                break

        # Give signal to return results by putting None to the queue
        self._analysis_pool.analyse_image(None)
        self._storagepool.store_image(None)
        # Close analysis
        while not self._analysis_pool.empty:
            log.info("Waiting for analysis to finish, approximately {} images remaining.".format(
                self._analysis_pool.images_remaining))
            time.sleep(1)

        self._results = self._analysis_pool.read_results(timeout=None)
        self._results.analyzed_images_path = self._analysed_images_directory
        self._results.input_images_path = self._storage_directory
        self._results.parameters = self._params

        self._analysis_pool.close()

    def start_analysis(self, data, params):
        """
        Start offline analysis of already captured images.
        :param data: Path for the input images as diskcache.Cache.
        :param params: Additional input arguments for the analysis.
        :return: Analysis result object as dictionary.
        """
        log.info("start_analysis data={}, params={}".format(data, params))

        self._results = None

        # dynamically load analysis class and create instance with given keyword arguments
        driver_module = importlib.import_module('hsup.' + self._analysis.lower())
        driver_class = getattr(driver_module, self._analysis)
        analysis = driver_class(**params)

        self._results = analysis.process(data, **params)

        return self._result_to_dict(self._results)

    def results(self, timeout=None, **kwargs):
        """
        Return results of the analysis.
        :param timeout: With timeout None, the function will block until results are available. If timeout is a positive
        number, the function waits for the specified number of seconds for the results to be ready. If results are not
        available after the specified timeout value, an error is returned.
        :param kwargs: Possible other unused keyword arguments.
        :return: Analysis results. If no analysis results exist, failure status is returned.
        """

        # Return error if no measurement has been run.
        if self._analysis_pool is None:
            return {"status": "nok"}

        # Signal to stop measurement and proceed to waiting for results to be available.
        self.get_results_event.set()

        # Check for elapsing timeout while measurement is stopped and analysis is being run.
        start_time = time.time()
        while self._analysis_pool.is_running() or self._storagepool.is_running():
            if timeout is not None and time.time() - start_time > timeout:
                log.error("Retrieving results timed out.")
                self._analysis_pool.abort()
                self._analysis_pool.close()
                break
            time.sleep(0.1)

        if self._results is not None:
            return self._result_to_dict(self._results)
        else:
            return {"status": "nok"}

    def status(self):
        """
        Query status of the HSUP analysis. Includes information about storage and analysis process state.
        :return: Dictionary with process statuses, number of images captured and number of images waiting for analysis.
        """
        analysis_running = False
        results_storage_running = False
        input_storage_running = False
        analysis_images_remaining = 0
        input_storage_images_remaining = 0
        result_storage_images_remaining = 0

        # check state of analysis process, is it running and how many images left to analyze (if any)
        if self._analysis_pool is not None:
            analysis_running = self._analysis_pool.analysis_is_running()
            results_storage_running = self._analysis_pool.result_storage_is_running()
            analysis_images_remaining = self._analysis_pool.images_remaining
            input_storage_images_remaining = self._analysis_pool.storage_images_remaining

        # check state of results storage process, is it running and how many images left to analyze (if any)
        if self._storagepool is not None:
            input_storage_running = self._storagepool.storage_is_running()
            result_storage_images_remaining = self._storagepool.images_remaining

        analysis_state = 'running' if analysis_running else 'stopped'
        results_storage_state = 'running' if results_storage_running else 'stopped'
        input_storage_state = 'running' if input_storage_running else 'stopped'

        # check for failure during analysis
        if not analysis_running and analysis_images_remaining > 0:
            analysis_state = 'failure'

        return {'status_analysis': analysis_state,
                'status_results_storage': results_storage_state,
                'status_input_storage': input_storage_state,
                'images_total': self._image_counter,
                'analysis_images_remaining': analysis_images_remaining,
                'input_storage_images_remaining': input_storage_images_remaining,
                'result_storage_images_remaining': result_storage_images_remaining}

    @staticmethod
    def _result_to_dict(result: Result):
        """
        Function to convert Result object into dictionary for transfer over the REST API.
        :param result: Result object to be converted.
        :return: Result object as dictionary.
        """
        result_dict = {"status": result.status,
                       "status_message": result.status_message,
                       "results": result.data,
                       "parameters": result.parameters,
                       "analyzed_images_path": result.analyzed_images_path,
                       "input_images_path": result.input_images_path}

        return result_dict

    def _img_to_analysis(self, img, error):
        """
        Callback function for every captured image. The input image object is passed to both the analysis worker process
        and the image storage worker process.
        :param img: Image object with image array, timestamp, exposure, offset and counter_value
        :param error: Possible error, if image capture failed. Otherwise error is None.
        :return: None
        """
        if error is None:
            self._image_counter += 1
            im = np.array(img, dtype=np.uint8, copy=False)
            data = HSUPImage(image=im, timestamp=img.timestamp / self._camera.tickfrequency,
                             exposure=img.exposure,
                             offset_x=img.offset[0], offset_y=img.offset[1], countervalue=img.counter_value)
            self._storagepool.store_image(data)
            self._analysis_pool.analyse_image(data)
        else:
            log.error("Image callback error: " + str(error))

        # special case for the combination of a) Watchdog analysis and b) backlight sync disabled
        if self._camera_trigger_mode == self.HSUP_CAMERA_TRIGGER_MODE_AUTOMATIC and not self._backlight_sync:
            # after capturing a few frames from the beginning of HW start trigger, switch over to internal SW timer
            # this is needed because our Basler cameras cannot start a continuous (never ending) capture without a max
            # number of frames
            if self._image_counter == 10:
                self._camera.stop_grabbing()
                self._camera.start_continuous(callback=self._img_to_analysis, trigger_type='SW')

    def _camera_configure(self, camera_params):
        """
        Set various camera parameters and configurations needed for the measurement.
        Also opens camera to ensure we can set parameters to it.
        :param camera_params: Camera parameters that are directly set to camera driver.
        """
        log.debug("Configuring camera: {}".format(camera_params))
        self._camera.open()

        # Always use fast sensor readout mode (if available).
        self._camera.set_fast_readout_mode()

        # Set camera parameters.
        if camera_params:
            self._camera.set_parameters(camera_params)

        # Enable image metadata (chunk data).
        self._camera.activate_chunkdata()
        self._camera.set_countervalue_chunkdata(enabled=True)
        self._camera.set_exposure_chunkdata(enabled=True)
        log.debug("Camera configured.")

    def _determine_trigger_settings(self, n_oversampling, mode):
        """
        Determine correct settings for camera trigger based on display type, analysis type and other parameters.
        :param n_oversampling: Amount of images to capture per trigger signal.
        :param mode: Measurement mode is either 'Manual' or 'Automatic'. Manual means without trigger from touch.
        :return: Trigger type as string.
        """
        trigger_type = 'SW'

        # Regular display (LCD)
        if not self._backlight_sync:

            # In automatic mode measurement camera capture is started from finger touch.
            if mode == self.HSUP_CAMERA_TRIGGER_MODE_AUTOMATIC:

                if self._triggersensor is None or self._triggersensor._driver is None:
                    raise MeasurementError("Unable to set automatic trigger. Triggersensor not found.")

                # Single trigger from finger movement is a sub-mode of backlight+encoder trigger mode
                # (backlight sync is however not used).
                self._triggersensor.init_auto_trigger()

                if self._analysis == 'Watchdog':
                    # in Watchdog analysis capture is started at finger release from DUT surface, which generates one HW
                    # trigger pulse
                    self._triggersensor.set_trigger_touch_end()
                else:
                    # other analyses use start from finger touch moment
                    self._triggersensor.set_trigger_touch_start()

                trigger_type = 'HWBurst'
                # set a rather large value to start initial capture with. Capture mode will be switched over to
                # internal SW timer on the fly later on
                self._camera.set_burst_frame_count(200)

            elif mode == self.HSUP_CAMERA_TRIGGER_MODE_MANUAL:
                trigger_type = 'SW'

        # OLED display with rolling backlight
        elif self._backlight_sync:

            if self._videosensor is None or self._videosensor._driver is None:
                raise MeasurementError("Unable to synchronize to display backlight. Videosensor not found.")

            # operating mode must be BL+ENC to be able to read the backlight period
            self._videosensor.set_trigger_mode_backlight_encoder()
            if self._videosensor.backlight_period_ms() == 0:
                raise MeasurementError("Failed to detect display backlight period for camera sync.")

            if not self._validate_camera_settings(n_oversampling):
                raise MeasurementError("Camera frame rate of {:.1f} is too low at current settings to capture "
                                       "{} frames in sync with the backlight.".
                                       format(self._camera.resulting_frame_rate, n_oversampling))

            # In automatic mode measurement camera capture is started from finger touch.
            if mode == self.HSUP_CAMERA_TRIGGER_MODE_AUTOMATIC:

                # TODO: Check if init_auto_trigger() could be used or whether set_trigger_mode_backlight_encoder()
                #       and reset_encoder_value() cannot be called in consecutive lines.
                self._videosensor.set_trigger_mode_backlight_encoder()

                # reboot trigger app to stop trigger signal generation
                self._videosensor.open_camera_trigger_app()
                self._videosensor.exit_application()
                self._videosensor.open_camera_trigger_app()

                self._videosensor.reset_encoder_value()

                if self._analysis == 'Watchdog':
                    # In Watchdog analysis capture is started at finger release from DUT surface.
                    self._videosensor.set_trigger_backlight_falling()

                else:
                    # Other analyses use start from finger touch moment.
                    self._videosensor.set_trigger_backlight_rising()

            # In manual mode frame capture is started immediately.
            elif mode == self.HSUP_CAMERA_TRIGGER_MODE_MANUAL:
                self._videosensor.set_trigger_mode_backlight()

            # Set number of frames to capture per trigger signal (external HW trigger from backlight).
            self._camera.set_burst_frame_count(n_oversampling)
            trigger_type = 'HWBurst'

        return trigger_type

    def _validate_camera_settings(self, n_oversampling):
        """
        Test if camera is able to capture frames fast enough, w.r.t. the backlight period and number of
        frames per trigger.
        :param n_oversampling: number of frames to capture per trigger signal
        :return: True if settings are ok
        """
        camera_fps = self._camera.resulting_frame_rate  # camera frames per second at current settings
        bl_period = self._videosensor.backlight_period_ms() / 1000

        if bl_period > 0:
            bl_freq = 1.0 / bl_period
            frames_per_period = n_oversampling
            # check if we have time to capture all the required frames within the backlight period
            return bl_freq * frames_per_period <= camera_fps
        else:
            log.error("Failed to detect display backlight period for camera sync.")
            return False

    @staticmethod
    def _load_settings(settings_path):
        """
        Load given analysis settings from YAML configuration file.
        :param settings_path: Configuration file path where to load the settings.
        :return: Loaded settings as dict.
        """
        _yaml = yaml.YAML()
        with open(settings_path, 'r') as file:
            settings = _yaml.load(file)
            log.debug("Settings loaded: {}".format(settings))
            return settings
