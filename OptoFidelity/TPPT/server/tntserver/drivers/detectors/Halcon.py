import logging
import math
import os
import numpy as np
import cv2
from multiprocessing import Process, Queue
from concurrent.futures import ProcessPoolExecutor

from PIL import Image as PILImage
from threading import Lock
from optovision.utils.circle_extractor_utils import threshold_image

log = logging.getLogger(__name__)

try:
    import pyhalcon
    import pyhalcon._pyhalcon as halcon
except ImportError as e:
    log.exception(e)
    # Install halcon using instructions https://wiki.optofidelity.com/display/TNT/HALCON+-+how+to+install
    log.warning('pyhalcon not available - using stub implementation')


class ResultObjectStub:
    """
    Describes a found icon.
    """

    def __init__(self):
        self.angle = None
        self.score = None
        self.scale = None
        self.tl = None
        self.br = None
        self.model = None


def extract_foreground(image, blk_size, const):
    """
    Extract the foreground of given image.
    Uses various image manipulation techniques.
    :param image: Source image.
    :param blk_size: blk_size parameter for cv2.adaptiveThreshold().
    :param const: C parameter for cv2.adaptiveThreshold().
    :return: Image that has only the foreground of the input image.
    """
    original_image=image.copy()
    cnt_image = image.copy()

    thresh = threshold_image(image=255 - image, threshold_type="adaptive_mean", blk_size=blk_size, C=const)

    thresh = cv2.erode(thresh, np.ones((3, 3)), 2)
    thresh = cv2.dilate(thresh, np.ones((3, 3)), 2)

    # fit contours
    im3, base_contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
    )

    shape = cnt_image.shape[:2]
    poly_im = np.zeros(shape, dtype=np.uint8)

    for cnt in base_contours:
        cv2.fillPoly(poly_im, pts=[cnt], color=(255, 255, 255))

    output = cv2.bitwise_and(original_image, original_image, mask=poly_im)

    return output


def compute_color_score_template_match(image, template, template_scale=1.0):
    """
    Compute color score between two images.
    Uses template matching which requires that the feature whose color is
    compared has the same size in both images.
    :param image: First image.
    :param template: Second image which is treated as the template (should be smaller than image).
    :param template_scale: Scaling factor for template image to be applied before template matching.
    :return: Score in range [0, 1].
    """

    scaled_template = cv2.resize(template, dsize=None, fx=template_scale, fy=template_scale)

    # Make sure that the image is larger than the template. Otherwise OpenCV may trigger assertion.
    # Image should be 3x the size of the template in both dimensions so that the template can slide across
    # the target icon within the image and thus find optimal template matching.
    # Image is extended with black borders on each side to increase the image size.
    image_height, image_width = image.shape[:2]
    template_height, template_width = scaled_template.shape[:2]

    if template_width > image_width // 3:
        d = template_width * 3 - image_width
        image = cv2.copyMakeBorder(image, 0, 0, math.floor(d / 2), math.ceil(d / 2), cv2.BORDER_CONSTANT, (0, 0, 0))

    if template_height > image_height // 3:
        d = template_height * 3 - image_height
        image = cv2.copyMakeBorder(image, math.floor(d / 2), math.ceil(d / 2), 0, 0, cv2.BORDER_CONSTANT, (0, 0, 0))

    # Perform template matching.
    res = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)

    _, max_val, _, _ = cv2.minMaxLoc(res)

    return max_val


def kmeans_color_quantization(image: np.ndarray, clusters=8, rounds=1):
    """
    Quantize image color content.
    :param image: Image.
    :param clusters: Number of color clusters.
    :param rounds: Number of rounds to use in kmeans algorithm.
    :return: Image with quantized colors.
    """
    h, w = image.shape[:2]
    samples = np.zeros([h*w,3], dtype=np.float32)
    count = 0

    for x in range(h):
        for y in range(w):
            samples[count] = image[x][y]
            count += 1

    compactness, labels, centers = cv2.kmeans(samples,
            clusters,
            None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10000, 0.0001),
            rounds,
            cv2.KMEANS_RANDOM_CENTERS)

    centers = np.uint8(centers)
    res = centers[labels.flatten()]

    return res.reshape((image.shape))


