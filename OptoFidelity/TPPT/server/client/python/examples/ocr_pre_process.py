"""
requirements
    pip install python-opencv numpy Pillow tntclient
"""

import logging
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from tntclient.tnt_client import TnTClient

log = logging.getLogger(__name__)


def setup_logging():
    fmt = '%(asctime)s %(levelname)7s: %(threadName)10s %(name)10s -> %(funcName)20s %(lineno)5d - %(message)s'
    logging.basicConfig(level=logging.NOTSET,
                        format=fmt)


def get_np_arr_from_image(filename):
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
    for d in results:
        image = cv2.rectangle(image, (int(d['topLeftX']), int(d['topLeftY'])), (int(d['bottomRightX']), int(d['bottomRightY'])), (255, 0, 0))
        image = cv2.putText(image, d['text'], (int(d['centerX']), int(d['centerY'])), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 3)
    return image


def show_image(image, ocr_results=None):
    if ocr_results is not None:
        for d in ocr_results['results']:
            image = cv2.rectangle(image, (int(d['topLeftX_px']), int(d['topLeftY_px'])),
                                  (int(d['bottomRightX_px']), int(d['bottomRightY_px'])), (255, 0, 0))
            image = write_text(image, d['text'], (int(d['centerX_px']), int(d['centerY_px'])))
    cv2.namedWindow("", cv2.WINDOW_NORMAL)
    cv2.imshow("", image)
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


def main():
    show_images = {
        'original': False,
        'pre_processed': False,
        'debug': True               # found text overlay on original image
    }
    setup_logging()
    tnt_client = TnTClient()
    # take screenshot from the DUT
    img_nparr = get_nparr_from_dut(tnt_client, 'simu_dut', offset_x=-150, offset_y=-150)
    # get raw image using camere OR
    # img_nparr = get_nparr_from_camera(tnt_client=tnt_client)
    # OR use file that you already have
    # filename = r'C:\Temp\ocr_01.png'     # *.png and *.jpg are supported
    # img_nparr = get_np_arr_from_image(filename)
    # show original image
    if show_images['original']:
        show_image(img_nparr)
    img_nparr_processed = process_image_for_ocr(img_nparr)
    # show processed image
    if show_images['pre_processed']:
        show_image(img_nparr_processed)
    # convert to png
    png_bytes = convert_nparr2png(img_nparr_processed)
    # send image to server
    img = tnt_client.add_image('ocr')
    img.set_png(png_bytes)
    # perform OCR on the image using tesseract
    ocr_results = img.search_text(detector='tesseract')
    if show_images['debug']:
        show_image(img_nparr, ocr_results)


if __name__ == '__main__':
    main()
