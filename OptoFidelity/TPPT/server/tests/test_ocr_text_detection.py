import logging
import os
import sys

import cv2
import numpy as np
import pytest

from tntserver.Nodes.Node import Node
from tntserver.Nodes.TnT.Detector import Detector
from tntserver.Nodes.TnT.Detectors import Detectors
from tntserver.drivers.detectors import Tesseract
from tntserver.Nodes.TnT.Images import Images
from tntserver.Nodes.TnT.Image import search_text


OCR_ENGINES = ('abbyy', 'tesseract')


@pytest.fixture(scope="session")
def nodes():
    """
    Initiate nodes for unit test
    """
    root = Node("root")
    Node.root = root
    images = Images('images')
    root.add_child(images)
    detectors = Detectors('detectors')
    root.add_child(detectors)
    # create detectors
    try:
        abbyy = Detector(name='abbyy')
        abbyy._init(driver='Abbyy', license='SWED-1000-0003-0684-9595-9238')
        if abbyy.initialized is True:
            detectors.add_child(abbyy)
        else:
            raise RuntimeError("Abbyy initialization failed, OCR engine not available.")
    except Exception as e:
        logging.exception(e)
    # if os.getenv fails then install tesserocr_dependencies
    try:
        tessdata_path = os.getenv('TESSDATA_PREFIX', default=r'C:\Optofidelity\Tesserocr dependencies\tessdata')
        tesseract = Detector(name='tesseract')
        tesseract._init(driver='Tesseract', tessdata_path=tessdata_path)
        # explicitly initialize API, and keep import here in try..except block
        import tesserocr
        with tesserocr.PyTessBaseAPI() as api:
            pass
        detectors.add_child(tesseract)
    except Exception as e:
        logging.exception(e)


def get_np_arr_from_image(filename):
    with open(filename, "rb") as f:
        data = f.read()
    data = cv2.imdecode(np.asarray(bytearray(data), dtype=np.uint8), cv2.IMREAD_COLOR)
    return data


def get_image(ocr_engine, image_filename='ocr_test.png'):
    """
    return image or skip test if ocr_engine isn't available
    """
    engine = Node.find(ocr_engine)
    if engine is None:
        pytest.skip('{} not available'.format(ocr_engine))
    # read image from disk
    images_directory = os.path.join(os.getcwd(), 'tests', 'images')
    img_nparr = get_np_arr_from_image(os.path.join(images_directory, image_filename))
    return img_nparr


@pytest.mark.skipif(sys.platform != 'win32', reason="does not run on anything other than windows")
@pytest.mark.parametrize("ocr_engine", OCR_ENGINES)
def test_text_detection(nodes, ocr_engine):
    """
    Verify that the detection works and expected number of words/paragraphs is returned
    Verify that supplying default parameters yields the same result as skipping them
    """
    img = get_image(ocr_engine=ocr_engine, image_filename='ocr_test.png')
    results = search_text(image=img, detector=ocr_engine)['results']
    assert len(results) == 53
    results_none = search_text(image=img, detector=ocr_engine, language='English', pattern=None,
                               regexp=False, case_sensitive=False, min_score=0.6)['results']
    assert results == results_none
    results_empty = search_text(image=img, detector=ocr_engine, language='English', pattern="",
                               regexp=False, case_sensitive=False, min_score=0.6)['results']
    assert results == results_empty


@pytest.mark.skipif(sys.platform != 'win32', reason="does not run on anything other than windows")
@pytest.mark.parametrize("ocr_engine", OCR_ENGINES)
def test_detecting_single_word(nodes, ocr_engine):
    """
    Verify that single words from the list are also detected
    """
    img = get_image(ocr_engine=ocr_engine, image_filename='ocr_test.png')
    results = search_text(image=img, detector=ocr_engine, pattern='patient')['results']
    assert len(results) == 1
    assert results[0]['text'] == 'patient'
    assert results[0]['score'] == 1.0


@pytest.mark.skipif(sys.platform != 'win32', reason="does not run on anything other than windows")
@pytest.mark.xfail
@pytest.mark.parametrize("ocr_engine", OCR_ENGINES)
def test_detecting_sentence_01(nodes, ocr_engine):
    """
    Verify that sentence can be detected
    """
    img = get_image(ocr_engine=ocr_engine, image_filename='ocr_test.png')
    sentence = 'A patient at'
    results = search_text(image=img, detector=ocr_engine, pattern=sentence, min_score=1.0)['results']
    assert len(results) == 1, 'expected to fail, pattern matching cannot handle this'
    assert results[0]['text'] == sentence


@pytest.mark.skipif(sys.platform != 'win32', reason="does not run on anything other than windows")
@pytest.mark.xfail
@pytest.mark.parametrize("ocr_engine", OCR_ENGINES)
def test_detecting_sentence_02(nodes, ocr_engine):
    """
    Verify that sentence spanning two verses can be detected
    """
    img = get_image(ocr_engine=ocr_engine, image_filename='ocr_test.png')
    sentence = 'for a scan so they'
    results = search_text(image=img, detector=ocr_engine, pattern=sentence, min_score=1.0)['results']
    assert len(results) == 1, 'expected to fail, multiline sentence'
    assert results[0]['text'] == sentence, 'expected to fail, multiline sentence'

