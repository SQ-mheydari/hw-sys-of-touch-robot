from threading import Lock
import os
import logging
import difflib
import re
import json
import cv2
import sys
from tempfile import NamedTemporaryFile

log = logging.getLogger(__name__)

# Try to import pyfre. It can fail if path to FREngine.dll is not setup correctly.
try:
    import pyfre
except (ImportError, SystemError):
    class pyfre:
        def initialize_engine(self, *args, **kwargs):
            pass

        def process_image(self, *args, **kwargs):
            return []

    # Install Abbyy FineReader Engine (FRE) using instructions https://wiki.optofidelity.com/display/TNT/ABBYY+-+FineReader+Engine
    # It has the runtime binaries for performing OCR. Note: Terms Abbyy and FRE are used interchangeably in this file.
    log.warning('pyfre not available - using stub implementation.')


class Abbyy:
    """
    OCR detector that uses ABBYY.
    """
    img_path = Lock()

    # Typical ABBYY paths. Key is (bitness, version).
    ABBYY_PATHS = {
        ("32", "10"): r'C:\Program Files (x86)\ABBYY SDK\10\FineReader Engine\Bin',
        ("32", "12"): r'C:\Program Files (x86)\ABBYY SDK\12\FineReader Engine\Bin',
        ("64", "12"): r'C:\Program Files\ABBYY SDK\12\FineReader Engine\Bin64',
    }

    def __init__(self, license, pyfre_driver=None, version=10, **kwargs):
        """
        Initialize ABBYY FRE driver.
        :param license: License key for ABBYY FRE.
        :param pyfre_driver: Pyfre driver to use. If None then Pyfre for ABBYY is used. Useful for testing Abbyy class.
        :param version: ABBYY backend version. Can be 10 or 12.
        """

        # Version must be string.
        version = str(version)

        self.pyfre = pyfre if pyfre_driver is None else pyfre_driver
        self.initialized = None
        self._ensure_fre_on_path(version)
        try:
            log.info("Initializing OCR engine with license: {}".format(license))
            self.pyfre.initialize_engine(license, version=version)
            self.initialized = True
        except SystemError as e:
            if hasattr(e, '__context__'):
                e = e.__context__
            log.error('Could not initialize FineReader Engine: {}'.format(e))
            self.initialized = False

    def _ensure_fre_on_path(self, version):
        """
        Try to make sure ABBYY FRE is in path.
        :param version: ABBYY FRE backend version.
        """
        bitness = "64" if sys.maxsize > 2**32 else "32"

        abbyy_path = Abbyy.ABBYY_PATHS.get((bitness, version), None)

        if abbyy_path is not None:

            current_path = os.environ['PATH']

            if abbyy_path not in current_path:
                log.debug("Adding ABBYY location '{}' to path.".format(abbyy_path))

                os.environ["PATH"] = current_path + os.pathsep + abbyy_path

        if "ABBYY" not in os.environ['PATH']:
            log.warning("ABBYY not found in path. OCR will most likely not work.")

    def detect(self, image, language: str, pattern, regexp: bool,
               case_sensitive: bool, min_score: float, **kwargs):
        """
        Find text from image using ABBYY.
        :param image: Image as Numpy array.
        :param language: Language to use.
        :param pattern: Text pattern to search. If None then all text is searched.
        :param regexp: Is the item parameter a regex pattern?
        :param case_sensitive: Is detection case-sensitive?
        :param min_score: Minimum confidence value between search item and ocr item that is accepted as a match.

        More on min_score: Value from 0.0 - 1.0.
        0.0 means that everything is accepted, 1.0 means that match is exact.
        From difflib: "As a rule of thumb, a ratio() value over 0.6 means the sequences are close matches".
        If isRegex is True, this value has no effect and returned
        match will have 1.0 confidence.

        Returns a list of dictionaries. Format:

        [
            {
                    topLeftX_px,
                    topLeftY_px,
                    bottomRightX_px,
                    bottomRightY_px,
                    centerX_px,
                    centerY_px,
                    text,
                    score,
                    kind
            },
            ...
        ]
        """
        if kwargs:
            log.debug("kwargs ignored in Abbyy: {}".format(kwargs))
        words = self._process_image(image, language)

        log.info("Abbyy results:{}".format(str(words).encode("utf-8")))

        results = []

        # bboxes has items (tl, br, text, kind).
        bboxes = self._parse_bounding_boxes(words)

        log.info("Bboxes: {}".format(str(bboxes).encode("utf-8")))

        # If no pattern is given, use all results returned by ABBYY as they are.
        # In both cases create items list where each item has form (tl, br, text, confidence, kind)
        if pattern is None or pattern == "":
            items = []

            # Add confidence value to items.
            for box in bboxes:
                items.append((box[0], box[1], box[2], 1.0, box[3]))

            log.info("Items: {}".format(str(items).encode("utf-8")))
        else:
            # items has items (tl, br, text, confidence).
            items = self._filter_from_results(
                bboxes,
                pattern,
                is_regex=regexp,
                min_confidence=min_score,
                case_sensitive=case_sensitive
            )

            # Add kind attribute to each item. It was removed by _filter_from_results() so need to add something.
            for item in items:
                item.append("Word")

            log.info("Items: {}".format(str(items).encode("utf-8")))

            items = self._sort(items)

            log.info("Sorted: {}".format(str(items).encode("utf-8")))

        for bbox in items:
            top_left_x = bbox[0][0]
            top_left_y = bbox[0][1]
            bottom_right_x = bbox[1][0]
            bottom_right_y = bbox[1][1]
            text = bbox[2]
            score = bbox[3]
            kind = bbox[4]

            results.append(
                dict(
                    topLeftX_px=top_left_x,
                    topLeftY_px=top_left_y,
                    bottomRightX_px=bottom_right_x,
                    bottomRightY_px=bottom_right_y,
                    centerX_px=(top_left_x + bottom_right_x) / 2,
                    centerY_px=(top_left_y + bottom_right_y) / 2,
                    text=text,
                    score=score,
                    kind=kind
                )
            )

        log.info("Results: {}".format(json.dumps(results).encode("utf-8")))

        return results

    def _process_image(self, image, language: str = 'English'):
        words = []

        with self.img_path:
            # Using NamedTemporaryFile to ensure that the temporary file is saved in a write-allowed location
            with NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                cv2.imwrite(temp_file.name, image)
                file_path = temp_file.name

            # Additional dictionary is used in one specific project, if it is missing it's okay
            dictionary_folder_path = os.path.join('data', 'ocr_dictionary')
            additional_arguments = {}

            additional_dictionary_path = dictionary_folder_path + '\\additionalDictionary.ame'

            if os.path.isfile(additional_dictionary_path):
                additional_arguments['additional_dictionary'] = additional_dictionary_path

            # Need to reopen the file due to Windows file handling, see discussion at https://bugs.python.org/issue14243
            with open(file_path, 'rb') as temp_file:
                try:
                    words = self.pyfre.process_image(temp_file.name, language, **additional_arguments)
                except Exception as e:
                    log.warning("error in ocr: {}".format(e))

            os.remove(file_path)

        return words

    def _parse_bounding_boxes(self, results):
        """
            Parses bounding boxes from OCR librarys format.

            Returns a list of bounding boxes:

            [
                [(topLeftX, topLeftY), (bottomRightX, bottomRightY), text, kind],
                ...
            ]

            First two are the bounding box coordinates, and text is the
            identification of the box.
        """
        bounding_boxes = []

        for kind, bbox, text in results:
            bounding_boxes.append([(bbox[0], bbox[1]), (bbox[2], bbox[3]), text, kind])

        return bounding_boxes

    def _filter_from_results(self, bounding_boxes, pattern, is_regex=False,
                             min_confidence=1.0, case_sensitive=True):
        """
            Filters bounding boxes with given text pattern and parameters.
        """

        if bounding_boxes is None:
            return None

        if case_sensitive:
            item = pattern
        else:
            item = pattern.casefold()

        if is_regex:
            regex = re.compile(item)

        found_from_text_pattern = False
        found_bounding_boxes = []

        # this looks for a single word match
        for top_left, bottom_right, box_text, kind in bounding_boxes:

            if kind.lower() == 'word' and box_text.strip():

                original_box_text = box_text

                if not case_sensitive:
                    box_text = box_text.casefold()

                confidence = difflib.SequenceMatcher(None, item, box_text).ratio()

                if is_regex and re.match(regex, box_text) is not None or \
                   confidence >= min_confidence:

                    found_from_text_pattern = True
                    if is_regex:
                        confidence = 1.0

                    found_bounding_boxes.append([top_left, bottom_right,
                                                 original_box_text, confidence])

        # if match not found from single words,
        # assume that more complex multiword regex pattern/multiple words pattern is used
        # Paragraph contains single line and always multiple words
        if not found_from_text_pattern:
            for top_left, bottom_right, box_text, type in bounding_boxes:

                if type.lower() == "paragraph":

                    paragraph = [top_left, bottom_right, box_text, type]

                    if not case_sensitive:
                        box_text = box_text.casefold()

                    # use re.search to find from whole line, not only from the beginning
                    if is_regex:
                        match = regex.search(box_text)
                        if match:

                            box = self._rebox_matched_paragraph(
                                match.group(0).split(' '),
                                bounding_boxes,
                                1.0,
                                paragraph,
                                case_sensitive
                            )

                            if box != None and len(box) != 0:
                                # sequential match, save
                                found_bounding_boxes.append(box)

                    # if not regex, use simple substr matching
                    else:
                        if self._check_substr(box_text, item):

                            box = self._rebox_matched_paragraph(
                                pattern.split(' '),
                                bounding_boxes,
                                1.0,
                                paragraph,
                                case_sensitive
                            )

                            if box != None and len(box) != 0:
                                found_bounding_boxes.append(box)

        return found_bounding_boxes

    def _rebox_matched_paragraph(self, matched_words, bounding_boxes, confidence, fit_to_box, case_sensitive):
        """ If a match is found from paragraph this function transforms
            the bounding box of the original paragraph to contain only words which
            are in matched_words.
            matched_words: is a list of matched word i.e. ['kissa', 'koira']
            bounding_boxes: contains all the found items
            confidence: confidence value
            fit_to_box: the box of the paragraph (used to check that a word is inside it)
        """

        if len(matched_words) < 1:
            return None

        boxes = []
        real_words = []
        paragraph_box = self._expand_bounding_box(fit_to_box, 0.05)

        # find the corresponding boxes
        for word in matched_words:
            for box in bounding_boxes:
                word_in_box = box[2]
                if not case_sensitive:
                    word_in_box = box[2].casefold()
                    word = word.casefold()
                # check that the box type is Word and it fits inside the paragraph
                if box[3].lower() == "word" and self._match_inside(paragraph_box, box):
                    # match partial words too
                    if self._check_substr(word_in_box, word):
                        boxes.append(box)
                        real_words.append(box[2])
                        break
                # If search string is "", add entire paragraph as well
                elif box[3].lower() == "paragraph" and self._match_inside(paragraph_box, box) and word == "":
                    boxes.append(box)
                    real_words.append(box[2])
                    break

        # if words were found, combine the bounding boxes
        new_box = []
        if len(boxes) == len(matched_words):
            # make the first word topleft corner as the topleft property
            # and last word bottom right as the bottom right property of the new box
            new_box = [boxes[0][0], boxes[len(boxes) - 1][1],
                       ' '.join(real_words), confidence]

        return new_box

    def _expand_bounding_box(self, box, expand_by=0.01):
        """ Expands bounding box by a selected percentage so partially detected
            string can be matched inside the expanded box and removed if
            necessary. Returns given box with expanded coordinates. """

        new_box = []

        top_left = (int(box[0][0] * (1.00 - expand_by)),
                    int(box[0][1] * (1.00 - expand_by)))
        right_bottom = (int(box[1][0] * (1.00 + expand_by)),
                        int(box[1][1] * (1.00 + expand_by)))

        new_box.append(top_left)
        new_box.append(right_bottom)
        new_box.append(box[2])
        new_box.append(box[3])

        return new_box

    def _match_inside(self, A, B):
        """ Checks if the box B fits inside box A. Returns true if fits. """

        if (A[0][0] < B[0][0] and A[0][1] < B[0][1] and A[1][0] > B[1][0] and A[1][1] > B[1][1]):
            return True
        return False

    def _check_substr(self, full, sub):
        """ Check if sub is a substr of full. """

        if sub in full:
            return True
        return False

    def _sort(self, results):
        """ Sorts the results from top left row by row to the bottom. """

        # Using average line height, calculate threshold value that
        # is used to determine if the words are on the same row
        line_heights = []

        for result in results:
            line_heights.append(abs(result[0][1] - result[1][1]))

        if len(line_heights) == 0:
            return results

        row_thresh = (sum(line_heights) / len(line_heights)) / 2.0

        # Sort list by y-coordinate
        sorted_list = sorted(results, key=lambda k: (k[0][1] + k[1][1]) / 2.0)
        separated_by_row = []
        row = []

        for i in range(0, len(sorted_list) - 1):
            row.append(sorted_list[i])

            # Get y coordinates of the current word and the next word
            current_y = (sorted_list[i][0][1] + sorted_list[i][1][1]) / 2.0
            next_y = (sorted_list[i + 1][0][1] + sorted_list[i + 1][1][1]) / 2.0
            if abs(current_y - next_y) > row_thresh:
                separated_by_row.append(row)
                row = []  # new row starts
        row.append(sorted_list[len(sorted_list) - 1])
        separated_by_row.append(row)

        # Arrange every row by x-coordinate in ascending order
        sorted_rows = []
        for i in range(len(separated_by_row)):
            sorted_rows.append(sorted(separated_by_row[i], key=lambda k: k[0][0]))

        flat_results = [x for sublist in sorted_rows for x in sublist]
        return flat_results
