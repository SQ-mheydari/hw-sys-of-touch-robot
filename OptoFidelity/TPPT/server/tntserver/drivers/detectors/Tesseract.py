import difflib
import logging

from enum import Enum

log = logging.getLogger(__name__)
# map language name from Abbyy to Tesseract
LANGUAGE_MAP = {
    'English': 'eng',
}


class MockTesseract:
    def __init__(self):
        pass

    def detect(self, *args, **kwargs):
        log.error("tesserocr isn't available")
        return None

    class OEM(Enum):
        LSTM_ONLY = 0

    class PSM(Enum):
        SPARSE_TEXT_OSD = 0

    class RIL(Enum):
        WORD = 0

try:
    import PIL
    import locale

    # Fix assert error reported in https://github.com/sirfz/tesserocr/issues/165 .
    locale.setlocale(locale.LC_ALL, 'C')

    import tesserocr
    from tesserocr import RIL, PSM, OEM
except ImportError as e:
    log.exception(e)
    tesserocr = MockTesseract()


class Tesseract:
    """
    OCR detector that uses Tesseract.
    Only usable for english
    """
    def __init__(self, **kwargs):
        self.tessdata_path = kwargs.get('tessdata_path', None)

    def detect(self, image, language: str, pattern: str, regexp: bool, case_sensitive: bool, min_score: float,
               oem=tesserocr.OEM.LSTM_ONLY, psm=tesserocr.PSM.SPARSE_TEXT_OSD, **kwargs):
        """
        Find text from image using Tesseract.
        :param image: Image as Numpy array.
        :param language: Language to use.
        :param pattern: Text pattern to search. If None then all text is searched.
        :param regexp: Is the item parameter a regex pattern?
        :param case_sensitive: Is detection case-sensitive?
        :param min_score: Minimum confidence value between search item and ocr item that is accepted as a match. (IGNORED)

        :param oem: OCR engine mode.
        :param psm: Page segmentation mode.
        :return: Returns list of dictionaries. Format:
        [
            dict(
                topLeftX=top_left_x,
                topLeftY=top_left_y,
                bottomRightX=bottom_right_x,
                bottomRightY=bottom_right_y,
                centerX=(top_left_x + bottom_right_x) / 2,
                centerY=(top_left_y + bottom_right_y) / 2,
                text=text,
                score=score,
            ), ...
        ]
        """

        if kwargs:
            log.debug("kwargs ignored in Tesseract: {}".format(kwargs))
        pil2kind = {
            tesserocr.RIL.WORD: 'Word',
            tesserocr.RIL.TEXTLINE: 'Line',
            tesserocr.RIL.PARA: 'Paragraph',
            tesserocr.RIL.BLOCK: 'Block'
        }
        pil_image = PIL.Image.fromarray(image)
        detections = []

        arguments = {
            'lang': LANGUAGE_MAP[language],
            'psm': psm,     # page segmentation mode
            'init': True,   # default option
            'oem': oem      # default option
        }
        if self.tessdata_path is not None:
            arguments['path'] = self.tessdata_path
        with tesserocr.PyTessBaseAPI(**arguments) as api:
            api.SetImage(pil_image)
            api.Recognize()
            for page_iterator_level in (tesserocr.RIL.WORD, tesserocr.RIL.PARA):
                kind = pil2kind[page_iterator_level]
                for word in tesserocr.iterate_level(api.GetIterator(), page_iterator_level):
                    confidence = word.Confidence(page_iterator_level)
                    if word.Empty(page_iterator_level):
                        continue
                    else:
                        text = word.GetUTF8Text(page_iterator_level)
                        top_left_x, top_left_y, bottom_right_x, bottom_right_y = word.BoundingBox(page_iterator_level)
                    # Detections are here for possible reuse of Abbyy's code
                    # if this never happens then it's safe to populate results already here
                    detections.append((kind, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), text, confidence))
        results = []
        for kind, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), text, confidence in detections:
            results.append(
                dict(
                    topLeftX_px=top_left_x,
                    topLeftY_px=top_left_y,
                    bottomRightX_px=bottom_right_x,
                    bottomRightY_px=bottom_right_y,
                    centerX_px=(top_left_x + bottom_right_x) / 2,
                    centerY_px=(top_left_y + bottom_right_y) / 2,
                    text=text,
                    score=confidence/100,
                    kind=kind
                )
            )
        results = Tesseract.filter_results(results, pattern, regexp, case_sensitive, min_score)
        return results

    @staticmethod
    def filter_results(results, pattern: str, regex: str, case_sensitive: bool, min_score: float):
        """
        Filter results based on pattern
        :param results: list of dictionaries containing OCR detections and it's properties
        :param pattern: string to search for or regular expression
        :param regex: is pattern a regular expression, True or False
        :param case_sensitive: is pattern case sensitive, True or False
        :param min_score: 0.0 - 1.0
        :return: filtered results
        """
        if pattern is not None and pattern != "":
            filtered_results = []
            for r in results:
                text = r['text']
                if regex is True:
                    raise NotImplementedError
                else:
                    if case_sensitive is False:
                        text = text.casefold()
                        pattern = pattern.casefold()
                    match_ratio = difflib.SequenceMatcher(a=pattern, b=text).ratio()
                    if match_ratio > min_score:
                        r['score'] = match_ratio
                        filtered_results.append(r)
            return filtered_results
        else:
            return results
