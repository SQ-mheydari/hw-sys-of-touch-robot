## ROI

Enable crop box for marking a region of interest (ROI) from the image.

## Configuration

In this pane one can adjust the configuration parameters. The parameters are updated to the camera
when Set Camera Parameters button is clicked. Please note that the configuration might need to be done
again if camera is moved, dut is moved or the lighting of the laboratory is changed.

## Exposure time

Exposure time of the camera in milliseconds. If display backlight synchronization is enabled,
you should set exposure and other camera parameters such that the resulting frame rate is at least equal to the
display backlight frequency.

## Max frame rate limit

Limit camera framerate to the given maximum value. Value 0 means there is no specified maximum. In this case, maximum
frame rate is determined by current camera settings.

## Image size

The size of the image in pixels. This is limited by the camera resolution (800x600 is quite common with
the high speed cameras). More information about measurement type specific image sizes can be found
from the respective helps.

### Field: width

Image width in pixels

### Field: height

Image height in pixels

## Image offset

Image offset determining which part of the cameras visible area is captured.
Zero X and Y means its the top left of the cameras area. Please note that this is limited
by the image size (for example if camera resolution is 800x600 and image size 400x400 the offset
cannot be 600x600 because the image would be outside camera area)

### Field: offset X

Image X offset in pixels

### Field: offset Y

Image Y offset in pixels

## Binning

Number of pixels to sum in horizontal and vertical direction. Range of values is 1..4.
Increasing the value to N will effectively make each pixel brightness N times higher, but
will also cut down the image resolution by N in the affected direction (horizontal or
vertical).

### Field: horizontal binning

Number of adjacent horizontal pixels to be summed (1..4).

### Field: vertical binning

Number of adjacent vertical pixels to be summed (1..4).

## Camera trigger mode

Selection if camera will start taking images automatically when finger touches the DUT,
or manually when measurement is started.

## Display backlight synchronization

Selection if display backlight is synchronized, or if camera's internal SW timing
(free-running) is used. If display backlight synchronization is enabled,
you should set exposure and other camera parameters such that the resulting frame rate is at least equal to the
display backlight frequency.

## Analysis timeout

Time indicating for how long images are captured for the analysis.

## Mode selection button

Change between Measurement and Result modes.

## Resulting max frame rate

This value is obtained from camera. This is the actual capture frame rate of the camera, subject to current parameters
such as exposure time, image size etc. Please note that this value is only updated when the Set Camera Parameters button
is pushed.

The unit is frames-per-second (fps). There is no absolute correct value for this, however this should
be considerably more than the screen fps. If screen has 60fps, this value should be greater than 200fps.

Frame rate is affected by exposure time and image size.

## Update display backlight period

This gives the current value of the period but the value used in camera sync is obtained in real time.
You should set exposure and other camera parameters such that the resulting frame rate is at least equal to the
display backlight frequency. In order to read the backlight period a videosensor is needed.

## Start

Start measurement with current parameters.

## Analyze

Analyze captured data again with given analysis parameters.

## Load data

Load previously captured measurement data

## Save data

Save current captured measurement data.