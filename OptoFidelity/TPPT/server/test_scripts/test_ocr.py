import difflib
import logging
import cv2
import numpy as np

import os
import time
try:
    import tesserocr
except ImportError as e:
    print("tesserocr not available")
from tntserver.drivers.detectors.Tesseract import Tesseract
from tntserver.drivers.detectors.Abbyy import Abbyy
from tntserver.Nodes.TnT.Image import Image
from tntserver.Nodes.TnT.Images import Images

tesseract = Tesseract(tessdata_path=r'C:\Users\lwalac\Documents\repositories\tessdata')
abbyy = Abbyy(license='SWED-1000-0003-0684-9595-9238')
tnt_images = Images(name='images')


log = logging.getLogger(__name__)


def setup_logging():
    fmt = '%(asctime)s %(levelname)7s: %(threadName)10s %(name)10s -> %(funcName)20s %(lineno)5d - %(message)s'
    logging.basicConfig(level=logging.NOTSET,
                        format=fmt)


def get_nparr_from_image(filename):
    with open(filename, "rb") as f:
        data = f.read()
    data = cv2.imdecode(np.asarray(bytearray(data), dtype=np.uint8), cv2.IMREAD_COLOR)
    return data


def check_filename(filename_or_path):
    """
    :param filename_or_path: filename or path
    :return: True or False depending on filtering criteria
    """
    extension = filename_or_path.split(os.path.extsep)[-1]
    if extension in ['jpg', 'png'] and 'plot' not in filename_or_path:
        return True
    return False


def get_wordlist_from_results(results):
    """
    :param results: OCR detection results as returned by tnt-server
    :return: list of detected words
    """
    wordlist = []
    for d in results['ocr_results']:
        word = d['text']
        if word is not None:
            wordlist.append(word)
    return wordlist


def process(image_path, engine, display_image=False, pre_process=True, kwargs={}):
    """

    :param image_path: path to image
    :param engine: OCR engine object
    :param display_image: True of False, show image for debugging purposes
    :param pre_process: True or False
    :param kwargs: passed to engine.detect method
    :return: Dictionary with original image, parameters and OCR results
    """
    engine_name = engine.__class__.__name__
    parameters = {
        'engine_name': engine_name,
        'display_image': display_image,
        'pre_process': pre_process
    }
    parameters.update(kwargs)
    # print('Using engine {}'.format(engine_name))
    t0 = time.time()
    tnt_img = create_tnt_image(name=1, image_path=image_path)
    if pre_process:
        processed_image = process_image_for_ocr(tnt_img)
    else:
        processed_image = tnt_img
    img_nparr = processed_image.data
    ocr_results = engine.detect(image=img_nparr, **kwargs)
    processing_time = time.time() - t0
    # print('{} {:.2f}'.format(image_path, processing_time))
    # print('\t{}'.format(out))
    # print('\t{}'.format(get_wordlist_from_results(out)))

    if pre_process:
        # convert to rgb
        img_with_overlayed_results = cv2.cvtColor(tnt_img.data, cv2.COLOR_GRAY2RGB)
        img_with_overlayed_results = draw_results_over_image(img_with_overlayed_results, ocr_results)
    else:
        img_with_overlayed_results = draw_results_over_image(processed_image, ocr_results)
    if display_image:
        show_image(img_with_overlayed_results, ocr_results)
    return {
        'original_image': tnt_img.data,
        'processed_image': processed_image,
        'img_with_overlayed_results': img_with_overlayed_results,
        'ocr_results': ocr_results,
        'parameters': parameters,
        'processing_time': processing_time
    }


def draw_results_over_image(in_image, results):
    if type(in_image) is Image:
        image = in_image.data
    else:
        image = in_image
    for d in results:
        image = cv2.rectangle(image, (int(d['topLeftX_px']), int(d['topLeftY_px'])), (int(d['bottomRightX_px']), int(d['bottomRightY_px'])), (255, 0, 0))
        image = cv2.putText(image, d['text'], (int(d['centerX_px']), int(d['centerY_px'])), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 3)
    return image


