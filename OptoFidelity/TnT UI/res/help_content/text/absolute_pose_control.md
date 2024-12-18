## Absolute pose control
This enables moving the robot to a pose given by the user. There is an input field corresponding to each axis. The 
linear axes are in given in millimeters and the angular axes in degrees.

The pose is always given in workspace coordinates. This corresponds to the 'tnt' context.

## Refresh fields
Click 'Refresh' to update the fields to the current robot position.

## Move robot to pose
Click 'Move' to move the robot linearly to the position defined by the input fields. 
Make sure there are no obstacles in the path!

If any of the input fields has an invalid value, it will be shown as red.
If the position is outside the axis bounds, the robot will not move and an error message will be shown.

## Move robot in increments
Click the minus and plus buttons next to the input fields to decrease or increase the axis value by the step size and 
move the robot to this new position.
The step size can be chosen from the dropdown menu next to the axes.

If the user edits the axis input fields, these buttons are disabled until 'Refresh', 'Move' or the minus/plus button of
another axis is pressed.
