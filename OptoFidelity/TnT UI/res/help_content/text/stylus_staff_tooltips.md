## Stylus name

Currently attached tip that is the target of stylus calibration.
To change the active tip, see the Tips view.

If tip is not attached, the attached tool is the target of stylus calibration.
To change the active tool, see the Tools view.

## Positions

List of robot positions where robot tilt and azimuth are different and
the stylus end effector is at the same workspace location.

## Save position

Click to save current robot position as new entry in the list.

## Calculate

Click to calculate the stylus tool offset from the list of positions.
There must be at least three positions but usually at least five is recommended.
User is prompted to save the result.

## Load

Load robot position list from database to inspect previous calibration.

## Weight current

Calculate a more accurate stylus tool offset for one specific orientation.
There must be two saved positions: one with zero tilt and azimuth, and the desired
orientation.
