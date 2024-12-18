Synchro finger and camera offset calibration must be performed to
be able to move robot fingers accurately and to be able to map camera
positions to robot positions.

OptoFidelity personnel will perform the calibrations as part of
delivery and in normal circumstances user should not need to
calibrate again.

*Performing the calibration incorrectly causes risk of collision
when using previously positioned DUTs, tips etc.*

## Overview

The offset of both fingers to the azimuth axis is calibrated using TnT
UI and Audit gauge. The procedure simultaneously calibrates also camera
offset to the azimuth axis and focus distance. This is because camera
is used to perform finger offset calibration but camera offset is also
unknown at that stage.

Camera distortion must be calibrated before synchro calibration.

*Use low speed such as 20 mm/s during calibration. There is risk of
colliding with the Audit gauge when doing the calibration.*

*Separation axis must be at home position during the calibration
process. The wizard does not currently home the separation
automatically. It is best to start doing the calibrations just
after robot has homed and then not touch the separation axis.*

## Starting calibration

Select the Synchro calibration view from the left panel of the Config
page. You should see this:

![Synchro calibration view.](ui_help_images/synchro_view.jpg "Synchro calibration view.")

Choose the camera that you want to use in offset calibration.

You can calibrate both fingers one at a time. Click "Start Offset
Calibration" button to open the wizard which will instruct you through a
step-by-step calibration process.

Make sure the separation axis is at home position and azimuth angle
is zero.

The starting point of synchro calibration should look something like
this:

![Synchro calibration starting point.](ui_help_images/synchro_start.jpg "Synchro calibration starting point.")

## Step 1

In this step, you need to move the robot so that the audit gauge lit
inset is at the focus of the camera in the camera view. You can place
some paper target on top of the Audit gauge to see the focus better.

Notice that the camera focus must be adjusted from the lens so that
when the lit inset is at focus, the robot tool is higher than the
Audit gauge lit inset. In images below, the first case represents
incorrect focusing and the latter represents correct focusing:

![Bad focus.](ui_help_images/synchro_focus_bad.jpg "Bad focus.")

![Good focus.](ui_help_images/synchro_focus_good.jpg "Good focus.")

When the lit inset is in focus, click "Save height". This will save
the robot z-position so that it can be used later to move robot so that
the inset is in focus.

![Synchro calibration step 1.](ui_help_images/synchro_step1.jpg "Synchro calibration step 1.")

![Synchro calibration Audit gauge in focus.](ui_help_images/synchro_step1_focus.jpg "Synchro calibration Audit gauge in focus.")

Then click "Next".

## Step 2

In this step, move the finger so that it is inside the audit gauge
lit inset.

![Synchro calibration step 2.](ui_help_images/synchro_step2.jpg "Synchro calibration step 2.")

Make sure that the moving part of the Audit gauge is
centered as illustrated below:

![Audit gauge centered.](ui_help_images/synchro_audit_centered.jpg "Audit gauge centered.")

When the tool is in the lit inset, the voice coil should be compressed
approximately 1 mm so that the lit inset is centered at the finger.
This is illustrated in images below:

![Tool in Audit gauge.](ui_help_images/synchro_tool_in_audit.jpg "Tool in Audit gauge.")

![Voice coil flex while tool is in Audit gauge.](ui_help_images/synchro_vc_flex.jpg "Voice coil flex while tool is in Audit gauge.")

Then click "Save position". This will save to robot xyz position to be
used later to move finger close to lit inset.

Then click "Next".

## Step 3

In this step, user will collect a list of robot position-pairs where
robot finger is at target and when camera is at target. Initially the
list is empty.

![Synchro calibration step 3.](ui_help_images/synchro_step3.jpg "Synchro calibration step 3.")

User will first determine Robot position (finger at target).
When finger is inside the lit inset and voice coil has compressed
approximately 1 mm, click "Set" next to
"Robot position (finger at target)". This saves robot position when
finger is at target.

