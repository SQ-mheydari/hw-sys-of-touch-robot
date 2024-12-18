
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTHsupWatchdogClient(TnTClientObject):
    """
    Class for performing Human Simulated User Performance (HSUP) analysis.
    """
    def __init__(self, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "analyzers", "watchdog")
        
    def get_results(self, timeout=None):    
        """
        Return results of the analysis.
        :param timeout: With timeout None, the function will block until results are available. If timeout is a positive
        number, the function waits for the specified number of seconds for the results to be ready. If results are not
        available after the specified timeout value, an error is returned.
        :param kwargs: Possible other unused keyword arguments.
        :return: Analysis results. If no analysis results exist, failure status is returned.
        """
        params = {
        }
        
        if timeout is not None:
            params['timeout'] = timeout
        
        return self._GET('results', params)
        
    def start(self, settings_path=None, params={}):    
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
        params = {
            'params': params,
        }
        
        if settings_path is not None:
            params['settings_path'] = settings_path
        
        return self._PUT('start_measurement', params)
        
    def get_status(self, ):    
        """
        Query status of the HSUP analysis. Includes information about storage and analysis process state.
        :return: Dictionary with process statuses, number of images captured and number of images waiting for analysis.
        """
        params = {
        }
        
        
        return self._GET('status', params)
        
class TnTHsupSpaClient(TnTClientObject):
    """
    Class for performing Human Simulated User Performance (HSUP) analysis.
    """
    def __init__(self, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "analyzers", "spa")
        
    def get_results(self, timeout=None):    
        """
        Return results of the analysis.
        :param timeout: With timeout None, the function will block until results are available. If timeout is a positive
        number, the function waits for the specified number of seconds for the results to be ready. If results are not
        available after the specified timeout value, an error is returned.
        :param kwargs: Possible other unused keyword arguments.
        :return: Analysis results. If no analysis results exist, failure status is returned.
        """
        params = {
        }
        
        if timeout is not None:
            params['timeout'] = timeout
        
        return self._GET('results', params)
        
    def start(self, settings_path=None, params={}):    
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
        params = {
            'params': params,
        }
        
        if settings_path is not None:
            params['settings_path'] = settings_path
        
        return self._PUT('start_measurement', params)
        
    def get_status(self, ):    
        """
        Query status of the HSUP analysis. Includes information about storage and analysis process state.
        :return: Dictionary with process statuses, number of images captured and number of images waiting for analysis.
        """
        params = {
        }
        
        
        return self._GET('status', params)
        
class TnTHsupP2IClient(TnTClientObject):
    """
    Class for performing Human Simulated User Performance (HSUP) analysis.
    """
    def __init__(self, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "analyzers", "p2i")
        
    def get_results(self, timeout=None):    
        """
        Return results of the analysis.
        :param timeout: With timeout None, the function will block until results are available. If timeout is a positive
        number, the function waits for the specified number of seconds for the results to be ready. If results are not
        available after the specified timeout value, an error is returned.
        :param kwargs: Possible other unused keyword arguments.
        :return: Analysis results. If no analysis results exist, failure status is returned.
        """
        params = {
        }
        
        if timeout is not None:
            params['timeout'] = timeout
        
        return self._GET('results', params)
        
    def start(self, settings_path=None, params={}):    
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
        params = {
            'params': params,
        }
        
        if settings_path is not None:
            params['settings_path'] = settings_path
        
        return self._PUT('start_measurement', params)
        
    def get_status(self, ):    
        """
        Query status of the HSUP analysis. Includes information about storage and analysis process state.
        :return: Dictionary with process statuses, number of images captured and number of images waiting for analysis.
        """
        params = {
        }
        
        
        return self._GET('status', params)
        
