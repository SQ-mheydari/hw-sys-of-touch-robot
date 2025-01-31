import improved_ocr
from tntclient.tnt_client import TnTClient

tnt_client = TnTClient()

img_nparr = improved_ocr.get_nparr_from_image(filename="camera_image.png")

CROP_BOXES = (
    # 0 ----------> X
    # |
    # |
    # Y
    # top_left_x, top_left_y, bottom_right_x, bottom_right_y ( in pixels )
    (164, 526, 450, 634),
    (139, 603, 532, 771),
)
combined_results = []
for coordinates in CROP_BOXES:
    results = improved_ocr.detect_text_cropped(tnt_client=tnt_client, img_nparr=img_nparr, crop_box=coordinates)
    combined_results += results

improved_ocr.show_image(img_nparr, {'results': combined_results}, window_title="All results")

EXPECTED_WORDS = ('word1', 'word2')
found_words, all_found_words, filtered_ocr_results = improved_ocr.filter_results(combined_results, EXPECTED_WORDS)

improved_ocr.show_image(img_nparr, {'results': filtered_ocr_results}, window_title="Filtered results")
