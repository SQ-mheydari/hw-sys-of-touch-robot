import time
import os
import cv2
import numpy as np
from scipy import misc
import base64
import logging
import importlib
from pathlib import Path

from typing_extensions import Literal

from tntserver.Nodes.Node import Node, json_out, jpeg_out, png_out, private
from tntserver.Nodes.TnT import DeletableNode
from tntserver import robotmath

log = logging.getLogger(__name__)


def image_data_to_http_response(filetype, image):
    """
    Convert filetype and image data to correct HTTP response.
    :param filetype: Filetype as string.
    :param image: Image as Numpy array.
    :return: HTTP response (content_type, data).
    """
    data = None
    t = "text/string"

    if filetype == "none":
        data = image
        t = "raw"
    elif filetype == "jpg":
        r, data = cv2.imencode(".jpg", image)
        t = "image/jpeg"
    elif filetype == "png":
        r, data = cv2.imencode(".png", image)
        t = "image/png"
    elif filetype == "raw":
        data = str(np.asarray(image)).encode("ascii")
        t = "text/string"
    elif filetype == "bytes":
        h, w = image.shape[:2]
        d = image.shape[2] if len(image.shape) > 2 else 1
        header = bytearray()
        header += int.to_bytes(w, 4, byteorder="big")
        header += int.to_bytes(h, 4, byteorder="big")
        header += int.to_bytes(d, 4, byteorder="big")
        data = image.tobytes()
        data = header + data
        t = "application/octet-stream"
    elif filetype == "npy":
        import io
        b = io.BytesIO()
        np.save(b, image)
        data = b.getvalue()
        t = "image/npy"

    return t, data