def unique_quantized_colors(image: np.ndarray, num_colors):
    """
    Determine unique quantized color of given image.
    E.g. if there is a red icon on black background, this should return the red and black colors.
    :param image: Image.
    :param num_colors: Number of colors to extract.
    :return: Tuple (unique_colors, color_counts).
    """
    image_quant = kmeans_color_quantization(image, num_colors)

    h, w = image_quant.shape[:2]
    samples = np.zeros([h * w, 3], dtype=np.float32)
    count = 0

    for x in range(h):
        for y in range(w):
            samples[count] = image_quant[x][y]
            count += 1

    unique, counts = np.unique(samples, return_counts=True, axis=0)

    ixs = np.argsort(counts)

    return unique[ixs], counts[ixs]


def compute_color_score_quantized(image, icon_colors, threshold=0.02):
    """
    Compute icon color score based on pre-computed icon colors.
    :param image: Image to compute color score from.
    :param icon_colors: List of colors to compare to image content.
    :param threshold: Comparison threshold in range [0, 1].
    :return: Score in range [0, 1].
    """
    image_colors, counts = unique_quantized_colors(image, num_colors=8)

    num_matches = 0

    threshold *= 255

    for icon_color in icon_colors:
        for image_color in image_colors:
            # Images are in BGR format (opencv default) but stored icon colors are in RGB. Convert to RGB.
            image_color[0], image_color[2] = image_color[2], image_color[0]

            color_diff = np.array(image_color) - np.array(icon_color)

            if abs(color_diff[0]) <= threshold and abs(color_diff[1]) <= threshold and abs(color_diff[2]) <= threshold:
                num_matches += 1

    # With loose threshold one color in icon_colors may match to multiple colors in the image.
    return 1.0 if num_matches >= len(icon_colors) else 0.0


def threshold_color_image(image, threshold=0.0):
    """
    Threshold color image so that values whose color intensity is below threshold
    are clipped to black. Other colors remain unchanged.
    :param image: Image to threshold.
    :param threshold: Threshold as relative value between min and max color intensity.
    :return: Thresholded image.
    """
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    min_value = float(np.min(gray_image))
    max_value = float(np.max(gray_image))

    # Compute threshold from average intensity.
    threshold_value = int(round(min_value + (max_value - min_value) * threshold))

    _, thresholded_gray = cv2.threshold(gray_image, threshold_value, 255, cv2.THRESH_BINARY)

    thresholded_image = cv2.cvtColor(thresholded_gray, cv2.COLOR_GRAY2BGR)

    # Multiply original image by threshold mask. Scale by 1/255 to make the threshold image behave as scale factor.
    result = cv2.multiply(image, thresholded_image, scale=1.0/255)

    return result


def compute_image_bgr_moment_vectors(image):
    """
    Compute image color moment vectors. Each vector has 3 scalar components (one for each color channel).
    Moments are: mean, stdev.
    :param image: Image to oompute moments from.
    :return: mean_vector, stdev_vector.
    """

    mean_bgr = np.mean(image, axis=(0, 1))
    stdev_bgr = np.std(image, axis=(0, 1))

    # Create vector that is normalized unless it is a zero vector.
    # Mean zero vector is black image.
    # Stdev zero vector is constant color image.
    def create_vector(v):
        v_len = np.linalg.norm(v)

        if v_len == 0:
            return np.array([0, 0, 0])

        return v / v_len

    return create_vector(mean_bgr), create_vector(stdev_bgr)


def compute_color_score_moments(image1, image2, multiplier=1.0):
    """
    Compute color score between two images.
    Uses color moments (mean and stdev) to measure color. This algorithm is sensitive to contrast differences.
    :param image1: First image.
    :param image2: Second image.
    :param multiplier: Multiplier for color difference. If > 1.0 then color differences are pronounced in the score.
    :return: Score in [0, 1] where higher is better. compute_color_score(a, a) equals 1 for any image a.
    """

    mean1, stdev1 = compute_image_bgr_moment_vectors(image1)
    mean2, stdev2 = compute_image_bgr_moment_vectors(image2)

    # Compute color difference from Euclidean norms of moment differences.
    difference = np.linalg.norm(mean1 - mean2) + np.linalg.norm(stdev1 - stdev2)

    # Use mapping 1 / (1 + x) to calculate score in range [0, 1]. Zero difference gives score 1.
    score = 1 / (1 + difference * multiplier)

    return score