![Set robot position (finger at target).](ui_help_images/synchro_step3_2.jpg "Set robot position (finger at target).")

Approaching "Robot position (finger at target)" should look like in
figure below:

![Synchro tool above Audit gauge.](ui_help_images/synchro_angle1_out.jpg "Synchro tool above Audit gauge.")

Tool in "Robot position (finger at target)" should look like in
figure below:

![Synchro tool in Audit gauge.](ui_help_images/synchro_angle1_in.jpg "Synchro tool in Audit gauge.")

Then user will determine Robot position (camera at target).
Click "Locate" next to "Robot position (camera at target)". This will
first move robot directly upwards to height where the lit inset is in
camera focus.

Then it will move robot until the camera center is at the lit inset
center. The "Locate" button will be disabled until complete.

The automatic lit inset search is sensitive to lighting conditions.
It may be best to turn off the lights in the room. In case the
algorithm fails after a fixed number of iterations, you can try again.

Bad lighting (several round shapes are visible):

![Bad lighting for lit inset search.](ui_help_images/synchro_lit_inset_bad.jpg "Bad lighting for lit inset search.")

Good lighting (only lit inset is visible):

![Good lighting for lit inset search.](ui_help_images/synchro_lit_inset_good.jpg "Good lighting for lit inset search.")

After the lit inset is at camera center, click "Set" next to
"Robot position (camera at target)".

![Camera centered to lit inset.](ui_help_images/synchro_step3_3.jpg "Camera centered to lit inset.")

![Position-pair completed.](ui_help_images/synchro_step3_4.jpg "Position-pair completed.")

Now the two positions have been set. Click "Append to list" to add
this position-pair to the list.

![Apped position-pair to list.](ui_help_images/synchro_step3_5.jpg "Apped position-pair to list.")

Then repeat previous steps for obtaining robot position-pair for a
number of different azimuth angles. To start, click "Locate" next to
"Robot position (finger at target)". This will move the finger
approximately above the lit inset. How close it will go depends on
how good the underlying calibration is (there must be some approximate
finger calibration to start with). When the finger is above the lit
inset, rotate azimuth to desired angle and then repeat the steps to
get the position-pair.

The minimum number of angles is 3 and usually this is sufficient.
So use angles 0 deg, -120 deg and 120 deg to get evenly distributed
set of points.

Setting "Robot position (finger at target)" at azimuth angle 120 deg:

![Synchro tool above Audit gauge at azimuth 120 deg.](ui_help_images/synchro_angle2_out.jpg "Synchro tool above Audit gauge at azimuth 120 deg.")
![Synchro tool in Audit gauge at azimuth 120 deg.](ui_help_images/synchro_angle2_in.jpg "Synchro tool in Audit gauge at azimuth 120 deg.")

Setting "Robot position (finger at target)" at azimuth angle -120 deg:

![Synchro tool above Audit gauge at azimuth -120 deg.](ui_help_images/synchro_angle3_out.jpg "Synchro tool above Audit gauge at azimuth -120 deg.")
![Synchro tool in Audit gauge at azimuth -120 deg.](ui_help_images/synchro_angle3_in.jpg "Synchro tool in Audit gauge at azimuth -120 deg.")

In the end you should have something like this:

![Final measurement list.](ui_help_images/synchro_step3_6.jpg "Final measurement list.")

Then click "Next".

## Step 4

Click "Calculate offsets" to finalize the calibration. The residual
error should be much less than 1.0 to be viable.
Usually it is in the order 0.01.

![Synchro calibration step 4.](ui_help_images/synchro_step4.jpg "Synchro calibration step 4.")

Below there is also a button for performing refined calibration.
This will use the new calibration to collect new data set completely
automatically. Usually this is not done.

Click "Finish" to save the calibration to permanent configuration.

## Verifying offset calibration

Accurate verification requires absolute positioning device such
as a laser tracker.

To verify roughly by visual inspection, you can rotate the tool from
UI with varying separations and inspect if the finger xy position is
stationary or not.
