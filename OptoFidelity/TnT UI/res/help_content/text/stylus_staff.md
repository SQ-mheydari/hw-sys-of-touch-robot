Stylus is a tip which has offset in x, y and z directions. Stylus calibration needs to be done
in order to be able to move the effective position accurately when changing the tilt and azimuth angles of the robot.
The calibration is also required before DUTs can be positioned with the stylus tip.

## Stylus mounting

1. Mount the stylus to the stylus holder by loosening the 4 screws on the holder.
2. Insert stylus into the holder. Convenient tip distance from blue mounting block is ~30mm.
3. Tighten the 4 screws. No excessive tightness required.

![Stylus mounting.](ui_help_images/staff_stylus.jpg "Stylus mounting.")

## Stylus calibration

Stylus calibration is based on use of two-camera calibration device.
The stylus tip is brought to the same location with varying tilt and azimuth angles
with the help of two camera images. The calibration procedure is done using the Stylus calibration
view in TnT UI.

### Step 1

Open TnT UI Config page and Stylus calibration view.

Once the calibration view is opened in the UI, two camera images should be visible.

The view indicates which tip resource is currently attached to the robot. The stylus calibration will target that resource.
You can create new tips and attach and detach them in the Tips view in the UI.

### Step 2

1. Drive the stylus tip to ~1mm distance from the LED blob.
2. Use 0 degrees tilt and azimuth angles at first.

![Stylus calibration start.](ui_help_images/staff_stylus_calib_start.jpg "Stylus calibration start.")

### Step 3

1. Check that the stylus tip is visible in both x- (left) and y-axis (right) stylus cameras.
    - If not, move the stylus so that it is visible in both images
    - Adjust the stylus tip position until it can be seen sharply in both images.

### Step 4

1. Choose New from data set dropdown list and click Load to generate new calibration.
2. Click Save position.

- New data element will appear to Positions -list with saved axis locations.
- Since this is the first saved position to this data set, also images are saved. From this on this original position of stylus tip shown in images with light gray color.

![Stylus calibration first image.](ui_help_images/staff_stylus_calib_first.jpg "Stylus calibration first image.")

### Step 5

1. Turn tilt and azimuth to new values (see list below).
2. Align the current stylus tip with original tip position and save positions.

List of angles

- Tilt 0 deg, Azimuth 0 deg
- Tilt 30 deg, Azimuth 45 deg
- Tilt 45 deg, Azimuth 90 deg
- Tilt 45 deg, Azimuth -45 deg
- Tilt 45 deg, Azimuth -90 deg

![Stylus calibration second image.](ui_help_images/staff_stylus_calib_second.jpg "Stylus calibration second image.")

### Step 6

1. After saving at least 5 positions, click on the calculate button to generate new stylus calibration.

Notice that the calibration results is stored to the currently attached tip resource.
To calibrate other styluses, go to Tips view to first attach the target stylus tip.

## Weighting to current orientation

The stylus calibration is not perfectly accurate in every orientation.
To get a more accurate position, the calibration can be performed for a specific orientation.

### Step 1

Perform the stylus calibration as shown above.

### Step 2

It is recommended to create a copy of the tip for each orientation you want to calibrate.

1. Go to tips view.
2. Click 'Edit' next to the tip you calibrated and then 'Copy'.
3. Name the tip descriptively (e.g. 'stylus_t10' for tilt = 10) and click 'Finish'.
4. Click 'Pick' next to the copy you just created.

### Step 3

Now the calibration procedure is repeated but this time with only two positions.

1. Go to Stylus calibration view.
2. Set azimuth = 0 and tilt = 0.
3. Move the stylus tip so that it is visible in the cameras and click 'Save position'.
4. Set the azimuth and tilt to your desired orientation.
5. Align the tip with the previous tip position and click 'Save position'.

### Step 4

Click 'Weight to current orientation' and then Ok.

Warning: The calibration is no longer accurate if you change the orientation.
To calibrate for a different orientation, repeat the steps.
