"""
requirements
    - pip install python-opencv numpy Pillow tntclient
    - TnT Server has to be up and running and both Abbyy and Tesseract OCR engines have to be configured

NOTE: When SHOW_IMAGES are used then press any letter to close the window.
      If you close the window in other way the script will stop responding
"""

import difflib
import logging
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

SHOW_IMAGES = {
    'original': False,
    'pre_processed': False,
    'debug': False  # found text overlay on original image
}


def setup_logging():
    fmt = '%(asctime)s %(levelname)7s: %(threadName)10s %(name)10s -> %(funcName)20s %(lineno)5d - %(message)s'
    logging.basicConfig(level=logging.NOTSET,
                        format=fmt)


def get_nparr_from_image(filename):
    with open(filename, "rb") as f:
        data = f.read()
    data = cv2.imdecode(np.asarray(bytearray(data), dtype=np.uint8), cv2.IMREAD_COLOR)
    return data


def get_nparr_from_camera(tnt_client, camera_name='Camera1'):
    cam = tnt_client.camera(camera_name)
    data = cam.take_still(filetype='bytes', undistorted=True)
    img_nparr = convert_bytes2nparr(data)   # convert raw data to numpy array
    return img_nparr


def get_nparr_from_server(tnt_client, image_name):
    img = tnt_client.image(image_name)
    png_bytes = img.png()
    img_nparr = cv2.imdecode(np.asarray(bytearray(png_bytes), dtype=np.uint8), cv2.IMREAD_COLOR)
    return img_nparr


def get_nparr_from_dut(tnt_client, dut_name, **kwargs):
    dut = tnt_client.dut(dut_name)
    # possible parameters for dut.screenshot with their default values
    # camera_id='Camera1', crop_left=None, crop_upper=None, crop_right=None, crop_lower=None,
    # crop_unit=None (per/mm/pix), exposure=None, gain=None, offset_x=0, offset_y=0
    image_name = dut.screenshot(**kwargs)
    img_nparr = get_nparr_from_server(tnt_client, image_name)
    return img_nparr


def draw_results_over_image(image, results):
    img_copy = image.copy()
    for d in results:
        img_copy = cv2.rectangle(img_copy, (int(d['topLeftX']), int(d['topLeftY'])), (int(d['bottomRightX']), int(d['bottomRightY'])), (255, 0, 0))
        img_copy = cv2.putText(img_copy, d['text'], (int(d['centerX']), int(d['centerY'])), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 3)


def show_image(image, ocr_results=None, window_title=""):
    img_copy = image.copy()
    if ocr_results is not None:
        for d in ocr_results['results']:
            img_copy = cv2.rectangle(img_copy, (int(d['topLeftX_px']), int(d['topLeftY_px'])),
                                  (int(d['bottomRightX_px']), int(d['bottomRightY_px'])), (255, 0, 0))
            img_copy = write_text(img_copy, d['text'], (int(d['centerX_px']), int(d['centerY_px'])))
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    cv2.imshow(window_title, img_copy)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def save_image(image, path):
    cv2.imwrite(path, image)


def write_text(image: np.array, text: str, pos: tuple) -> np.array:
    """
    :param image: image as np.array
    :param text: text to be written to the center of the image
    :return: image with added text
    """
    image = cv2.putText(image, text, (int(pos[0]), int(pos[1])), cv2.FONT_HERSHEY_PLAIN,
                        2,
                        (0, 0, 255), 3)
    return image


def get_optimal_channel(image: np.array) -> int:
    """Get optimal color channel to use for OCR when a single channel is needed."""
    color = ('b', 'g', 'r')
    bg2fg_ratios = []
    for index, column in enumerate(color):
        hist = cv2.calcHist([image], [index], None, [256], [0, 256])
        bg = np.sum(hist[0:128])
        fg = np.sum(hist[128:256])
        try:
            # this line was causing: "RuntimeWarning: divide by zero encountered in float_scalars"
            r = bg / fg
        except ZeroDivisionError:
            r = bg
        bg2fg_ratios.append(r)
    channel = np.argmax(bg2fg_ratios)
    return channel


def flip_colors(image: np.array) -> np.array:
    masked_img = cv2.bitwise_not(image)
    return masked_img