def compute_color_score_hist(image1, image2, num_bins=10, multiplier=1.0):
    """
    Compute color score between two images.
    Uses histograms to measure color. This algorithm is sensitive to noise and background gradients.
    :param image1: First image.
    :param image2: Second image.
    :param multiplier: Multiplier for color difference. If > 1.0 then color differences are pronounced in the score.
    :return: Score in [0, 1] where higher is better. compute_color_score(a, a) equals 1 for any image a.
    """

    def normalized_histogram(data):
        hist, _ = np.histogram(data, bins=num_bins)

        return hist / sum(hist)

    # Compute histogram for each color channel of the two images.
    h1_b = normalized_histogram(image1[:, :, 0])
    h1_g = normalized_histogram(image1[:, :, 1])
    h1_r = normalized_histogram(image1[:, :, 2])

    h2_b = normalized_histogram(image2[:, :, 0])
    h2_g = normalized_histogram(image2[:, :, 1])
    h2_r = normalized_histogram(image2[:, :, 2])

    # Compute color difference from Euclidean norms of histogram differences of each color channel.
    difference = np.linalg.norm(h1_b - h2_b) + np.linalg.norm(h1_g - h2_g) + np.linalg.norm(h1_r - h2_r)

    # Use mapping 1 / (1 + x) to calculate score in range [0, 1]. Zero difference gives score 1.
    score = 1 / (1 + difference * multiplier)

    return score


def read_icon(icon_name):
    """
    Reads the icon from the system.

    :param icon_name: Icon name as filename including path.
    :return: Icon as pyhalcon.ShapeModel, or None if not found with given name.
    """

    shm = None

    # Check that path exists.
    if os.path.exists(icon_name):
        if not icon_name.lower().endswith(".shm"):
            raise Exception("Path to icon file must have extension '.shm'.")

        shm = pyhalcon.ShapeModel.from_file(icon_name)
    else:
        raise Exception("Icon '{}' doesn't exist.".format(icon_name))

    return shm


def convert_to_halcon_image(image):
    """
    Convert numpy array into Halcon image.

    :param image: Image as numpy array.
    :return: Image as pyhalcon.Image.
    """
    log.debug("Creating Halcon image")

    # convert image from numpy array to PIL and then pyhalcon.Image
    if len(image.shape) == 3:
        pil_image = PILImage.fromarray(image, 'RGB')
    else:
        pil_image = PILImage.fromarray(image, 'L')
    halcon_image = pyhalcon.Image.from_pil(pil_image)

    log.debug("Creating halcon image finished")

    return halcon_image


def get_shape_model_contours(shm, row1=0, column1=0, angle1=0, row2=0, column2=0, angle2=0, sx=1, sy=1, px=0, py=0):
    """
    Get shape model contours with possible transformations
    :param shm: Shape model of which contours we want.
    :param row1: Row coordinate of the original point.
    :param column1: Column coordinate of the original point.
    :param angle1: Angle of the original point.
    :param row2: Row coordinate of the transformed point.
    :param column2: Column coordinate of the transformed point.
    :param angle2: Angle of the transformed point.
    :param sx: Scale factor along the x-axis.
    :param sy: Scale factor along the y-axis.
    :param px: Fixed point of the transformation (x coordinate).
    :param py: Fixed point of the transformation (y coordinate).

    :return: Shape model contours as pyhalcon.Contours
    """

    # Get shape model contours and move them to suitable position save them as png image.
    modelcontours = shm.get_contours(1)

    # Move contours to the center of the image and scale them.
    transformedcontours = modelcontours.get_repositioned_rotated_and_scaled_contours(row1, column1, angle1, row2,
                                                                                     column2, angle2, sx, sy)

    return transformedcontours


