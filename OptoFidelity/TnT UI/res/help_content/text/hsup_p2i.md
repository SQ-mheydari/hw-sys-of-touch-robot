## Pen to Ink analysis

The analysis measures the latency of drawn ink line on DUT screen with respect to the the moving robot finger. The 
latency is measured by detecting finger tip and ink line tip from each image with an associated time stamp.

The tip of the robot should not reflect light in order to allow the algorithm to work properly. Black matte colored
tip is optimal for pen to ink analysis.

### Basic usage tips

- Before starting a measurement, set the measurement configuration as desired, see the tooltip help for explanation of 
each configuration setting.
- The line drawn on the screen needs to be horizontal. The region of interest (ROI) must be adjusted to be narrow and 
wide in the horizontal direction. You can alternatively reduce the image size to already approximate the ROI (the 
resolution can be for example 480x160px).
- The movement can be either to the right or to the left in the camera view. Make sure to select the proper direction
from the drop-down selection menu.
- The finger must be as vertical as possible in the camera image.
- The contrast of the image is very important in this measurement. One can try to enhance it with binning if the
exposure time cannot be increased. Please note that increasing binning lowers the resolution.
- The ROI should be as tight as possible, see reference image below.

![Pen to ink ROI example.](ui_help_images/p2i_reference_roi.png "Pen to ink ROI example")

### P2I Troubleshooting

Typically the latency measurement result looks like a sawtooth wave centered around some average value, in this case 
around 63 ms, as shown in the example image below. The waveform shape illustrates how the DUT updates the ink line 
position periodically to catch up with the moving finger.

![Pen to ink example result.](ui_help_images/p2i_plot.png "Pen to ink example result")

If your measurement results do not resemble the example image, the following procedure can help to identify problem. 
Perform measurement where one line is drawn from left to right. Check following things:

- Measurement ROI is empty before recording starts. No ink, pen or other objects are inside the measurement ROI when 
recording starts

- Ink line starts and ends outside the measurement ROI

- Fingertip has no reflections and appears uniformly black in the camera image. 

If the above points are not true, check some of the most common error sources listed below.

**1. Wrong objects in measurement area**

- In the measurement ROI only the fingertip (pen) and the drawn line (ink) should be visible. No other moving objects 
should be in the measurement ROI during recording. Browse the frames to check that no extra objects are in measurement 
area. Change the camera position or narrow down the measurement ROI to remove extra objects. Only the drawn line and 
the tip of the finger should be inside. When using a robot the cone shaped part of the finger should not be inside the 
ROI at any point during the measurement.

![Only inkline and fingertip should be visible.](ui_help_images/p2i_wrong_objects.png "Only inkline and fingertip should be visible")

**2. Gap between pen and ink is too narrow**

- To get valid results, certain amount of gap between pen (finger) and ink is required. If there is no visible gap 
between pen and ink or the gap is very narrow then no measurement results are given or results are incorrect. The gap 
should be at least half of the finger width. Draw the line using a higher robot speed to provide larger gap. 

![Too narrow and correct size gap between ink and finge.](ui_help_images/p2i_ink_gap_reference.png "Too narrow and correct size gap between ink and finger")

**3. Contrast between finger and background is not high enough**

- If contrast between finger and background is not high enough, measurement results might be incorrect. Example of a low
contrast image is given below. Make sure that the finger is clearly different from the background in the recorded images. 
Change aperture of the lens to change how objects are seen in image. Bright white screen area, black ink and dark finger 
shape usually work best.

![Image must have sufficient contrast.](ui_help_images/p2i_low_contrast.png "Image must have sufficient contrast")

**4. Noise in measurement results**

- If the camera is shaking during measurement there might be incorrect detections of pen and ink. Robot movements can 
cause shaking of the camera. Decreasing acceleration/deceleration of the robot can reduce camera shaking.

**5. Finger isn't vertical in the image**

- The finger must be as vertical as possible in the image. Adjust the camera positioning such that you are not viewing
the DUT and finger from an angle. You should point the camera perpendicular to the finger movement direction.

![Finger must be vertical in image.](ui_help_images/p2i_angled_finger.png "Finger must be vertical in image")


**6. Finger isn't uniformly black in the image**

- The finger should be uniformly black in the image. Do not use a regular brass finger that reflects the light from the
DUT screen below.

![Finger must be uniformly black.](ui_help_images/p2i_reflecting_finger.png "Finger must be uniformly black")