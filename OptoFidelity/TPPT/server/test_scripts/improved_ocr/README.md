Script to perform multiple detections on single image
# Requirements
- required packages: python-opencv, numpy, Pillow, tntclient
- TnT Server should be running for script to work
# Setup
Install requirements
```
pip install python-opencv numpy Pillow
```
## Optional, if using virtual environment
Create virtual environment and activate
```
python -m venv venv
venv\Scripts\activate.bat
```
Install requirements
```
pip install python-opencv numpy Pillow
```
Install tntclient, ask our support for latest version
```
pip install tntclient-*.whl
```
# Example script
## Required imports and setup
```
import improved_ocr
from tntclient.tnt_client import TnTClient

tnt_client = TnTClient()
```
## Get image for analysis using one of those options
### from file
*.png and *.jpg are supported
```
img_nparr = improved_ocr.get_nparr_from_image(filename="image.png")
```
### from DUT
```
img_nparr = improved_ocr.get_nparr_from_dut(tnt_client=tnt_client, dut_name='dut1')
```
### full frame from camera
```
img_nparr = improved_ocr.get_nparr_from_camera(tnt_client=tnt_client)
```
## Analyse image using one of the following options
### find words from whole image using different engines and combine results
```
combined_results = improved_ocr.detect_text_improved(tnt_client, img_nparr)
```
### find words from parts of the image, very useful for situations where position of the word is known in advance
```
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
```
## Debugging methods
### filter results to contain only expected words
```
# combined_results are from detect_text_improved or detect_text_cropped
EXPECTED_WORDS = ('word1', 'word2')
found_words, all_found_words, filtered_ocr_results = improved_ocr.filter_results(combined_results, EXPECTED_WORDS)
```
### display image with overlayed results (press any key to close the window)
```
improved_ocr.show_image(img_nparr, {'results': combined_results}, window_title="All results")
```
### save image for later analysis
```
improved_ocr.save_image(img_nparr, path='debug_image_01.png')
```