def detect_icon(icon, image, min_score, scale_min, scale_max, angle_start, angle_extent):
    """
    Detect icon using Halcon.
    :param icon: Icon file path.
    :param image: Image where to detect icon from.
    :param min_score: Minimum detection score.
    :param scale_min: Minimum icon scale used when creating shape models and detecting icons.
    :param scale_max: Maximum icon scale.
    :param angle_start: Minimum angle in radians.
    :param angle_extent: Maximum angle relative to angle_start in radians.
    :return: Detection results.
    """

    try:
        icon_shm = read_icon(icon)
        detector = pyhalcon.SimpleDetector()
        detector.add_model(icon_shm)

        halcon_image = convert_to_halcon_image(image)

        # Use lower scorelimit than the confidence as Halcon works more reliably this way
        # giving more high score results too
        scorelimit = min(0.5, min_score)

        # The default values of anglestart and angleextent are in degrees even though they should be in radians.
        # Make sure to pass them here in radians!
        objects = detector.find_objects(image=halcon_image, scorelimit=scorelimit, scalemin=scale_min,
                                        scalemax=scale_max, anglestart=angle_start, angleextent=angle_extent)

        return objects
    except halcon.Error as err:
        if err.args[0] == 2041:
            raise Exception("Halcon error {}: {} (Make sure that Halcon license dongle is attached)".format(err.args[0], err.args[1]))
        else:
            raise Exception("Halcon error {}: {}".format(err.args[0], err.args[1]))


def change_background_color(img, old_color, new_color):
    """
    Change image background color from old_color to new_color
    :param img: Image object.
    :param old_color: Color to replace.
    :param new_color: New color.
    :return: Image with replaced color.
    """

    img = img.convert('RGB')
    img_data = np.array(img)

    # replace old color with new color
    img_data[(img_data == old_color).all(axis=-1)] = new_color
    new_img = PILImage.fromarray(img_data, mode='RGB')

    return new_img


def _create_scaled_shape_model(icon_img, shm_path, contour_img_path, queue, scale_min, scale_max,
                               scale_step, angle_start, angle_extent, angle_step, **kwargs):
    """
    Create Halcon's scaled shape model.

    :param icon_img: Icon image as numpy array.
    :param shm_path: Path where the shape model file is written to.
    :param contour_img_path: Path where contour image file is written to. None means it is not written.
    :param queue: Queue object where to put result.
    :param scale_min: Minimum icon scale.
    :param scale_max: Maximum icon scale.
    :param scale_step: Scale step size or "auto".
    :param angle_start: Minimum angle in radians.
    :param angle_extent: Maximum angle relative to angle_start in radians.
    :param angle_step: Angle step size in radians or "auto".
    :param kwargs: Additional Halcon specific parameters for shape model creation.
    """

    try:
        halcon_img = convert_to_halcon_image(icon_img)
        # TODO: There should be more investigation if we should leave the image into color version
        #       but currently do conversion to gray as in pyhalcon.SimpleDetector.create_shm()
        halcon_img = halcon_img.to_gray()

        model_id = halcon.T_create_scaled_shape_model(
            halcon_img.obj,
            kwargs.get('num_levels', 'auto'),
            angle_start,
            angle_extent,
            angle_step,
            scale_min,
            scale_max,
            scale_step,
            kwargs.get('optimization', 'auto'),
            kwargs.get('metric', 'ignore_local_polarity'),
            kwargs.get('contrast', 'auto'),
            kwargs.get('min_contrast', 'auto')
        )

        shm = pyhalcon.ShapeModel(model_id)

        shm.write(shm_path)

        if contour_img_path is not None:
            image_height, image_width = icon_img.shape[:2]

            transformed_contours = get_shape_model_contours(shm, 0, 0, 0, image_height / 2, image_width / 2, 0, 1, 1)

            # Note: width and height arguments here must be -1. Halcon will create a window of appropriate size.
            # If you try to use the image width and height, it will not always work. It seems that Halcon forces internally
            # minimum width and height of 128 which can mess up the aspect ratio.
            img = pyhalcon.image.get_shapemodel_as_pil_image(transformed_contours, -1, -1, 'red')
            img = change_background_color(img, (0, 0, 0), (255, 255, 255))
            img.save(contour_img_path, 'png')

        # None value denotes success.
        queue.put(None)
    except halcon.Error as err:
        if err.args[0] == 2041:
            queue.put("Halcon error {}: {} (Make sure that Halcon license dongle is attached)".format(err.args[0], err.args[1]))
        else:
            queue.put("Halcon error {}: {}".format(err.args[0], err.args[1]))
    except Exception as e:
        queue.put(str(e))