class Image(DeletableNode):
    """
    Image object that stores image pixels as rectangular array and some metadata such
    as ppmm value that was used in case image was captured with a camera.
    Image is a node meaning that it can also have a homogeneous transform with respect to parent node.
    Operations such as cropping maintain the validity of this transformation.
    Note that only image pixel data is saved so the metadata and transformation are lost on server restart.
    """
    transient = True

    def __init__(self, name):
        super().__init__(name)

        # Cache for image data, cleared every time image is saved.
        self._data_temp = None

        self.time = time.time()

        # TODO: ppmm should be removed as basically image size and frame determine the mapping from pixels to mm.
        self.ppmm = 1

    def _init(self, **kwargs):
        pass

    @json_out
    def get_self(self):
        image_stats = {
            "name": self.name,
            "properties": {
                "height": self.height,
                "width": self.width,
                "time": self.time,
                "size": self.size
            }
        }
        return image_stats

    @jpeg_out
    def get_jpeg(self):
        """
        Get image as JPEG formatted bytearray.
        """
        return self.jpeg()

    def jpeg(self):
        return cv2.imencode(ext='.jpg', img=self.data)[1]

    @json_out
    def put_jpeg(self, image : str):
        """
        Set image data as JPEG.

        :param image: JPEG image as base64 encoded string. Can also be bytes object (will be automatically converted to base64).

        Example:

        with open("image.jpeg", "rb") as file:
            data = file.read()

        image_client.set_jpeg(data)
        """
        # Decode string to bytes.
        image = base64.decodebytes(image.encode("ascii"))

        # Decode from bytes to numpy array.
        self.data = cv2.imdecode(np.asarray(bytearray(image), dtype=np.uint8), cv2.IMREAD_COLOR)

        self.save_image()

    @png_out
    def get_png(self):
        """
        Get image as PNG formatted bytearray.

        Convert to Numpy array using OpenCV:
        nparr = np.fromstring(png, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        """
        return self.png()

    def png(self):
        return cv2.imencode(ext='.png', img=self.data)[1]

    @json_out
    def put_png(self, image: str):
        """
        Set image data as PNG.

        :param image: PNG image as base64 encoded string. Can also be bytes object (will be automatically converted to base64).

        Example:

        with open("image.png", "rb") as file:
            data = file.read()

        image_client.set_png(data)
        """
        # Decode string to bytes.
        image = base64.decodebytes(image.encode("ascii"))

        # Decode from bytes to numpy array.
        self.data = cv2.imdecode(np.asarray(bytearray(image), dtype=np.uint8), cv2.IMREAD_COLOR)

        self.save_image()

    @property
    @private
    def data(self):
        if self._data_temp is not None:
            return self._data_temp

        data = None
        if self.image_path.endswith(".png"):
            try:
                data = cv2.imread(self.image_path)
            except FileNotFoundError:
                pass  # File data has not been saved yet.
        elif self.image_path.endswith(".npy"):
            # Image can also be saved as numpy array in older systems.
            try:
                data = np.load(self.image_path)
            except FileNotFoundError:
                pass  # File data has not been saved yet.

        return data

    @data.setter
    def data(self, value):
        self._data_temp = value

    @property
    @private
    def width(self):
        """
        Image width in pixels.
        """
        if self.data is None:
            return 0

        return np.size(self.data, 1)

    @property
    @private
    def height(self):
        """
        Image height in pixels.
        """
        if self.data is None:
            return 0

        return np.size(self.data, 0)

    @property
    @private
    def center_x(self):
        return int(self.width / 2)

    @property
    @private
    def center_y(self):
        return int(self.height / 2)

    @property
    def ppmm(self):
        return self._ppmm

    @ppmm.setter
    def ppmm(self, value):
        self._ppmm = value

    @property
    @private
    def size(self):
        if self.data is None:
            return 0, 0

        return self.data.shape[:2]

    def invert(self):
        """
        Invert image colors.
        """

        # Bitwise invert is the same as (255 - color).
        self.data = np.invert(self.data)

    @json_out
    def post_invert(self):
        """
        Invert image colors.
        Operation is applied to the image in memory. Change is not applied to the image file.
        """
        self.invert()

    def convert_to_gray_scale(self):
        """
        Convert image to gray scale.
        """

        # Do nothing if image is already gray scale.
        if len(self.data.shape) == 2:
            return

        self.data = cv2.cvtColor(self.data, cv2.COLOR_BGR2GRAY)

    @json_out
    def post_convert_to_gray_scale(self):
        """
        Convert image to gray scale.
        Operation is applied to the image in memory. Change is not applied to the image file.
        """
        self.convert_to_gray_scale()

    def resize(self, width=None, height=None, factor=None):
        """
        Resizes the image. At least one parameter should have a value. If factor is given width and height should be
        empty. Width and height can be given at same time.
        :param width: New width.
        :param height: New height.
        :param factor: Scale factor for the image.
        """
        aspect_ratio = self.width / self.height

        if not width and not height and not factor:
            raise ValueError("All parameters were empty")

        if factor is not None:
            if width or height:
                raise ValueError("Factor cannot be given with width or height")
            else:
                width = self.width * factor
                height = self.height * factor
        elif height and not width:
            width = aspect_ratio * height
        elif width and not height:
            height = width / aspect_ratio

        self.data = cv2.resize(self.data, (max(1, int(round(width))), max(1, int(round(height)))),
                               interpolation=cv2.INTER_CUBIC)

    @json_out
    def post_resize(self, width=None, height=None, factor=None):
        """
        Resizes the image. At least one parameter should have a value. If factor is given width and height should be
        empty. Width and height can be given at same time.
        :param width: New width.
        :param height: New height.
        :param factor: Scale factor for the image.
        """
        self.resize(width, height, factor)

    def px_to_mm(self, px_value):
        """
            Convert pixels into millimeters (<float>).
        """
        return px_value / self.ppmm

    def px_to_mm_pose(self, x, y):
        """
            Convert coordinates given in pixels into pose object
            (relative to image pose).
        """
        x_mm = self.px_to_mm(x - self.width / 2)
        y_mm = self.px_to_mm(y - self.height / 2)

        # TnT compatibility
        return {'i': x_mm, 'j': y_mm, 'k': 0}

    def crop(self, crop_left, crop_upper, crop_right, crop_lower, crop_unit):
        """
        Crop image.
        Cropping is applied to the image in memory. Change is not applied to the image file.
        :param crop_left: Left coordinate for cropping rectangle. If None then 0 is used.
        :param crop_upper: Upper coordinate for cropping rectangle. If None then 0 is used.
        :param crop_right: Right coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_lower: Lower coordinate for cropping rectangle. If None then maximum value is used.
        :param crop_unit: Unit of crop coordinates One of "per", "pix" or "mm".
        """

        crop_left, crop_upper, crop_right, crop_lower = \
            convert_crop_to_pixels(crop_left, crop_upper, crop_right, crop_lower, self.width, self.height,
                                   self.ppmm, crop_unit)

        # Apply offset to image frame. Note that self.frame maps from pixel space to mm space so offset
        # transform is in pixel units.
        offset = robotmath.xyz_to_frame(crop_left, crop_upper, 0)
        self.frame = self.frame * offset

        self.data = self.data[crop_upper:crop_lower, crop_left:crop_right]

    @json_out
    def post_crop(self, crop_left, crop_upper, crop_right, crop_lower, crop_unit):
        """
        Crop image.
        Cropping is applied to the image in memory. Change is not applied to the image file.
        :param crop_left: Left coordinate for cropping rectangle.
        :param crop_upper: Upper coordinate for cropping rectangle.
        :param crop_right: Right coordinate for cropping rectangle.
        :param crop_lower: Lower coordinate for cropping rectangle.
        :param crop_unit: Unit of crop coordinates. One of "per", "mm", or "pix".
        """

        self.crop(crop_left, crop_upper, crop_right, crop_lower, crop_unit)

    @property
    @private
    def images(self):
        """
        Images node that is the container of this image.
        """
        if self.parent is None or self.parent.__class__.__name__ != "Images":
            raise Exception("Image object must be a child of Images object.")

        return self.parent

    def save_image(self):
        if self.data is None:
            raise Exception("Image can't be saved because no data has been set!")

        # Self.image_path can return also .npy paths so we need to make sure we are using png.
        image_path = os.path.join(self.image_folder_path, '{}.png'.format(self.name))

        cv2.imwrite(image_path, self.data, [cv2.IMWRITE_PNG_COMPRESSION, 0])

        # After image is saved we'll free the used memory.
        self._data_temp = None

    @json_out
    def post_save_image(self):
        """
        Save image to file.
        Image object name is used as filename.
        Note that existing image file will be replaced.
        """
        self.save_image()

    @property
    @private
    def image_folder_path(self):
        """
        Image folder path.
        """

        # This is defined by Images node which should be the parent of Image node.
        return self.images.image_folder_path

    @property
    @private
    def image_path(self):
        """
        Image path.
        """
        # Older systems have saved images as numpy arrays so the case needs to be checked.
        npy_path = os.path.join(self.image_folder_path, '{}.npy'.format(self.name))
        png_path = os.path.join(self.image_folder_path, '{}.png'.format(self.name))

        if Path(npy_path).is_file():
            return npy_path
        else:
            return png_path

    def get_data(self, filetype: Literal["none", "jpg", "png", "raw", "bytes", "npy"]):
        """
        Get image data in chosen filetype.
        :param filetype: Filetype of the returned image.
        """
        img = self.data

        t, img_as_http_response = image_data_to_http_response(filetype, img)
        return t, img_as_http_response

    def set_data(self, data):
        """
        Set image data.
        :param data: Image data as numpy array
        """

        self.data = data
        self.save_image()

    def remove(self):
        """
        Remove image resource.
        Deletes also associated image files.
        """
        try:
            os.remove(os.path.join(self.image_folder_path, '{}.png'.format(self.name)))
        except FileNotFoundError:
            pass  # It is ok if file does not exist in case user has deleted it.

        # In older versions npy was used as saving format which needs to be supported.
        try:
            os.remove(os.path.join(self.image_folder_path, '{}.npy'.format(self.name)))
        except FileNotFoundError:
            pass  # It is ok if file does not exist in case user has deleted it.

        return super().remove()

    @json_out
    def get_search_text(self, pattern="", regexp=False, language='English', min_score=0.8, case_sensitive=True,
                         detector='abbyy'):
        """
        Search text pattern from the image.

        :param pattern: Text or pattern to find. Search all text with pattern "" (default).
        :param regexp: Use pattern as a regexp. [True | False (default)].
        :param language: OCR language e.g. "English" (default), "Finnish".
        :param min_score: Minimum score (confidence value). 0.0 - 1.0. Default is 0.8,
        value over 0.6 means the sequences are close matches.
        :param case_sensitive: Should the comparison be done case sensitive or not. [True (default) | False]
        :param detector: Name of text detector to use.
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
        results = search_text(self.data, pattern, regexp, language, min_score, case_sensitive, detector)

        if self.valid_transform:
            calculate_detection_result_coordinates(results, self)

        return results

    @json_out
    def get_find_objects(self, filename, min_score=0.8, detector='halcon'):
        """
        Find an object from the image.

        :param filename: Name of the icon. This is the same as the icon filename without extension.
        :param min_score: Minimum accepted confidence score of result [0.0 .. 1.0] (default 0.8).
        :param detector: Name of detector to be used in object recognition.
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

        results = find_objects(image=self.data, icon_name=filename, min_score=min_score, detector=detector)

        if self.valid_transform:
            calculate_detection_result_coordinates(results, self)

        return results

    @property
    @private
    def valid_transform(self):
        parent = self.object_parent.__class__.__name__

        return parent in ["Dut", "Camera"]

    def filter(self, filter_name, parameters=None):
        """
        Filter image by using Python script.
        :param filter_name: Name of filter specified in the script file.
        :param parameters: Parameter dict to pass to the filter function.
        """

        path = os.path.join("data", "image_filters", filter_name + ".py")

        if not os.path.exists(path):
            raise Exception("Filter {} not found. Expected path '{}' to exist.".format(filter_name, path))

        module = importlib.import_module('data.image_filters.' + filter_name)

        if not hasattr(module, "filter_image"):
            raise Exception("Image filter '{}' must define method 'filter_image".format(filter_name))

        filter_function = getattr(module, "filter_image")

        if not callable(filter_function):
            raise Exception("Image filter '{}' does not define callable 'filter_image' function.".format(filter_name))

        self.data = filter_function(self.data, parameters)

    @json_out
    def post_filter(self, filter_name, parameters=None):
        """
        Filter image by using Python script.
        The scripts are located under "data/image_filters" and the filter names are specified by
        attribute FILTER_NAME within those files.
        Note: filter should not apply a spatial transform to the image or resize the image. Otherwise transformation
        of pixel coordinates to mm coordinates in e.g. find_objects() becomes invalid.
        :param filter_name: Name of filter specified in the script file.
        :param parameters: Parameter dict to pass to the filter function.
        """
        self.filter(filter_name, parameters)

        # Save image for debugging. Should not save automatically when called by user.
        #self.save_image()

    def transform_point(self, x, y):
        """
        Transform 2D point on the image to parent context.
        In case the parent is DUT, this transforms image pixel coordinates to DUT coordinates which are in mm.
        :param x: Image pixel x-coordinate.
        :param y: Image pixel y-coordinate.
        :return: (x, y) point in parent context.
        """
        if not self.valid_transform:
            raise Exception("Image does not define a valid transformation to parent context.")

        point = robotmath.xyz_to_frame(x, y, 0)
        point = self.frame * point

        point = robotmath.frame_to_xyz(point)

        return float(point[0]), float(point[1])

    @json_out
    def get_transform_point(self, x, y):
        """
        Transform 2D point on the image to parent context.
        In case the parent is DUT, this transforms image pixel coordinates to DUT coordinates which are in mm
        :param x: Image pixel x-coordinate.
        :param y: Image pixel y-coordinate.
        :return: Point in parent context as dict {"x": x, "y": y}.
        """

        point = self.transform_point(x, y)

        return {"x": point[0], "y": point[1]}


