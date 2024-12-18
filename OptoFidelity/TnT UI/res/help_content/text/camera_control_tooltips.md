## Selection

Select camera to control.

## Enabled

Check box to control if camera is enabled or not.
Only one camera is enabled at a time. Once camera is enabled, previous camera is disabled.

## Calibrated

Is camera image distortion calibrated or not.
Should be enabled in order to accurately move robot from camera image
and to e.g. teach icons.

## Exposure

Control camera exposure time. Higher exposure means brighter image but may cause
motion blur or increase acquisition time.

## Gain

Control camera gain. Higher gain means brighter image but may introduce noise.

## Zoom

Control camera zoom. This is digital zoom i.e. camera image is cropped around the center.
Zoom value 1 corresponds to the original camera image.

## Scaling

Scaling factor for camera image resolution. Value 1 corresponds to the original camera image.
Smaller values downscale the image. Use of scaling less than 1 degrades
image quality but may improve streaming frame rate.

## Interpolation

Choose which interpolation method is used when image is downscaled.
Quality improves in order 'nearest', 'linear', 'cubic' but at the cost of performance.
With very high resolution images this may affect streaming performance.

## On click action

Select action that is taken when user left-clicks the camera image.
None: Nothing happens.
Move camera: Camera center is moved to clicked location by moving robot to which the camera is attached to.
Move robot: Robot effector is moved to clicked location. Also works if camera is not attached to the robot. 
Following must be true for correct use: 1) Movement target must be at camera focus, 2) Distortion correction should be enabled, 3) camera PPMM value must have been calibrated (happens during distortion calibration).

## Auto-exposure

Find camera exposure where the image is not significantly under or over exposed over the entire camera image.
This may take a few seconds. Note that if there are light sources or bright reflections on the camera image,
this operation usually results in heavily under exposed image on average.

## To focus height

Move robot to height where current effector position is at focus.
To make surface appear at focus, first move camera effector so that it touches the surface.

## Robot to camera

Move robot effector xy position to the current camera center xy position.
This can be used to e.g. validate camera-offset calibration accuracy.