def show_image(in_image, ocr_results):
    if type(in_image) is Image:
        image = in_image.data
    else:
        image = in_image
    if ocr_results is not None:
        for d in ocr_results:
            image = cv2.rectangle(image, (int(d['topLeftX']), int(d['topLeftY'])), (int(d['bottomRightX']), int(d['bottomRightY'])), (255, 0, 0))
            image = cv2.putText(image, d['text'], (int(d['centerX']), int(d['centerY'])), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255))
    cv2.namedWindow("", cv2.WINDOW_NORMAL)
    cv2.imshow("", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def create_tnt_image(name, image_path, data=None):
    tnt_img = Image(name=name)
    tnt_img.parent = tnt_images
    if data is None:
        data = get_nparr_from_image(filename=image_path)
    tnt_img.set_data(data=data)
    return tnt_img


def save_image(in_image, path):
    if type(in_image) is Image:
        image = in_image.data
    else:
        image = in_image
    cv2.imwrite(path, image)


def write_text(in_image, text):
    """
    :param in_image: Image or np.array
    :param text: text to be written to the center of the image
    :return: image with added text
    """
    if type(in_image) is Image:
        in_image.set_data(
            cv2.putText(in_image.data, text, (int(in_image.center_x), int(in_image.center_y)), cv2.FONT_HERSHEY_PLAIN,
                        2,
                        (0, 0, 255), 3))
    else:
        in_image = cv2.putText(in_image, text, (int(np.size(in_image, 1)/2), int(np.size(in_image, 0)/2)), cv2.FONT_HERSHEY_PLAIN,
                        2,
                        (0, 0, 255), 3)
    return in_image


def get_optimal_channel(tnt_image):
    """Get optimal color channel to use for OCR when a single channel is needed."""
    color = ('b', 'g', 'r')
    bg2fg_ratios = []
    for index, column in enumerate(color):
        hist = cv2.calcHist([tnt_image.data], [index], None, [256], [0, 256])
        bg = np.sum(hist[0:128])
        fg = np.sum(hist[128:256])
        try:
            # this line was causing: "RuntimeWarning: divide by zero encountered in float_scalars"
            r = bg / fg
        except ZeroDivisionError:
            r = bg
        bg2fg_ratios.append(r)
    return np.argmax(bg2fg_ratios)


def process_image_for_ocr(tnt_image):
    """Processes the image to make it easier to read for OCR algorithms."""
    image = tnt_image.data
    if len(np.shape(image)) > 2:
        channel = get_optimal_channel(tnt_image)
        gray_im = image[:, :, channel]
        log.debug("channel: {}".format(str(channel)))
        image = gray_im
    log.debug(np.mean(image))
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
    tnt_image.data = masked_img
    return tnt_image


class Statistics:
    """
    Object holding some statistics regarding detected words from set of images
    """
    def __init__(self):
        self.customer_wordlist = ('Settings', 'January', 'Favourite', 'Phone', 'Utilities')
        self.data_set_names = ('lstm', 't_lstm', 'abbyy')
        self.data = {}
        self.close_matches = {}
        self.image_count = 0
        for n in self.data_set_names:
            self.data[n] = {w: 0 for w in self.customer_wordlist}
            self.close_matches[n] = {w: 0 for w in self.customer_wordlist}

    def update_word_count(self, data_set_name, word):
        if word in self.customer_wordlist:
            self.data[data_set_name][word] += 1
        else:
            for cw in self.customer_wordlist:
                close_matches = difflib.get_close_matches(word, possibilities=(cw,))
                if len(close_matches) > 0:
                    self.close_matches[data_set_name][cw] += 1

    def update_image_count(self):
        self.image_count += 1

    def print_statistics(self):
        for dsn in self.data_set_names:
            print("\t\t{}".format(dsn))
            out_str = ""
            for w in self.customer_wordlist:
                if self.data[dsn][w] > 0 or self.close_matches[dsn][w] > 0:
                    ratio = self.data[dsn][w] / self.image_count * 100
                    cm_ratio = self.close_matches[dsn][w] / self.image_count * 100
                    combined_ratio = ratio + cm_ratio
                    out_str += "\t\t\t{}: {:.2f}% {:.2f}%".format(w, ratio, combined_ratio)
            print(out_str)


def update_statistics(results: list, statistics: None):
    if statistics is None:
        statistics = Statistics()
    statistics.update_image_count()
    for name, result in results:
        wordlist = get_wordlist_from_results(result)
        for w in wordlist:
            statistics.update_word_count(name, w)
    return statistics


if __name__ == '__main__':
    """
    Run OCR engine on set of images from directory, gather statistics and write debug images
    to output_directory. Prints some statistics.
    """
    # setup_logging()
    # directory = r'C:\Users\lwalac\Desktop\tesseract\test_images\hud'
    directory = r'C:\Users\lwalac\Desktop\tesseract\test_images\iphone'
    directory = r'C:\Users\lwalac\Desktop\tesseract\OCR test images'
    # output_directory = r'C:\Users\lwalac\Desktop\tesseract\comparison\hud'
    output_directory = r'C:\Users\lwalac\Desktop\tesseract\comparison\ocr_test_images_processed'
    processing_args = {
        'display_image': False,
        'pre_process': False
    }
    statistics = Statistics()
    for dirpath, dirnames, filenames in os.walk(directory):
        for name in filenames:
            if check_filename(name):
                path = os.path.join(dirpath, name)
                lstm_results = process(path, engine=tesseract, **processing_args)
                t_img = lstm_results['img_with_overlayed_results']
                t_img = write_text(t_img, 'LSTM')
                kwargs = {
                    'oem': tesserocr.OEM.TESSERACT_LSTM_COMBINED
                }
                t_lstm_results = process(path, engine=tesseract, kwargs=kwargs, **processing_args)
                tc_img = t_lstm_results['img_with_overlayed_results']
                tc_img = write_text(tc_img, 'TESSERACT_LSTM_COMBINED')
                abbyy_results = process(path, engine=abbyy, **processing_args)
                a_img = abbyy_results['img_with_overlayed_results']
                a_img = write_text(a_img, 'ABBY')

                out_img = cv2.hconcat((t_img, tc_img))
                # out_img = cv2.hconcat((t_img, a_img))
                out_img = cv2.hconcat((out_img, a_img))
                # show_image("", out_img, None)

                n, ext = os.path.splitext(name)
                out_filename = '{}{}{}'.format(n, '_comparison', ext)
                out_path = os.path.join(output_directory, out_filename)
                save_image(out_img, out_path)
                update_statistics((
                    ('lstm', lstm_results),
                    ('t_lstm', t_lstm_results),
                    ('abbyy', abbyy_results),
                ), statistics)
                print(abbyy_results)
                print(t_lstm_results)
                print(lstm_results)
    print("\tpre_process: {}".format(processing_args['pre_process']))
    statistics.print_statistics()
