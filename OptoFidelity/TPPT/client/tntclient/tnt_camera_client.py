
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTCameraClient(TnTClientObject):
    """
    TnT Compatible Camera resource
    Should work together with
    - TnT Sequencer
    - TnT Positioning Tool
    - TnT UI

    Camera coordinate convention:
    Camera node's parent frame determines the camera mount frame. Convention is that
    camera mount frame local z-axis points in the direction of the camera view (towards imaging target).
    When looking along camera view, the local x-axis of camera mount frame points to the left meaning that
    the pixel x-coordinates increase along negative local x-axis direction. The local y-axis direction points down
    in the image meaning that pixel y-coordinates increase along positive local y-axis direction.
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "cameras", name)
        
    def detect_icon(self, icon, confidence=0.75, context=None, detector='halcon', exposure=None, gain=None):    
        """
        DEPRECATED!
        List of detected objects with their positions in relation to given context.
        :param icon: Name of the icon. You can teach new icons with TnT UI.
        :param confidence: Confidence factor 0..1 where 1 is very confident. Normal confidence is about 0.7.
        :param context: Returned positions are relative to this context.
        :param detector: Detector name as string, like "halcon".
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :return: List of detected objects.
        """
        params = {
            'icon': icon,
            'confidence': confidence,
            'detector': detector,
        }
        
        if context is not None:
            params['context'] = context
        if exposure is not None:
            params['exposure'] = exposure
        if gain is not None:
            params['gain'] = gain
        
        return self._GET('detect_icon', params)
        
    def focus_height(self, ):    
        """
        Get camera focus height (distance)
        :return: Focus height in mm.
        """
        params = {
        }
        
        
        return self._GET('focus_height', params)
        
    def get_parameter(self, name):    
        """
        Get parameter value.
        :param name: Name of the parameter to be read.
        :return: {'status': 'ok', 'params': parameter_dictionary}.
        """
        params = {
            'name': name,
        }
        
        
        return self._GET('parameter', params)
        
    def get_parameters(self, parameters=None):    
        """
        Get given set of parameters from camera. Input dict indicates which parameters are retrieved.
        :param parameters: Additional arguments to indicate which parameters should be retrieved from camera.
            Values are ignored. List cannot be passed into HTTP GET that only has arguments and no body.
        :return: Dictionary of requested parameters and their values.
        """
        params = {
        }
        
        if parameters is not None:
            params['parameters'] = parameters
        
        return self._GET('parameters', params)
        
    def read_text(self, context='tnt', language='English', detector='abbyy', exposure=None, gain=None):    
        """
        DEPRECATED!
        Take a photo and analyze the image for text.
        :param context: Returned positions are relative to this context.
        :param language: Language as string, like "English" (default).
        :param detector: Analyzer name, like abbyy (default).
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :return: Found text with position information.
        """
        params = {
            'context': context,
            'language': language,
            'detector': detector,
        }
        
        if exposure is not None:
            params['exposure'] = exposure
        if gain is not None:
            params['gain'] = gain
        
        return self._GET('read_text', params)
        
    def take_still(self, filetype='jpg', width=None, height=None, zoom=None, undistorted=False, exposure=None, gain=None, scaling=None, interpolation='cubic', flipx=None, flipy=None, rotate90=None, duration=None):    
        """
        Takes a photo. This function opens camera automatically, no need to use open() -function. In case the still is
        taken in the middle of stream view, a sleep-command might be needed before taking still to ensure that all
        the images from continuous capture are processed before clearing the queue.
        :param filetype: jpg, png, raw(np.array).
        :param width: optional target image width. both width and height needed
        :param height: optional target image height. both width and height needed
        :param zoom: optional image zoom.
        :param undistorted: true/false, only available after undistort called succesfully
        :param exposure: exposure in seconds. If not set, uses last exposure used.
        :param gain: gain value. If not set, uses last gain value used.
        :param scaling: Camera image scaling factor in range [0, 1].
        :param interpolation: Interpolation method ('nearest', 'linear', 'cubic').
        :param flipx: mirror x-coordinates of the image
        :param flipy: mirror y-coordinages of the image
        :param rotate90: rotate the image 90 degrees
        :param duration: Video capture duration in seconds. Per-pixel maximum will be taken over the video.
        :return: image in 'filetype' format

        In case filetype is "bytes", the returned image is bytearray that can be transformed into numpy array as:

        data = camera_client.take_still(filetype="bytes")
        w = int.from_bytes(data[0:4], byteorder="big")
        h = int.from_bytes(data[4:8], byteorder="big")
        d = int.from_bytes(data[8:12], byteorder="big")
        data = np.frombuffer(data[12:], dtype=np.uint8).reshape((h, w, d))
        """
        params = {
            'filetype': filetype,
            'undistorted': undistorted,
            'interpolation': interpolation,
        }
        
        if width is not None:
            params['width'] = width
        if height is not None:
            params['height'] = height
        if zoom is not None:
            params['zoom'] = zoom
        if exposure is not None:
            params['exposure'] = exposure
        if gain is not None:
            params['gain'] = gain
        if scaling is not None:
            params['scaling'] = scaling
        if flipx is not None:
            params['flipx'] = flipx
        if flipy is not None:
            params['flipy'] = flipy
        if rotate90 is not None:
            params['rotate90'] = rotate90
        if duration is not None:
            params['duration'] = duration
        
        return self._GET('still', params)
        
    def close(self, ):    
        """
        Shuts down the camera.
        """
        params = {
        }
        
        
        return self._PUT('close', params)
        
    def move(self, x, y, z, context='tnt'):    
        """
        Move camera focus point to given position (x, y, and z-coordinate) in a given context.
        :param x: Target x coordinate in a given context.
        :param y: Target y coordinate in a given context.
        :param z: Target z coordinate in a given context.
        :param context: Name of the target context.
        """
        params = {
            'x': x,
            'y': y,
            'z': z,
            'context': context,
        }
        
        
        return self._PUT('move', params)
        
    def open(self, ):    
        """
        Open camera for use.
        After the camera has been opened, sequential images can be taken quickly.
        """
        params = {
        }
        
        
        return self._PUT('open', params)
        
    def set_parameter(self, name, value):    
        """
        Set parameter value.
        :param name: Name of the parameter to set.
        :param value: Value to set to the parameter.
        :return: {'status': 'ok'}
        """
        params = {
            'name': name,
            'value': value,
        }
        
        
        return self._PUT('parameter', params)
        
    def set_parameters(self, parameters):    
        """
        Set camera parameters.
        See get_parameters.
        :param parameters: Parameter dictionary.
        :return: {'status': 'ok'}
        """
        params = {
            'parameters': parameters,
        }
        
        
        return self._PUT('parameters', params)
        
    def start_continuous(self, width=None, height=None, zoom=None, undistorted=False, exposure=None, gain=None, scaling=None, interpolation='nearest', trigger_type='SW', target_context=None, target_context_margin=0):    
        """
        Start continuous camera image capture.
        Note that Camera node argument max_queue_size should be small such as 1 to avoid latency.

        The mjpeg stream can be retrieved via GET request at URL
        http://127.0.0.1:8000/tnt/workspaces/ws/cameras/Camera1/mjpeg_stream
        where Camera1 is the name of the camera node.
        This can be used in HTML image element to view the stream.
        Be aware that browser can cache the image so if may be necessary to add e.g. current time as
        parameter to the URL by importing time library and adding '?'+str(time.time()) to the URL

        :param width: Width of image or None to use full image width.
        :param height: Height of image or None to use full image width.
        :param zoom: Zoom factor or None for no zoom.
        :param undistorted: Use distortion calibration to undistort?
        :param exposure: Camera exposure or None to use Camera node exposure state.
        :param gain: Camera gain or None to use Camera node exposure state.
        :param scaling: Scaling factor or None for no scaling.
        :param interpolation: Interpolation method ("nearest", "linear" or "cubic"). May affect image stream performance.
        :param trigger_type: Camera triggering based on internal timer "SW" or external trigger "HW".
        :param target_context: Possible DUT target for image context transformation, "None" means no transformation. (Default: None)
        :param target_context_margin: Margin for context transformation. (Default: 0)
        """
        params = {
            'undistorted': undistorted,
            'interpolation': interpolation,
            'trigger_type': trigger_type,
            'target_context_margin': target_context_margin,
        }
        
        if width is not None:
            params['width'] = width
        if height is not None:
            params['height'] = height
        if zoom is not None:
            params['zoom'] = zoom
        if exposure is not None:
            params['exposure'] = exposure
        if gain is not None:
            params['gain'] = gain
        if scaling is not None:
            params['scaling'] = scaling
        if target_context is not None:
            params['target_context'] = target_context
        
        return self._PUT('start_continuous', params)
        
    def stop_continuous(self, ):    
        """
        Stop continuous capture that was started by start_continuous().
        """
        params = {
        }
        
        
        return self._PUT('stop_continuous', params)
        
