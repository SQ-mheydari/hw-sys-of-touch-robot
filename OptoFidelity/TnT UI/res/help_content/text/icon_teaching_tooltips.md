## Enable crop box

Shows or hides the crop box on the camera image that is used to crop the desired icon from the image.

## DUT dropdown

Select the DUT to get image from the DUT where you want to crop icons.
This is especially useful if the DUT is rotated from the default orientation.

## Move to DUT

Move the robot so that camera is taking screenshots from the selected DUT.

## Add icon

Add the cropped portion of the camera image as an icon to the 'Icons' list.

## 2. Icon name

Give name to the new icon. Name must not contain word 'contours'.
## Min score

Sets minimum score while testing icons for DUT. Must be in range 0 < min score <= 1. If input is invalid, default value 
0.75 is used.

## Duration

Duration of video recording in seconds. If set to zero or invalid, a single screenshot is taken. 
Used when teaching blinking icons.

## Num colors

Number of colors to extract from icon. This should match the perceived number of distinct colors in the icon.

## Color threshold

Threshold in range 0 - 1 to determine if color components of detected icon and user specified colors match.

## Extract colors

Extract distinct colors from the icon so that user can select which colors are used in icon detection.