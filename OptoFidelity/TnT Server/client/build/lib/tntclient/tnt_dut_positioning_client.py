
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTDUTPositioningClient(TnTClientObject):
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, None, name)
        
    def dut_positioning_image(self, width, height, ppmm):    
        """
        Returns DUT positioning image according to input parameters.
        :param width: Image width in pixels.
        :param height: Image height in pixels.
        :param ppmm: Image scaling in pixels per millimeter. Image markers have a fixed diameter of 8 mm, which is
        scaled to number of pixels using this parameter.
        :return: Positioning image in PNG-format.
        """
        params = {
            'width': width,
            'height': height,
            'ppmm': ppmm,
        }
        
        
        return self._GET('dut_positioning_image', params)
        
    def positioning_image_parameters(self, width, height, ppmm):    
        """
        Returns dictionary of positioning image parameters according to image input parameters.
        :param width: Image width in pixels.
        :param height: Image height in pixels.
        :param ppmm: Image scaling in pixels per millimeter.
        :return: Dictionary with image parameters.
        """
        params = {
            'width': width,
            'height': height,
            'ppmm': ppmm,
        }
        
        
        return self._GET('positioning_image_parameters', params)
        
    def add_robot_plane_point(self, point):    
        """
        Add new plane point for the determination of DUT plane.
        :param point: Point as list [x, y, z].
        """
        params = {
            'point': point,
        }
        
        
        return self._PUT('add_robot_plane_point', params)
        
    def calculate(self, ):    
        """
        Calculate the DUT positioning based on positioned blobs and plane points.
        :return: Positioning data.
        """
        params = {
        }
        
        
        return self._PUT('calculate', params)
        
    def center_to_blob_in_image(self, dut_name, camera_exposure, camera_gain):    
        """
        Searches for position markers in the image and centers camera to the first found marker.
        :param dut_name: Name of DUT to position.
        :param camera_exposure: Camera exposure (in seconds) to use in blob detection.
        :param camera_gain: Camera gain to use in blob detection.
        """
        params = {
            'dut_name': dut_name,
            'camera_exposure': camera_exposure,
            'camera_gain': camera_gain,
        }
        
        
        return self._PUT('center_to_blob_in_image', params)
        
    def clear_plane_points(self, ):    
        """
        Clear plane points that have been added previously.
        """
        params = {
        }
        
        
        return self._PUT('clear_plane_points', params)
        
    def locate_next_blob(self, ):    
        """
        Searches for the next positioning marker in the sequence.
        :return: ID of detected marker.
        """
        params = {
        }
        
        
        return self._PUT('locate_next_blob', params)
        
    def start(self, dut_name, camera_exposure, camera_gain, position_image_params=None, show_positioning_image=False):    
        """
        Start DUT positioning process.
        :param dut_name: Name of DUT to position.
        :param camera_exposure: Camera exposure (in seconds) to use in blob detection.
        :param camera_gain: Camera gain to use in blob detection.
        :param position_image_params: Dictionary containing positioning image parameters. NOTE: The image parameters
        must match the shown image on the DUT screen. If show_positioning_image is True, this is handled automatically.
        However, if show_positioning_image is False the user manually sets the image on the DUT screen. In this case the
        user must make sure the passed parameters correspond to the image being showed.
        :param show_positioning_image: If true, positioning image is sent to DUT (via DUTServer connection)
        """
        params = {
            'dut_name': dut_name,
            'camera_exposure': camera_exposure,
            'camera_gain': camera_gain,
            'show_positioning_image': show_positioning_image,
        }
        
        if position_image_params is not None:
            params['position_image_params'] = position_image_params
        
        return self._PUT('start', params)
        
    def start_xyz_positioning(self, dut_name, camera_name, camera_exposure, camera_gain, display_ppmm, position_image_params, n_markers=5, show_positioning_image=False):    
        """
        Start complete DUT positioning process which includes sub-steps of surface probing. It is assumed the DUT is
        roughly horizontal and not inclined significantly wrt the robot tooling plate. Before calling this method
        the robot should be at a safe z-height to start centering the camera on found markers.
        :param dut_name: Name of DUT to position.
        :param camera_name: Name of positioning camera.
        :param camera_exposure: Camera exposure to use in blob detection.
        :param camera_gain: Camera gain to use in blob detection.
        :param display_ppmm: Screen ppmm of positioned DUT.
        :param position_image_params: Dictionary containing positioning image parameters. NOTE: The image parameters
        must match the shown image on the DUT screen. If show_positioning_image is True, this is handled automatically.
        However, if show_positioning_image is False the user manually sets the image on the DUT screen. In this case the
        user must make sure the passed parameters correspond to the image being showed.
        :param n_markers: Number of markers to use in positioning.
        :param show_positioning_image: If true, positioning image is sent to DUT (via DUTServer connection)
        """
        params = {
            'dut_name': dut_name,
            'camera_name': camera_name,
            'camera_exposure': camera_exposure,
            'camera_gain': camera_gain,
            'display_ppmm': display_ppmm,
            'position_image_params': position_image_params,
            'n_markers': n_markers,
            'show_positioning_image': show_positioning_image,
        }
        
        
        return self._PUT('start_xyz_positioning', params)
        
