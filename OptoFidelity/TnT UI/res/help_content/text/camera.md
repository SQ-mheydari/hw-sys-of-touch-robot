The camera to calibrate can be selected from the camera view control panel which is also used to select which camera is currently displayed.

Before the calibrations, make sure that the tip state of the robot is correct. This means that if calibrations
are done without a tip, there should be no tip attached in the tips view. If a sharp tip is used, the length of the tip
should be measured, and the tip should be attached in the tips view.

## Calibrate Camera Focus Height

Camera focus height is the distance from the camera mount flange to the camera focal plane.
This calibration is required before calibrating camera offset and camera distortion.
A change in camera focus height invalidates existing camera distortion calibration. It has no effect on camera
offset calibration in case the camera is well-aligned with the robot z-axis. However, in practise camera offset
should also be recalibrated if focus height changes.

![Focus height calibration.](ui_help_images/focus_calibration.jpg "Focus height calibration.")

Focus height can be adjusted by physically adjusting the camera lens focus ring as shown in the image.
Usually the ring has a small locking knob that needs to be first turned loose. 

There are generally two distinct recommendations for choosing focus height:

1. Maximum DUT positioning accuracy with TPPT tests: Choose as short focus height as possible but longer than
the longest tip. Usually 30 mm is appropriate.
2. Maximum DUT visibility in functional tests: Make sure that focus height is long enough to make the DUT screen
completely visible in the camera image for successful OCR and icon detection.

Press 'Start Focus Height Calibration' and follow the instructions.

## Calibrate Camera Offset

Camera offset calibration measures and calibrates distance between the tool tip and the camera on the camera focal plane.
Camera focus calibration must be done before offset calibration. 

The most common procedure is to use Audit Gauge
that has a moving lit inset that can be used to bring robot tip and camera center to the same world position in
a two-step process.

![Camera offset calibration.](ui_help_images/camera_offset_calib.jpg "Camera offset calibration.")

Camera offset calibration accuracy affects DUT positioning accuracy when camera is used to determine the DUT
corner x and y coordinates. In case camera center position changes due to e.g. lens adjustments, offset calibration
must be performed.

Select calibration method from the dropdown, press 'Start Offset Calibration' and follow the instructions.

## Calibrate Camera Distortion

Camera distortion calibration fixes the distortion errors of the image and calculates 'pixels per millimeter' value
which affects the accuracy of the robot when robot is moved by clicking on the camera image. This has no effect on
DUT positioning accuracy.

Select calibration method from the dropdown, press 'Start Distortion Calibration' and follow the instructions.

## Create Calibration Target

A tool for creating chessboard target to be used in calibrations. Click the button and go through the wizard.
