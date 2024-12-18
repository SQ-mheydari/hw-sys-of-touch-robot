
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTDUTClient(TnTClientObject):
    """
    TnT Compatible DUT resource
    Should work together with
    - TnT Sequencer
    - TnT Positioning Tool
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "duts", name)
        
    def remove(self):
        """
        Remove the resource.
        After the resource has been removed, the client object is no longer valid.
        """
        return self._DELETE('', {})
    
    def info(self, ):    
        """
        Read raw info from DUT device
        :return: info dictionary
        """
        params = {
        }
        
        
        return self._GET('info', params)
        
    def list_buttons(self, ):    
        """
        List button names of the current DUT.

        :return: List of button names.
        """
        params = {
        }
        
        
        return self._GET('list_buttons', params)
        
    def region_contour(self, region, num_points):    
        """
        Return the given region as a list of (x, y) points.
        "contour" as in how OpenCV names the approximation of a shape as a point list:
        'Contours can be explained simply as a curve joining all the continuous points (along the boundary)'
        Can be used to OpenCV shape analysis or any other shape-analysis or geometric operation.
        :param region: Name of the region.
        :param num_points: Number of points to use on contour.
        :return: List of (x, y) contour points, in millimeters. Scaling is applied.
        """
        params = {
            'region': region,
            'num_points': num_points,
        }
        
        
        return self._GET('region_contour', params)
        
    def get_robot_position(self, robot_name='Robot1'):    
        """
        Get the current robot position in DUT coordinates.
        DEPRECATED: Added for client compatibility.
        :param robot_name: Name of robot whose position to get.
        :return: Robot position in DUT coordinates.
        """
        params = {
            'robot_name': robot_name,
        }
        
        
        return self._GET('robot_position', params)
        
    def svg_data(self, ):    
        """
        Return the svg file specified for the dut. If there is
        no specified file, return empty string
        :return: svg file or empty string
        """
        params = {
        }
        
        
        return self._GET('svg_data', params)
        
    def touches(self, ):    
        """
        Gets list of touches since last call of this function.
        If you want to clear the touches buffer, call this function and discard the results.

        Current OptoTouch application supports the following fields:
            x           Touch x-coordinate. Touch resolution is the same as screen pixel resolution.
            y           Touch y-coordinate. Touch resolution is the same as screen pixel resolution.
            pressure    Touch pressure, float value in range 0..1, device dependent and not any standard unit.
            id          Touch id. Sequential number where every new finger to touch the screen
                        takes the first free positive number as id.
            action      Numbered enumeration where:
                        0 = touch start
                        1 = touch end
                        2 = touch move / stays pressed at point
                        3 = touch cancelled
            orientation Stylus event; angle in radians where 0 == north, -pi/2 = west, pi/2 = east
            azimuth     Stylus event; angle in radians where 0 == normal to surface and M_PI/2 is flat to surface.
            distance    Stylus event; 0.0 indicates direct contact and larger values
                                      indicate increasing distance from the surface.

        :return: (dict) where key 'fields' is a list of touch field names.
                    and where key 'touches' is a list of touches. One touch is an array of values.
        """
        params = {
        }
        
        
        return self._GET('touches', params)
        
    def find_objects(self, filename, min_score=0.8, crop_left=None, crop_upper=None, crop_right=None, crop_lower=None, crop_unit=None, exposure=None, gain=None, detector='halcon', offset_x=0, offset_y=0, camera_id='Camera1', duration=None):    
        """
        Find an object model (.shm) from the currently visible portion of the screen.

        :param filename: Name of the icon. This is the same as the icon filename without extension.
        :param min_score: Minimum accepted confidence score of result [0.0 .. 1.0] (default 0.8).
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :param detector: detector node to be used in object recognition
        :param offset_x: Take the picture with an offset in x from the DUT display center. (default is 0)
        :param offset_y: Take the picture with an offset in y from the DUT display center. (default is 0)
        :param camera_id: Name of the camera that is being used. (default is Camera1)
        :param duration: Video capture duration in seconds. Per-pixel maximum is taken over the video frames.
            If set to None only one screenshot is taken.
        :return: Dictionary with keys: "success", "screenshot", "results".

        Response body:
                success -- Always True
                results -- Array of Result objects
                screenshot -- Name of the screenshot

            Result object (dictionary):
                score -- Match score [0.0 .. 1.0]
                topLeftX_px -- Bounding box top left x coordinate in pixels
                topLeftY_px -- Bounding box top left x coordinate in pixels
                bottomRightX_px -- Bounding box bottom right x coordinate in pixels
                bottomRightY_px -- Bounding box bottom right y coordinate in pixels
                centerX_px -- Bounding box center x coordinate in pixels
                centerY_px -- Bounding box center y coordinate in pixels
                topLeftX -- Bounding box top left x coordinate in mm
                topLeftY -- Bounding box top left x coordinate in mm
                bottomRightX -- Bounding box bottom right x coordinate in mm
                bottomRightY -- Bounding box bottom right y coordinate in mm
                centerX -- Bounding box center x coordinate in mm
                centerY -- Bounding box center y coordinate in mm
                shape -- Name of the shape file
                scale -- Detected icon scale
                angle -- Detected icon angle
        """
        params = {
            'filename': filename,
            'min_score': min_score,
            'detector': detector,
            'offset_x': offset_x,
            'offset_y': offset_y,
            'camera_id': camera_id,
        }
        
        if crop_left is not None:
            params['crop_left'] = crop_left
        if crop_upper is not None:
            params['crop_upper'] = crop_upper
        if crop_right is not None:
            params['crop_right'] = crop_right
        if crop_lower is not None:
            params['crop_lower'] = crop_lower
        if crop_unit is not None:
            params['crop_unit'] = crop_unit
        if exposure is not None:
            params['exposure'] = exposure
        if gain is not None:
            params['gain'] = gain
        if duration is not None:
            params['duration'] = duration
        
        return self._POST('find_objects', params)
        
    def screenshot(self, camera_id='Camera1', crop_left=None, crop_upper=None, crop_right=None, crop_lower=None, crop_unit=None, exposure=None, gain=None, offset_x=0, offset_y=0):    
        """
        Take screenshot of DUT screen and save it as image. First moves robot so that camera is
        in the middle of the DUT.
        :param camera_id: Name of camera to take image with.
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        :param exposure: exposure in seconds. If not set, uses last exposure used.
        :param gain: gain value. If not set, uses last gain value used.
        :param offset_x: Take the picture with an offset in x from the DUT display center. (default is 0)
        :param offset_y: Take the picture with an offset in y from the DUT display center. (default is 0)
        :return: Image name.
        """
        params = {
            'camera_id': camera_id,
            'offset_x': offset_x,
            'offset_y': offset_y,
        }
        
        if crop_left is not None:
            params['crop_left'] = crop_left
        if crop_upper is not None:
            params['crop_upper'] = crop_upper
        if crop_right is not None:
            params['crop_right'] = crop_right
        if crop_lower is not None:
            params['crop_lower'] = crop_lower
        if crop_unit is not None:
            params['crop_unit'] = crop_unit
        if exposure is not None:
            params['exposure'] = exposure
        if gain is not None:
            params['gain'] = gain
        
        return self._POST('screenshot', params)
        
    def search_text(self, pattern='', regexp=False, language='English', min_score=0.8, case_sensitive=True, crop_left=None, crop_upper=None, crop_right=None, crop_lower=None, crop_unit=None, exposure=None, gain=None, detector='abbyy', offset_x=0, offset_y=0, filter=None, camera_id='Camera1'):    
        """
        Search text pattern from the visible portion of the DUT screen.

        :param pattern: Text or pattern to find. Search all text with pattern "" (default).
        :param regexp: Use pattern as a regexp. [True | False (default)].
        :param language: OCR language e.g. "English" (default), "Finnish".
        :param min_score: Minimum score (confidence value). 0.0 - 1.0. Default is 0.8,
        value over 0.6 means the sequences are close matches.
        :param case_sensitive: Should the comparison be done case sensitive or not. [True (default) | False]
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        :param exposure: Exposure in seconds. If not set, uses last exposure used.
        :param gain: Gain value. If not set, uses last gain value used.
        :param detector: Name of text detector to use.
        :param offset_x: Take the picture with an offset in x from the DUT display center. (default is 0)
        :param offset_y: Take the picture with an offset in y from the DUT display center. (default is 0)
        :param filter: Name of filter to apply to the image before text search. None to use no filtering (default).
        :param camera_id: Name of the camera that is being used. (default is Camera1)
        :return: Dictionary with keys "success", "results" and "screenshot".

            Response body:
                success -- Always True
                results -- Array of Result objects
                screenshot -- Name of the screenshot

                The results array is ordered in page order i.e. text found from left to right and top to bottom.
                Note that this means that the first item might not have the highest score.

            Result object (dictionary):
                score -- Match score [0.0 .. 1.0]
                topLeftX_px -- Bounding box top left x coordinate in pixels
                topLeftY_px -- Bounding box top left x coordinate in pixels
                bottomRightX_px -- Bounding box bottom right x coordinate in pixels
                bottomRightY_px -- Bounding box bottom right y coordinate in pixels
                centerX_px -- Bounding box center x coordinate in pixels
                centerY_px -- Bounding box center y coordinate in pixels
                topLeftX -- Bounding box top left x coordinate in mm
                topLeftY -- Bounding box top left x coordinate in mm
                bottomRightX -- Bounding box bottom right x coordinate in mm
                bottomRightY -- Bounding box bottom right y coordinate in mm
                centerX -- Bounding box center x coordinate in mm
                centerY -- Bounding box center y coordinate in mm
        """
        params = {
            'pattern': pattern,
            'regexp': regexp,
            'language': language,
            'min_score': min_score,
            'case_sensitive': case_sensitive,
            'detector': detector,
            'offset_x': offset_x,
            'offset_y': offset_y,
            'camera_id': camera_id,
        }
        
        if crop_left is not None:
            params['crop_left'] = crop_left
        if crop_upper is not None:
            params['crop_upper'] = crop_upper
        if crop_right is not None:
            params['crop_right'] = crop_right
        if crop_lower is not None:
            params['crop_lower'] = crop_lower
        if crop_unit is not None:
            params['crop_unit'] = crop_unit
        if exposure is not None:
            params['exposure'] = exposure
        if gain is not None:
            params['gain'] = gain
        if filter is not None:
            params['filter'] = filter
        
        return self._POST('search_text', params)
        
    def filter_lines(self, lines, region, margin=0):    
        """
        Filter list of (x1, y1, x2, y2) lines with given region and margin.
        The filter will cut lines to pieces that fit inside the region with given margin.
        One given line can result to none or several lines.
        :param lines: List of (x1, y1, x2, y2) lines, in millimeters.
        :param region: Name of the filter region.
        :param margin: Margin inwards the region, millimeters.
        :return: List of list of (x1, y1, x2, y2) lines (each given line results to a list of lines).
        """
        params = {
            'lines': lines,
            'region': region,
            'margin': margin,
        }
        
        
        return self._PUT('filter_lines', params)
        
    def filter_points(self, points, region, margin=0):    
        """
        Filter a list of points that are inside of DUT shape, given region and margin.
        :param points: List of (x, y) points, millimeters.
        :param region: Name of the region.
        :param margin: Margin inwards the given region, millimeters.
        :return: Filtered list of (x, y) points.
        """
        params = {
            'points': points,
            'region': region,
            'margin': margin,
        }
        
        
        return self._PUT('filter_points', params)
        
    def move(self, x, y, z, tilt=None, azimuth=None, robot_name='Robot1'):    
        """
        Moves in to given DUT position via straight path.
        DEPRECATED: Added for client compatibility.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT.
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param robot_name: Name of robot to move.
        """
        params = {
            'x': x,
            'y': y,
            'z': z,
            'robot_name': robot_name,
        }
        
        if tilt is not None:
            params['tilt'] = tilt
        if azimuth is not None:
            params['azimuth'] = azimuth
        
        return self._PUT('move', params)
        
    def show_image(self, image):    
        """
        Shows image on DUT screen.
        If image is bytes object, use:
        image = base64.decodebytes(image.encode("ascii"))

        :param image: base64 encoded data. None will empty the screen
        :return: "ok" / error
        """
        params = {
            'image': image,
        }
        
        
        return self._PUT('show_image', params)
        
    def circle(self, x, y, r, n=1, angle=0, z=None, tilt=0, azimuth=0, clearance=0, clockwise=False, separation=None, tool_name=None):    
        """
        Performs a circle movement with given parameters.

        :param x: Circle center x coordinate on DUT.
        :param y: Circle center y coordinate on DUT.
        :param r: Circle radius.
        :param n: How many circles should be moved. Can be floating point.
        :param angle: Start angle in degrees. For 0 angle, start x is x+r and start y is y.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: Coordinate z on dut when moving in circle (default: 0).
        :param clockwise: True if moving clockwise, false to move counter clockwise (default: false).
        :param separation: Separation during circle. If None, then default separation is used.
        :param tool_name: Name of tool to perform circle with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """
        params = {
            'x': x,
            'y': y,
            'r': r,
            'n': n,
            'angle': angle,
            'tilt': tilt,
            'azimuth': azimuth,
            'clearance': clearance,
            'clockwise': clockwise,
        }
        
        if z is not None:
            params['z'] = z
        if separation is not None:
            params['separation'] = separation
        if tool_name is not None:
            params['tool_name'] = tool_name
        
        return self._PUT('gestures/circle', params)
        
    def double_tap(self, x, y, z=None, tilt=0, azimuth=0, clearance=0, duration=0, interval=0, separation=None, tool_name=None):    
        """
        Performs a double tap with given parameters.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: Target z coordinate on DUT when tapping (default: 0).
        :param duration: How long to keep finger down in seconds (default: 0s).
        :param interval: How long to pause between taps in seconds (default: 0s).
        :param separation: Separation during tap. If None, then default separation is used.
        :param tool_name: Name of tool to perform tap with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """
        params = {
            'x': x,
            'y': y,
            'tilt': tilt,
            'azimuth': azimuth,
            'clearance': clearance,
            'duration': duration,
            'interval': interval,
        }
        
        if z is not None:
            params['z'] = z
        if separation is not None:
            params['separation'] = separation
        if tool_name is not None:
            params['tool_name'] = tool_name
        
        return self._PUT('gestures/double_tap', params)
        
    def drag(self, x1, y1, x2, y2, z=None, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, predelay=0, postdelay=0, separation=None, tool_name=None):    
        """
        Performs a drag with given parameters.

        :param x1: Start x coordinate on DUT.
        :param y1: Start y coordinate on DUT.
        :param x2: End x coordinate on DUT.
        :param y2: End y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt1: Start tilt angle in DUT frame.
        :param tilt2: End tilt angle in DUT frame.
        :param azimuth1: Start azimuth angle in DUT frame.
        :param azimuth2: End azimuth angle in DUT frame.
        :param clearance: Z coordinate on DUT when running drag (default: 0)
        :param predelay: Delay between touchdown and move in seconds.
        :param postdelay: Delay between the end of movement and touchup in seconds.
        :param separation: Separation during drag. If None, then default separation is used.
        :param tool_name: Name of tool to perform drag with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """
        params = {
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
            'tilt1': tilt1,
            'tilt2': tilt2,
            'azimuth1': azimuth1,
            'azimuth2': azimuth2,
            'clearance': clearance,
            'predelay': predelay,
            'postdelay': postdelay,
        }
        
        if z is not None:
            params['z'] = z
        if separation is not None:
            params['separation'] = separation
        if tool_name is not None:
            params['tool_name'] = tool_name
        
        return self._PUT('gestures/drag', params)
        
    def drag_force(self, x1, y1, x2, y2, force, z=None, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, separation=None, tool_name=None):    
        """
        Performs a drag with force with given parameters.

        Force can be applied with tool1, tool2 or with both simultaneously. Note that the tool that is used
        must have a valid force calibration table in the configuration. Otherwise exception is raised.
        In case both tools are used, the given force is per tool so that force=100 & tool_name="both" will apply
        200 gF on the target.

        :param x1: Start x coordinate on DUT.
        :param y1: Start y coordinate on DUT.
        :param x2: End x coordinate on DUT.
        :param y2: End y coordinate on DUT.
        :param force: Grams of force to apply when running on DUT surface.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt1: Start tilt angle in DUT frame.
        :param tilt2: End tilt angle in DUT frame.
        :param azimuth1: Start azimuth angle in DUT frame.
        :param azimuth2: End azimuth angle in DUT frame.
        :param separation: Separation during drag force. If None, then default separation is used.
        :param tool_name: Name of tool to perform drag force with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """
        params = {
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
            'force': force,
            'tilt1': tilt1,
            'tilt2': tilt2,
            'azimuth1': azimuth1,
            'azimuth2': azimuth2,
        }
        
        if z is not None:
            params['z'] = z
        if separation is not None:
            params['separation'] = separation
        if tool_name is not None:
            params['tool_name'] = tool_name
        
        return self._PUT('gestures/drag_force', params)
        
    def jump(self, x, y, z=0, jump_height=None):    
        """
        Performs a jump with given parameters.
        In case jump_height is not given, robot jumps to maximum height along robot z axis.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT.
        :param jump_height: Height of the jump from DUT surface (default: jump to robot maximum height).
        """
        params = {
            'x': x,
            'y': y,
            'z': z,
        }
        
        if jump_height is not None:
            params['jump_height'] = jump_height
        
        return self._PUT('gestures/jump', params)
        
    def multi_tap(self, points, lift=2, clearance=0):    
        """
        Performs multiple tap gestures in DUT context according to given points.
        Start and end of multi-tap sequence is the base distance of the DUT.

        :param points: List of TnTDUTPoint objects indicating where to tap. Z coordinates of the points
                       are ignored and lift and clearance are used for tap movement.
        :param lift: Distance of how high the effector is raised from the DUT between the taps.
        :param clearance: Z coordinate on DUT on tap down (default: 0).
        """
        params = {
            'points': points,
            'lift': lift,
            'clearance': clearance,
        }
        
        
        return self._PUT('gestures/multi_tap', params)
        
    def path(self, points, clearance=0, separation=None, tool_name=None):    
        """
        Performs path movement through given points.

        :param points: List of points to go through.
        :param clearance: Clearance added to z value of each point.
        :param separation: Separation during path. If None, then default separation is used.
        :param tool_name: Name of tool to perform path with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        """
        params = {
            'points': points,
            'clearance': clearance,
        }
        
        if separation is not None:
            params['separation'] = separation
        if tool_name is not None:
            params['tool_name'] = tool_name
        
        return self._PUT('gestures/path', params)
        
    def pinch(self, x, y, d1, d2, azimuth, z=None, clearance=0):    
        """
        Performs a pinch gesture in DUT context.

        :param x: Target x coordinate on DUT. Target is the middle position between fingers.
        :param y: Target y coordinate on DUT. Target is the middle position between fingers.
        :param d1: Distance between fingers at the beginning.
        :param d2: Distance between fingers at the end.
        :param azimuth: Azimuth angle during the pinch.
        :param z: Overrides base distance.
        :param clearance: Distance from DUT surface during gesture.
        :return: "ok" / error
        """
        params = {
            'x': x,
            'y': y,
            'd1': d1,
            'd2': d2,
            'azimuth': azimuth,
            'clearance': clearance,
        }
        
        if z is not None:
            params['z'] = z
        
        return self._PUT('gestures/pinch', params)
        
    def press(self, x, y, force, z=None, tilt=0, azimuth=0, duration=0, press_depth=-1, separation=None, tool_name=None):    
        """
        Performs a press gesture in DUT context.

        Force can be applied with tool1, tool2 or with both simultaneously. Note that the tool that is used
        must have a valid force calibration table in the configuration. Otherwise exception is raised.
        In case both tools are used, the given force is per tool so that force=100 & tool_name="both" will apply
        200 gF on the target.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param force: Force in grams, to be activated after moving to lower position.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param duration: How long to keep specified force active in seconds (default: 0s).
        :param press_depth: Distance from DUT surface during press, negative values being below/through DUT surface.
        Tip will be pressed to the desired depth if the force limit is not reached before that.
        If the force limit is reached before desired depth, the movement will stop there. (default: -1mm).
        :param separation: Separation during press. If None, then current separation is used.
        :param tool_name: Name of tool to perform press with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        :return: "ok" / error
        """
        params = {
            'x': x,
            'y': y,
            'force': force,
            'tilt': tilt,
            'azimuth': azimuth,
            'duration': duration,
            'press_depth': press_depth,
        }
        
        if z is not None:
            params['z'] = z
        if separation is not None:
            params['separation'] = separation
        if tool_name is not None:
            params['tool_name'] = tool_name
        
        return self._PUT('gestures/press', params)
        
    def swipe(self, x1, y1, x2, y2, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6, separation=None, tool_name=None):    
        """
        Performs a swipe with given parameters.
        Robot accelerates and decelerates along an arc of given radius before and after touching the DUT.

        :param x1: Swipe start x coordinate on DUT.
        :param x2: Swipe end x coordinate on DUT.
        :param y1: Swipe start y coordinate on DUT.
        :param y2: Swipe end y coordinate on DUT.
        :param tilt1: Swipe start tilt.
        :param tilt2: Swipe end tilt.
        :param azimuth1: Swipe start azimuth.
        :param azimuth2: Swipe end azimuth.
        :param clearance: (optional) distance from DUT surface during movement
        :param radius: Swipe radius.
        :param separation: Separation during swipe. If None, then default separation is used.
        :param tool_name: Name of tool to perform swipe with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        :return: "ok" / error
        """
        params = {
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
            'tilt1': tilt1,
            'tilt2': tilt2,
            'azimuth1': azimuth1,
            'azimuth2': azimuth2,
            'clearance': clearance,
            'radius': radius,
        }
        
        if separation is not None:
            params['separation'] = separation
        if tool_name is not None:
            params['tool_name'] = tool_name
        
        return self._PUT('gestures/swipe', params)
        
    def tap(self, x, y, z=None, tilt=0, azimuth=0, clearance=0, duration=0, separation=None, tool_name=None, kinematic_name=None):    
        """
        Performs a tap with given parameters.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: (optional) distance from DUT surface during movement
        :param duration: How long to keep finger down in seconds (default: 0s).
        :param separation: Separation during tap. If None, then default separation is used.
        :param tool_name: Name of tool to perform tap with. One of 'tool1', 'tool2', 'both' or None. None is the same as 'tool1'.
        :param kinematic_name: Name of kinematic to perform tap with. One of 'tool1', 'tool2', 'mid', 'synchro' or None.  None is the same as 'tool1'.
        :return: "ok" / error
        """
        params = {
            'x': x,
            'y': y,
            'tilt': tilt,
            'azimuth': azimuth,
            'clearance': clearance,
            'duration': duration,
        }
        
        if z is not None:
            params['z'] = z
        if separation is not None:
            params['separation'] = separation
        if tool_name is not None:
            params['tool_name'] = tool_name
        if kinematic_name is not None:
            params['kinematic_name'] = kinematic_name
        
        return self._PUT('gestures/tap', params)
        
    def watchdog_tap(self, x, y, z=None, tilt=0, azimuth=0, clearance=0, duration=0, trigger_direction=None):    
        """
        Performs a tap designed for HW level triggering based on when the DUT is touched.
        Example use case is watchdog measurement.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT when hovering before and after gesture (default: DUT's base_distance).
        :param tilt: Tilt angle in DUT frame (default: 0).
        :param azimuth: Azimuth angle in DUT frame (default: 0).
        :param clearance: (optional) distance from DUT surface during movement
        :param duration: How long to keep finger down in seconds (default: 0s).
        :param trigger_direction: Trigger when touching the DUT.
                                  None means that no triggering is done.
                                  "TOUCH_START" triggers when tool goes down to start touching the DUT.
                                  "TOUCH_END" triggers when tool goes up from DUT detach from it.
        :return: "ok" / error
        """
        params = {
            'x': x,
            'y': y,
            'tilt': tilt,
            'azimuth': azimuth,
            'clearance': clearance,
            'duration': duration,
        }
        
        if z is not None:
            params['z'] = z
        if trigger_direction is not None:
            params['trigger_direction'] = trigger_direction
        
        return self._PUT('gestures/watchdog_tap', params)
        
    @property
    def base_distance(self):
        """
        DUT base distance.
        """
        return self.get_property('base_distance')
        
    @base_distance.setter
    def base_distance(self, value):
        """
        DUT base distance.
        """
        self.set_property('base_distance', value)
        
    @property
    def bl(self):
        """
        Position of bottom left corner of the DUT.
        """
        return self.get_property('bl')
        
    @bl.setter
    def bl(self, value):
        """
        Position of bottom left corner of the DUT.
        """
        self.set_property('bl', value)
        
    @property
    def bottom_left(self):
        """
        Bottom left corner.
        DEPRECATED: Added for client compatibility.
        """
        return self.get_property('bottom_left')
        
    @bottom_left.setter
    def bottom_left(self, value):
        """
        Bottom left corner.
        DEPRECATED: Added for client compatibility.
        """
        self.set_property('bottom_left', value)
        
    @property
    def bottom_right(self):
        """
        Bottom right corner.
        This property can't be set. The value is calculated from tl, tr and bl.
        DEPRECATED: Added for client compatibility.
        """
        return self.get_property('bottom_right')
        
    @property
    def br(self):
        """
        Position of bottom right corner of the DUT.
        This property can't be set. The value is calculated from tl, tr and bl.
        """
        return self.get_property('br')
        
    @property
    def height(self):
        """
        DUT height in mm.
        """
        return self.get_property('height')
        
    @height.setter
    def height(self, value):
        """
        DUT height in mm.
        """
        self.set_property('height', value)
        
    @property
    def orientation(self):
        """
        Orientation of the DUT i.e. the basis vectors of DUT's transform matrix.
        Given as dictionary {'i': x_basis_vector, 'j': y_basis_vector, 'k': z_basis_vector}.
        """
        return self.get_property('orientation')
        
    @property
    def position(self):
        """
        Corner positions of the DUT in its relative coordinate system context.
        Property is in dictionary from {"top_left": top_left, "top_right": top_right,
        "bottom_left": bottom_left, "bottom_right": bottom_right}.
        DEPRECATED: Exists for client compatibility.
        """
        return self.get_property('position')
        
    @property
    def tl(self):
        """
        Position of top left corner of the DUT.
        """
        return self.get_property('tl')
        
    @tl.setter
    def tl(self, value):
        """
        Position of top left corner of the DUT.
        """
        self.set_property('tl', value)
        
    @property
    def top_left(self):
        """
        Top left corner.
        DEPRECATED: Added for client compatibility.
        """
        return self.get_property('top_left')
        
    @top_left.setter
    def top_left(self, value):
        """
        Top left corner.
        DEPRECATED: Added for client compatibility.
        """
        self.set_property('top_left', value)
        
    @property
    def top_right(self):
        """
        Top right corner.
        DEPRECATED: Added for client compatibility.
        """
        return self.get_property('top_right')
        
    @top_right.setter
    def top_right(self, value):
        """
        Top right corner.
        DEPRECATED: Added for client compatibility.
        """
        self.set_property('top_right', value)
        
    @property
    def tr(self):
        """
        Position of top right corner of the DUT.
        """
        return self.get_property('tr')
        
    @tr.setter
    def tr(self, value):
        """
        Position of top right corner of the DUT.
        """
        self.set_property('tr', value)
        
    @property
    def width(self):
        """
        DUT width in mm.
        """
        return self.get_property('width')
        
    @width.setter
    def width(self, value):
        """
        DUT width in mm.
        """
        self.set_property('width', value)
        