def search_text(image, pattern: str=None, regexp: bool=False, language: str='English', min_score: float=0.6,
                case_sensitive: bool=False, detector: str='abbyy', **kwargs) -> dict:
    """
    Search for text from an image using selected OCR engine
    :param image: image as numpy array
    :param pattern: pattern to search for: character, word or sentence
    :param regexp: flag for is pattern a regular-expression, True or False
    :param language:
    :param min_score: 0.0 - 1.0, > 0.6 is "close match"
    :param case_sensitive: flag for is pattern case sensitive, True or False
    :param detector: detector name ('abbyy' or 'tesseract')
    :param kwargs: extra parameters required for for example Tesseract, like: oem, psm
    :return: {
        'results': [
            {'topLeftX_px': 135,
            'text': 'alfie',
            'topLeftY_px': 43,
            'centerX_px': 159.5,
            'bottomRightY_px': 63,
            'confidence': 92.99671936035156,    # only from Tesseract
            'score': 1.0,
            'centerY_px': 53.0,
            'bottomRightX_px': 184}, ...
        ],
        'success': True
    }
    """
    detectors = Node.find("detectors")

    if detectors is None:
        raise Exception("Node 'detectors' not found. Revise configuration.")

    detector = Node.find_from(detectors, detector)

    if detector is None:
        raise Exception("Text detector not found. Revise configuration.")

    detector_arguments = {
        'image': image,
        'language': language,
        'pattern': pattern,
        'regexp': regexp,
        'case_sensitive': case_sensitive,
        'min_score': min_score
    }
    detector_arguments.update(kwargs)

    results = {
        "results": detector.detect(**detector_arguments),
        "success": True
    }

    return results


