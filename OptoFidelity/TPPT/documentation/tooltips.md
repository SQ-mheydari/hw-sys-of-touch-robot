## Clearance

The z-coordinate in DUT context when the robot is touching the DUT. Clearance 0 will just barely touch the DUT surface while
clearance -1 mm causes robot to press against the DUT when robot tries to move the effector 1 mm below the DUT surface.

## Edge offset x

Distance between the edge of the screen and the area of screen that is tested along X-axis.

## Edge offset y

Distance between the edge of the screen and the area of screen that is tested along Y-axis.

## Edge offset

Distance between the edges of the screen and the area of the screen that is used in the test.

## Grid file

Which file is used as the grid file.

## Grid unit

Units in which the grid is defined.

## Use grid file

Is a grid file being used.

## Grid spacing x tap

Distance between individual points along X-axis of the DUT panel.

## Grid spacing y tap

Distance between individual points along Y-axis of the DUT panel.

## Grid spacing tap

Distance between individual points along both X- and Y-axis of the DUT panel.

## Grid spacing swipe

Distance between individual lines along both X- and Y-axis of the DUT panel.

## Swipe type

What kind of swipe gesture is done.

## Swipe radius

Swipe radius specifies the arc that is used for acceleration and deceleration for the swipe. The arc is a quarter of a 
circle defined by the radius.

## Worst case lines

Lines that are drawn along the edges of the DUT, lines drawn diagonally from corner to corner and lines that are only
half of the DUT width or height. These tend to be the worst possible cases for panels. 

## Vertical/horizontal lines

Lines are drawn in the direction of X- or Y-axis of the DUT panel.

## Diagonal lines

Lines are drawn so that both X- and Y-coordinates (in DUT context) are changed for the points in the line.

## Amount of points

How many points are tapped during the test.

## Amount of taps

How many times a point is tapped during the test.

## Tap duration

How long the tip is touching the DUT during the tap.

## Calibrate system latency

Is system latency calibrated at the start of the test.

## Tip 1

Tip used in finger that does not move.

## Tip 2

Tip used in the separated finger.

## Flip x

Is X-axis of DUT panel's coordinates flipped.

## Flip y

Is Y-axis of DUT panel's coordinates flipped.

## Flip x and y

Rotate by 90 deg and flip other coordinate. Coordinates are DUT context.

## Dut resolution

Dut resolution given manually. Overwritten when fetched automatically from DUT

## Fetch resolution

Resolution is fetched automatically from DUT.

## Pit slot

Slot that the PIT is connected to.

## Pit driver

Drivers for PIT.

## Driver

Possible drivers to be used.

## Line drawing speed

Robot speed when doing swipe gestures. Accepts list of speeds. example: (80.0, 90.0, 100.0)

## Default speed

Robot default speed.

## Default acceleration

Robot default acceleration.

## Tilt angles

Tilt angles of the tip. Either a list of angles (e.g. '10, 20, 30') or a range in format start:end:step, 
including end (e.g. '0:90:15'). Each point is repeated for all tilt and azimuth angle combinations.

## Azimuth angles

Azimuth angles of the tip. Either a list of angles (e.g. '10, 20, 30') or a range in format start:end:step, 
including end (e.g. '0:90:15'). Each point is repeated for all tilt and azimuth angle combinations.
