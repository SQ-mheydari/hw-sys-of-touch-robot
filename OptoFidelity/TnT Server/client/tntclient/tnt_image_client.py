
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTImageClient(TnTClientObject):
    """
    Image object that stores image pixels as rectangular array and some metadata such
    as ppmm value that was used in case image was captured with a camera.
    Image is a node meaning that it can also have a homogeneous transform with respect to parent node.
    Operations such as cropping maintain the validity of this transformation.
    Note that only image pixel data is saved so the metadata and transformation are lost on server restart.
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "images", name)
        
    def remove(self):
        """
        Remove the resource.
        After the resource has been removed, the client object is no longer valid.
        """
        return self._DELETE('', {})
    
    def find_objects(self, filename, min_score=0.8, detector='halcon', parameters=None):    
        """
        Find an object from the image.

        :param filename: Name of the icon. This is the same as the icon filename without extension.
        :param min_score: Minimum accepted confidence score of result [0.0 .. 1.0] (default 0.8).
        :param detector: Name of detector to be used in object recognition.
        :param parameters: Optional detection parameters to override default values.
        :return: Dictionary with keys: "success", "results".

        Response body:
                success -- Always True
                results -- Array of Result objects

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

            Note: The bounding box mm coordinates are only calculated in case image object is a transform child
            of e.g. a DUT or a camera. Otherwise the coordinates don't exist in the result dictionary.
        """
        params = {
            'filename': filename,
            'min_score': min_score,
            'detector': detector,
        }
        
        if parameters is not None:
            params['parameters'] = parameters
        
        return self._GET('find_objects', params)
        
    def jpeg(self, ):    
        """
        Get image as JPEG formatted bytearray.
        """
        params = {
        }
        
        
        return self._GET('jpeg', params)
        
    def png(self, ):    
        """
        Get image as PNG formatted bytearray.

        Convert to Numpy array using OpenCV:
        nparr = np.fromstring(png, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        """
        params = {
        }
        
        
        return self._GET('png', params)
        
    def search_text(self, pattern='', regexp=False, language='English', min_score=0.8, case_sensitive=True, detector='abbyy', parameters=None):    
        """
        Search text pattern from the image.

        :param pattern: Text or pattern to find. Search all text with pattern "" (default).
        :param regexp: Use pattern as a regexp. [True | False (default)].
        :param language: OCR language e.g. "English" (default), "Finnish".
        :param min_score: Minimum score (confidence value). 0.0 - 1.0. Default is 0.8,
        value over 0.6 means the sequences are close matches.
        :param case_sensitive: Should the comparison be done case sensitive or not. [True (default) | False]
        :param detector: Name of text detector to use.
        :param parameters: Additional parameters for the OCR engine.
        :return: Dictionary with keys "success", and "results".

        Response body:
                success -- Always True
                results -- Array of Result objects

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

            Note: The bounding box mm coordinates are only calculated in case image object is a transform child
            of e.g. a DUT or a camera. Otherwise the coordinates don't exist in the result dictionary.
        """
        params = {
            'pattern': pattern,
            'regexp': regexp,
            'language': language,
            'min_score': min_score,
            'case_sensitive': case_sensitive,
            'detector': detector,
        }
        
        if parameters is not None:
            params['parameters'] = parameters
        
        return self._GET('search_text', params)
        
    def transform_point(self, x, y):    
        """
        Transform 2D point on the image to parent context.
        In case the parent is DUT, this transforms image pixel coordinates to DUT coordinates which are in mm
        :param x: Image pixel x-coordinate.
        :param y: Image pixel y-coordinate.
        :return: Point in parent context as dict {"x": x, "y": y}.
        """
        params = {
            'x': x,
            'y': y,
        }
        
        
        return self._GET('transform_point', params)
        
    def convert_to_gray_scale(self, ):    
        """
        Convert image to gray scale.
        Operation is applied to the image in memory. Change is not applied to the image file.
        """
        params = {
        }
        
        
        return self._POST('convert_to_gray_scale', params)
        
    def crop(self, crop_left, crop_upper, crop_right, crop_lower, crop_unit):    
        """
        Crop image.
        Cropping is applied to the image in memory. Change is not applied to the image file.
        :param crop_left: Left coordinate for cropping rectangle.
        :param crop_upper: Upper coordinate for cropping rectangle.
        :param crop_right: Right coordinate for cropping rectangle.
        :param crop_lower: Lower coordinate for cropping rectangle.
        :param crop_unit: Unit of crop coordinates. One of "per", "mm", or "pix".
        """
        params = {
            'crop_left': crop_left,
            'crop_upper': crop_upper,
            'crop_right': crop_right,
            'crop_lower': crop_lower,
            'crop_unit': crop_unit,
        }
        
        
        return self._POST('crop', params)
        
    def filter(self, filter_name, parameters=None):    
        """
        Filter image by using Python script.
        The scripts are located under "data/image_filters" and the filter names are specified by
        attribute FILTER_NAME within those files.
        Note: filter should not apply a spatial transform to the image or resize the image. Otherwise transformation
        of pixel coordinates to mm coordinates in e.g. find_objects() becomes invalid.
        :param filter_name: Name of filter specified in the script file.
        :param parameters: Parameter dict to pass to the filter function.
        """
        params = {
            'filter_name': filter_name,
        }
        
        if parameters is not None:
            params['parameters'] = parameters
        
        return self._POST('filter', params)
        
    def invert(self, ):    
        """
        Invert image colors.
        Operation is applied to the image in memory. Change is not applied to the image file.
        """
        params = {
        }
        
        
        return self._POST('invert', params)
        
    def resize(self, width=None, height=None, factor=None):    
        """
        Resizes the image. At least one parameter should have a value. If factor is given width and height should be
        empty. Width and height can be given at same time.
        :param width: New width.
        :param height: New height.
        :param factor: Scale factor for the image.
        """
        params = {
        }
        
        if width is not None:
            params['width'] = width
        if height is not None:
            params['height'] = height
        if factor is not None:
            params['factor'] = factor
        
        return self._POST('resize', params)
        
    def save_image(self, ):    
        """
        Save image to file.
        Image object name is used as filename.
        Note that existing image file will be replaced.
        """
        params = {
        }
        
        
        return self._POST('save_image', params)
        
    def set_jpeg(self, image):    
        """
        Set image data as JPEG.

        :param image: JPEG image as base64 encoded string. Can also be bytes object (will be automatically converted to base64).

        Example:

        with open("image.jpeg", "rb") as file:
            data = file.read()

        image_client.set_jpeg(data)
        """
        params = {
            'image': image,
        }
        
        
        return self._PUT('jpeg', params)
        
    def set_png(self, image):    
        """
        Set image data as PNG.

        :param image: PNG image as base64 encoded string. Can also be bytes object (will be automatically converted to base64).

        Example:

        with open("image.png", "rb") as file:
            data = file.read()

        image_client.set_png(data)
        """
        params = {
            'image': image,
        }
        
        
        return self._PUT('png', params)
        
    @property
    def height(self):
        """
        Image height in pixels.
        """
        return self.get_property('height')
        
    @property
    def width(self):
        """
        Image width in pixels.
        """
        return self.get_property('width')
        
