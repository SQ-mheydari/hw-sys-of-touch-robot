Stylus tool and camera offset calibration must be performed to be able to move the stylus accurately and to be able 
to map camera positions to robot positions.

OptoFidelity personnel will initally perform the calibrations as part of delivery.  

**Note:** Whenever a new stylus is installed, the calibration must be performed again.

Performing the calibration incorrectly causes risk of collision when using previously positioned DUTs.

## Overview

The offset of the stylus from the azimuth axis is calibrated using TnT UI and Audit gauge. The procedure simultaneously 
calibrates also camera offset to the azimuth axis and focus distance. This is because camera is used to perform stylus 
offset calibration but the same camera offset is also unknown at that stage.

Camera distortion must be calibrated before synchro calibration.

*Use low speed such as 20 mm/s during calibration. There is risk of colliding with the Audit gauge when doing the 
calibration.*

*Tilt axis must be set to zero during the calibration process. The wizard does not currently move the tilt axis
automatically. It is best to start doing the calibrations just after robot has homed and then not touch the tilt axis.*

## Starting calibration

Select the Stylus calibration view from the left panel of the Config
page. You should see this:

*(image_placeholder)*

Choose the camera that you want to use in offset calibration.

Click "Start Offset  Calibration" button to open the wizard which will instruct you through step-by-step calibration 
process.

Make sure the tilt axis is at zero position and azimuth angle
is zero.

The starting point of stylus calibration should look something like
this:

*(image_placeholder)*

## Step 1

In this step, you need to move the robot so that the audit gauge lit inset is at the focus of the camera in the 
camera view. You can place some paper target on top of the Audit gauge to see the focus better.

Notice that the camera focus must be adjusted from the lens so that when the lit inset is at focus, the robot tool is
higher than the Audit gauge lit inset. In images below, the first case represents incorrect focusing and the latter 
represents correct focusing:

*(image_placeholder)*

*(image_placeholder)*

When the lit inset is in focus, click "Save height". This will save the robot z-position so that it can be used later 
to move robot so that the inset is in focus.

*(image_placeholder)*

*(image_placeholder)*

Then click "Next".

## Step 2

In this step, move the stylus so that it is inside the audit gauge lit inset.

*(image_placeholder)*

Make sure that the moving part of the Audit gauge is centered as illustrated below:

*(image_placeholder)*

When the tool is in the lit inset, the voice coil should be compressed approximately 1 mm so that the lit inset is 
centered at the stylus. This is illustrated in the images below:

*(image_placeholder)*

*(image_placeholder)*

Then click "Save position". This will save to robot xyz position to be used later to move stylus close to lit inset.

Then click "Next".

## Step 3

In this step, user will collect a list of robot position-pairs where stylus is at target and when camera is at target. 
Initially the list is empty.

*(image_placeholder)*

User will first determine Robot position (stylus at target). When finger is inside the lit inset and voice coil has 
compressed approximately 1 mm, click "Set" next to "Robot position (stylus at target)". This saves robot position when
stylus is at target.

*(image_placeholder)*

Approaching "Robot position (stylus at target)" should look like in
figure below:

*(image_placeholder)*

Tool in "Robot position (stylus at target)" should look like in
figure below:

*(image_placeholder)*

Then user will determine Robot position (camera at target).
Click "Locate" next to "Robot position (camera at target)". This will first move robot directly upwards to height 
where the lit inset is in camera focus.

Then it will move robot until the camera center is at the lit inset
center. The "Locate" button will be disabled until complete.

The automatic lit inset search is sensitive to lighting conditions.
It may be best to turn off the lights in the room. In case the
algorithm fails after a fixed number of iterations, you can try again.

Bad lighting (several round shapes are visible):

*(image_placeholder)*

Good lighting (only lit inset is visible):

*(image_placeholder)*

After the lit inset is at camera center, click "Set" next to "Robot position (camera at target)".

*(image_placeholder)*

*(image_placeholder)*

Now the two positions have been set. Click "Append to list" to add this position-pair to the list.

*(image_placeholder)*

Then repeat previous steps for obtaining robot position-pair for a
number of different azimuth angles. To start, click "Locate" next to
"Robot position (stylus at target)". This will move the stylus
approximately above the lit inset. How close it will go depends on
how good the underlying calibration is (there must be some approximate
stylus calibration to start with). When the stylus is above the lit
inset, rotate azimuth to desired angle and then repeat the steps to
get the position-pair.

The minimum number of angles is 3 and usually this is sufficient.
So use angles 0 deg, -120 deg and 120 deg to get evenly distributed
set of points.

Setting "Robot position (stylus at target)" at azimuth angle 120 deg:

*(image_placeholder)*
*(image_placeholder)*

Setting "Robot position (stylus at target)" at azimuth angle -120 deg:

*(image_placeholder)*
*(image_placeholder)*

In the end you should have something like this:

![Final measurement list.](ui_help_images/synchro_step3_6.jpg "Final measurement list.")

Then click "Next".

## Step 4

Click "Calculate offsets" to finalize the calibration. The residual error should be much less than 1.0 to be viable.
Usually it is in the order 0.01.

*(image_placeholder)*

Below there is also a button for performing refined calibration. This will use the new calibration to collect new data 
set completely automatically. Usually this is not done.

Click "Finish" to save the calibration to permanent configuration.

## Verifying offset calibration

Accurate verification requires absolute positioning device such as a laser tracker.

To verify roughly by visual inspection, you can rotate the tool from UI with varying separations and inspect if the 
stylus xy position is stationary or not.
