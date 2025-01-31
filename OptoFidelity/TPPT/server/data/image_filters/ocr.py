import numpy as np
import cv2
import logging

log = logging.getLogger(__name__)


FILTER_VERSION = "1.0"


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


def filter_image(image: np.array, parameters) -> np.array:
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