def process_image_for_ocr(image: np.array) -> np.array:
    """Processes the image to make it easier to read for OCR algorithms."""
    if len(np.shape(image)) > 2:
        channel = get_optimal_channel(image)
        gray_im = image[:, :, channel]
        log.debug("channel: {}".format(str(channel)))
        image = gray_im
    kernel_sharpen_3 = np.array([[-11, -1, -1, -1, -11],
                                 [-1, 2, 2, 2, -1],
                                 [-1, 2, 127, 2, -1],
                                 [-1, 2, 2, 2, -1],
                                 [-11, -1, -1, -1, -11]]) / 127.0
    work_img = cv2.medianBlur(image, 3)
    # enhance edges
    work_img = cv2.filter2D(work_img, -1, kernel_sharpen_3)
    work_img = cv2.erode(work_img, (1, 1))
    med = np.median(work_img)
    _, threshold2 = cv2.threshold(work_img, med, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(threshold2) < 150:
        threshold2 = cv2.dilate(threshold2, (3, 3))
    else:
        threshold2 = cv2.erode(threshold2, (3, 3))
    masked_img = threshold2
    masked_img = cv2.dilate(masked_img, (7, 7), iterations=2)
    if np.mean(masked_img) < 100:  # if image background is black, inverse the colors
        masked_img = cv2.bitwise_not(masked_img)
    return masked_img


def convert_bytes2nparr(data: bytes) -> np.array:
    w = int.from_bytes(data[0:4], byteorder="big")
    h = int.from_bytes(data[4:8], byteorder="big")
    d = int.from_bytes(data[8:12], byteorder="big")
    img_nparr = np.frombuffer(data[12:], dtype=np.uint8).reshape((h, w, d))
    return img_nparr


def convert_nparr2png(nparr: np.array) -> bytes:
    """
    convert image to PNG
    """
    pil_img = Image.fromarray(nparr)
    bytes_io = BytesIO()
    pil_img.save(bytes_io, format='png')
    png_bytes = bytes_io.getvalue()
    return png_bytes


def crop_image(img, crop_box):
    """
    return cropped image
    :param img: image to be cropped
    :param args: top_left_x, top_left_y, bottom_right_x, bottom_right_y
    :return: cropped image
    """
    top_left = (crop_box[0], crop_box[1])
    bottom_right = (crop_box[2], crop_box[3])
    cropped_image = img[top_left[1]:bottom_right[1],
                    top_left[0]:bottom_right[0]]
    return cropped_image


def modify_results_for_full_image(results, crop_box):
    """
    Convert results from cropped image so that bounding box will have coordinates from original image
    """
    for result in results:
        result['centerX_px'] += crop_box[0]
        result['centerY_px'] += crop_box[1]
        result['topLeftX_px'] += crop_box[0]
        result['topLeftY_px'] += crop_box[1]
        result['bottomRightX_px'] += crop_box[0]
        result['bottomRightY_px'] += crop_box[1]
    return results


def detect_text_cropped(tnt_client, img_nparr, crop_box):
    original_image = img_nparr
    cropped_image = crop_image(original_image, crop_box)
    combined_results = detect_text_improved(tnt_client, cropped_image)
    results = modify_results_for_full_image(combined_results, crop_box)
    return results


def detect_text_improved(tnt_client, img_nparr):
    img_nparr_processed = flip_colors(img_nparr)
    # convert to png
    png_bytes = convert_nparr2png(img_nparr)
    png_bytes_processed = convert_nparr2png(img_nparr_processed)
    # send image to server
    img_processed = tnt_client.add_image('ocr_processed')
    img_processed.set_png(png_bytes_processed)
    img = tnt_client.add_image('ocr')
    img.set_png(png_bytes)
    # perform OCR on the image using tesseract
    ocr_results_processed = img_processed.search_text(detector='tesseract', pattern=None)
    ocr_results = img.search_text(detector='tesseract', pattern=None)
    ocr_results_processed_abbyy = img_processed.search_text(detector='abbyy', pattern='', case_sensitive=False, regexp=False)
    ocr_results_abbyy = img.search_text(detector='abbyy', pattern='', case_sensitive=False, regexp=False)
    combined_results = ocr_results['results'] + ocr_results_processed['results'] + ocr_results_processed_abbyy['results'] + ocr_results_abbyy['results']
    return combined_results


def filter_results(combined_results, expected_words):
    found_words = []
    found_words_with_score = []
    filtered_ocr_results = []
    for result in combined_results:
        word = result['text']
        score = result['score']
        kind = result['kind']
        if word in expected_words and word not in found_words and kind == 'Word':
            found_words.append(word)
            found_words_with_score.append((word, score))
            filtered_ocr_results.append(result)
        else:
            # get close matches here
            for cw in expected_words:
                close_matches = difflib.get_close_matches(word, possibilities=(cw,))
                if len(close_matches) > 0 and word not in found_words and kind == 'Word':
                    found_words.append(word)
                    found_words_with_score.append((word, score))
                    filtered_ocr_results.append(result)
    return found_words, found_words_with_score, filtered_ocr_results


def generate_crop_boxes(img_nparr):
    """
    Crop boxes generated here aren't optimal. To shorten execution time it's better to tailor crop boxes
    for specific image(s).
    """
    height, width, _ = img_nparr.shape
    overlap = 0.5
    box_width = round(width/5)
    box_height = round(height/5)
    cropping = {}
    mx = box_width * (1 - overlap)
    my = box_height * (1 - overlap)
    columns = round((width - box_width) / mx) + 1
    rows = round((height - box_height) / my) + 1
    crop_boxes = []
    for ii in range(columns):
        for kk in range(rows):
            x0 = round(ii * mx)
            y0 = round(kk * my)
            x1 = round(x0 + box_width) if round(x0 + box_width) < width else width
            y1 = round(y0 + box_height) if round(y0 + box_height) < height else height
            crop_boxes.append((x0, y0, x1, y1))
            cropping['{}:{}'.format(ii, kk)] = (x0, y0, x1, y1)
    return cropping