def create_scaled_shape_model(icon_img, shm_path, contour_img_path, timeout, **kwargs):
    """
    Create Halcon's scaled shape model.

    :param icon_img: Icon image as numpy array.
    :param shm_path: Path where the shape model file is written to.
    :param contour_img_path: Path where contour image file is written to. None means it is not written.
    :param timeout: Time in seconds to wait for the result.
    :param kwargs: Additional Halcon specific parameters for shape model creation.
    """
    # Uses queue to pass data from Halcon process to main process.
    queue = Queue()

    # Process creation has roughly 200 ms overhead.
    p = Process(target=_create_scaled_shape_model, args=(icon_img, shm_path, contour_img_path, queue), kwargs=kwargs)
    p.start()
    p.join()

    results = queue.get(block=True, timeout=timeout)

    # If results is string, it is treated as error message from the process.
    if isinstance(results, str):
        raise Exception(results)


class Halcon:
    """
    Halcon based icon detection.
    """

    def __init__(self, color_cmp_method=None, color_cmp_params=None, simulator=False, multiprocessing=True,
                 process_timeout=10.0, scale_min=0.8, scale_max=1.2, scale_step="auto", angle_start=-10.0,
                 angle_extent=20.0, angle_step="auto", **kwargs):
        """
        Initialize Halcon driver.
        :param color_cmp_method: Color comparison method ("template", "histogram" or "moments").
        If None then colors are not compared.
        :param color_cmp_params: Dictionary of parameters for color comparison.
        :param simulator: If True, Halcon is not used but instead detection uses stub implementation.
        :param multiprocessing: If True, run Halcon commands in separate process to avoid crashing the main process
        :param process_timeout: Time in seconds to wait for multiprocessing operations to finish.
        :param scale_min: Minimum icon scale used when creating shape models and detecting icons.
        :param scale_max: Maximum icon scale.
        :param scale_step: Scale step size.
        :param angle_start: Minimum angle in degrees.
        :param angle_extent: Maximum angle relative to angle_start in degrees.
        :param angle_step: Angle step size in degrees.
        in case of severe errors. Useing separate process can cause small overhead to detection.
        """
        self.simulator = simulator
        self.multiprocessing = multiprocessing
        self.pool = None
        self.process_timeout = process_timeout

        if multiprocessing:
            log.debug("Running Halcon in multiprocess mode.")

            # ProcessPoolExecutor handles crash of child process correctly. New process is created after a crash.
            # Use only one process to perform detections.
            self.pool = ProcessPoolExecutor(1)
        else:
            log.debug("Running Halcon in singleprocess mode.")

        self.color_cmp_method = color_cmp_method
        self.color_cmp_params = color_cmp_params if color_cmp_params is not None else {}
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.scale_step = scale_step
        self.angle_start = math.radians(angle_start)
        self.angle_extent = math.radians(angle_extent)
        self.angle_step = math.radians(angle_step) if angle_step != "auto" else angle_step

    def compute_color_score(self, image, icon, scale, metadata=None):
        """
        Compute color score between image and icon (reference image).
        :param image: Image as numpy array.
        :param icon: Icon SHM path. Is is assumed that there is a PNG file with similar path.
        :param scale: Scale factor for icon image.
        :param metadata: Optional metadata of icon.
        :return: Score in range [0, 1].
        """

        if metadata is None:
            metadata = {}

        icon_image_path = os.path.splitext(icon)[0] + ".png"

        icon_image = cv2.imread(icon_image_path)

        threshold = self.color_cmp_params.get("threshold", 0.2)

        if self.color_cmp_params.get("extract_foreground", False):
            blk_size = self.color_cmp_params.get("extract_foreground_blk_size", 33)
            const = self.color_cmp_params.get("extract_foreground_const", 2)

            image = extract_foreground(image, blk_size=blk_size, const=const)
            icon_image = extract_foreground(icon_image, blk_size=blk_size, const=const)

        image = threshold_color_image(image, threshold)
        icon_image = threshold_color_image(icon_image, threshold)

        if self.color_cmp_method == "histogram":
            num_bins = self.color_cmp_params.get("num_bins", 10)
            multiplier = self.color_cmp_params.get("multiplier", 1.0)

            return compute_color_score_hist(image, icon_image, num_bins=num_bins, multiplier=multiplier)
        elif self.color_cmp_method == "moments":
            multiplier = self.color_cmp_params.get("multiplier", 1.0)

            return compute_color_score_moments(image, icon_image, multiplier=multiplier)
        elif self.color_cmp_method == "template":
            return compute_color_score_template_match(image, icon_image, scale)
        elif self.color_cmp_method == "quantized":
            if not metadata.get("colors", None):  # Handle non-existing key and empty list.
                return 1.0  # In this case color detection is not used for the icon so return full score.

            threshold = metadata.get("color_threshold", 0.02)

            return compute_color_score_quantized(image, metadata["colors"], threshold)

        raise Exception("Unrecognized color comparison method '{}'.".format(self.color_cmp_method))

    def detect(self, image, icon, min_score=0.75, metadata=None):
        """
        Detect icon from image using Halcon shape model.
        :param image: Image as Numpy array.
        :param icon: Path to icon model file.
        :param min_score: Score limit for icon detection.
        :param metadata: Metadata for icon.
        :return: List of results.

        Result object is dict:
        [{
                "topLeftX_px": 4.21,
                "topLeftY_px": 2.37,
                "bottomRightX_px": 6.23,
                "bottomRightY_px": 3.54,
                "centerX_px": 5.22,
                "centerY_px": 2.96,
                "shape": "shapeName.shm",
                "score": 0.781,
                "scale": 1.0,
                "angle": 0
            }]
        """
        log.info('Using Halcon icon detector, minimum score {}. Color comparison method: {}.'.format(min_score, self.color_cmp_method))

        log.debug("Finding objects.")

        if self.simulator:
            objects = []

            obj = ResultObjectStub()
            obj.angle = 30
            obj.scale = 0.3
            obj.score = 0.9
            obj.tl = (10, 20)
            obj.br = (300, 400)
            obj.model = 'model_filename'

            objects.append(obj)
        else:
            if self.multiprocessing:
                try:
                    future = self.pool.submit(detect_icon, icon, image, min_score, self.scale_min, self.scale_max,
                                              self.angle_start, self.angle_extent)

                    objects = future.result(timeout=self.process_timeout)
                except Exception as e:
                    log.error("Icon detection failed: {}".format(str(e)))

                    self.pool.shutdown(wait=False)

                    # Recreate the pool in case the process remains in some undefined state.
                    self.pool = ProcessPoolExecutor(1)

                    raise
            else:
                objects = detect_icon(icon, image, min_score, self.scale_min, self.scale_max, self.angle_start,
                                      self.angle_extent)

        log.debug("Finding objects finished: {} icon(s) detected.".format(len(objects)))

        results = []

        for obj in objects:
            score = obj.score

            if self.color_cmp_method is not None:
                cropped_image = image[obj.tl[1]:obj.br[1], obj.tl[0]:obj.br[0], :]
                color_score = self.compute_color_score(cropped_image, icon, obj.scale, metadata)

                # Total score is product of shape model based detection score and color similarity score.
                score = obj.score * color_score

                log.debug("Object score {} is weighted by color score {} to produce total score {}.".
                          format(obj.score, color_score, score))

            # Add result if the score is higher than requested confidence
            if score >= min_score:
                result = dict()
                result['score'] = score
                result['topLeftX_px'] = obj.tl[0]
                result['topLeftY_px'] = obj.tl[1]
                result['bottomRightX_px'] = obj.br[0]
                result['bottomRightY_px'] = obj.br[1]
                result['centerX_px'] = (obj.tl[0] + obj.br[0]) / 2
                result['centerY_px'] = (obj.tl[1] + obj.br[1]) / 2
                result['shape'] = icon
                result['scale'] = obj.scale
                result['angle'] = obj.angle

                results.append(result)

        log.info('Found {} results.'.format(len(results)))

        return results

    def create_scaled_shape_model(self, icon_img, shm_path, contour_img_path=None, **kwargs):
        """
        Create Halcon's scaled shape model.

        :param icon_img: Icon image as numpy array.
        :param shm_path: Path where the shape model file is written to.
        :param contour_img_path: Path where contour image file is written to. None means it is not written.
        :param kwargs: Additional Halcon specific parameters for shape model creation.
        """

        create_scaled_shape_model(icon_img, shm_path, contour_img_path, self.process_timeout, scale_min=self.scale_min,
                                  scale_max=self.scale_max, scale_step=self.scale_step, angle_start=self.angle_start,
                                  angle_extent=self.angle_extent, angle_step=self.angle_step, **kwargs)