def find_objects(image, icon_name, min_score=0.8, detector='halcon'):
    detectors = Node.find("detectors")

    if detectors is None:
        raise Exception("Node 'detectors' not found. Revise configuration.")

    detector = Node.find_from(detectors, detector)

    if detector is None:
        raise Exception("Icon detector not found. Revise configuration.")

    # Path to icon SHM file.
    icon_path = None

    metadata = None

    # First check if icon name is a valid path.
    if os.path.exists(icon_name):
        icon_path = icon_name
    else:
        # Then check if icon can be found by it's name from icon Nodes.
        icons = Node.find("icons")

        if icons is None:
            raise Exception("Node 'icons' not found. Revise configuration.")

        icon_node = Node.find_from(icons, icon_name)

        if icon_node is not None:
            icon_path = os.path.abspath(icon_node.path)

            if not os.path.exists(icon_path):
                raise Exception("Icon '{}' doesn't exist".format(icon_name))

            metadata = icon_node.load_metadata()
        else:
            raise Exception("Icon node '{}' doesn't exist".format(icon_name))

    assert icon_path is not None

    results = {}
    results["results"] = detector.detect(image=image, icon=icon_path, min_score=min_score, metadata=metadata)
    results["success"] = True

    return results


def calculate_detection_result_coordinates(results, screenshot):
    """
    Calculate detection result coordinates from pixel coordinates.
    The mm coordinates are placed directly in the provided results dict.
    The pixel coordinates of the result dict are modified so that they correspond to uncropped screenshot.
    It is assumed that the screenshot Image object defines a valid transformation from pixel coordinates to mm.
    :param results: Results dict returned by OCR or icon detection. Must have result pixel coordinate keys.
    :param screenshot: Image object which is used to transform pixel coordinates to mm coordinates.
    """

    # Calculate offset in pixels from Image origin to its transform parent origin.
    offset_x, offset_y = screenshot.transform_point(0, 0)
    offset_x *= screenshot.ppmm
    offset_y *= screenshot.ppmm

    for result in results["results"]:
        result["topLeftX"], result["topLeftY"] = screenshot.transform_point(result["topLeftX_px"],
                                                                            result["topLeftY_px"])
        result["bottomRightX"], result["bottomRightY"] = screenshot.transform_point(result["bottomRightX_px"],
                                                                                    result["bottomRightY_px"])
        result["centerX"], result["centerY"] = screenshot.transform_point(result["centerX_px"], result["centerY_px"])

        # Offset result pixel coordinates so that if the Image transform parent is e.g. DUT and the image
        # is cropped screenshot of the DUT, the pixel coordinates are in relation to the uncropped image.
        result["topLeftX_px"] = int(round(result["topLeftX_px"] + offset_x))
        result["topLeftY_px"] = int(round(result["topLeftY_px"] + offset_y))
        result["bottomRightX_px"] = int(round(result["bottomRightX_px"] + offset_x))
        result["bottomRightY_px"] = int(round(result["bottomRightY_px"] + offset_y))
        result["centerX_px"] = int(round(result["centerX_px"] + offset_x))
        result["centerY_px"] = int(round(result["centerY_px"] + offset_y))


def convert_crop_to_pixels(crop_left, crop_upper, crop_right, crop_lower, width, height, ppmm, crop_unit):
    """
    Convert crop parameters to pixel units.
    :param crop_left: Left crop coordinate. If None then 0 is used.
    :param crop_upper: Upper crop coordinate. If None then 0 is used.
    :param crop_right: Right crop coordinate. If None then maximum value is used.
    :param crop_lower: Lower crop coordinate. If None then maximum value is used.
    :param width: Image width in pixels.
    :param height: Image height in pixels.
    :param ppmm: PPMM to convert mm units to pixel units.
    :param crop_unit: Crop unit. One of "per", "pix" or "mm".
    :return: crop_left, crop_upper, crop_right, crop_lower in pixel units.
    """
    if crop_left is None:
        crop_left = 0

    if crop_upper is None:
        crop_upper = 0

    if crop_unit == "per":
        if crop_right is None:
            crop_right = 1.0

        if crop_lower is None:
            crop_lower = 1.0

        crop_left = crop_left * width
        crop_upper = crop_upper * height
        crop_right = crop_right * width
        crop_lower = crop_lower * height
    elif crop_unit == "pix":
        if crop_right is None:
            crop_right = width

        if crop_lower is None:
            crop_lower = height
    elif crop_unit == "mm":
        crop_left = crop_left * ppmm
        crop_upper = crop_upper * ppmm

        if crop_right is None:
            crop_right = width
        else:
            crop_right = crop_right * ppmm


        if crop_lower is None:
            crop_lower = height
        else:
            crop_lower = crop_lower * ppmm
    else:
        raise Exception("Invalid crop unit {}. Valid values are 'mm', 'pix' and 'per'.".format(crop_unit))

    def clamp(min, max, value):
        if min > max:
            raise Exception("Clamp min greater than max.")

        if value < min:
            return min
        if value > max:
            return max
        else:
            return value

    # Limit crop values to image size and convert to int.
    crop_left = clamp(0, width, int(crop_left))
    crop_upper = clamp(0, height, int(crop_upper))
    crop_right = clamp(0, width, int(crop_right))
    crop_lower = clamp(0, height, int(crop_lower))

    if crop_right <= crop_left:
        raise Exception("Crop parameters were incorrect: crop_right must be bigger than crop_left.")

    if crop_lower <= crop_upper:
        raise Exception("Crop parameters were incorrect: crop_lower must be bigger than crop_upper.")

    return crop_left, crop_upper, crop_right, crop_lower