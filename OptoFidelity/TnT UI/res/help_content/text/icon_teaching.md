## Camera controls

To get a screenshot of the given DUT, select the DUT from the dropdown list and press "Move to DUT".
This will move the robot so that camera is taking screenshots from the DUT. This is especially useful
if the DUT is rotated from the default orientation. Note that the image may look incorrect if the camera is not over
the selected DUT as the image transformation on rotated DUTs can cause the image to look weird in other positions.

If the DUT is not completely visible in the image, you can still move the robot when you have used "Move to DUT" button.
If you want to move in DUT X and Y directions, select DUT name from the "Context" dropdown and use robot controls.
To revert back to getting full camera image, set DUT to "-None-".

## Cropping icons

Check the "Enable crop box" button to enable the icon cropping box.

You can drag the cropping box corners to reshape the box or you can drag the box from the edges to move it around.

After the cropping box is over the desired icon, click the 'Add cropped icon' button to add the icon to the 'Icons' list.

Clicking on the button opens a dialog for adding the icon. The dialog shows a preview of the icon, the icon shapemodel and an input box for the name.

## Testing icon recognition

You can test the icon recognition for taught icons by clicking the 'Test' button for that particular icon.

Additionally you can edit already taught icons simply by clicking the 'Edit' button for that icon. 'Edit' button opens a wizard that offers a possibility to edit or delete the icon.

## Icon recognition test results

The result modal shows all icons in the image that were matched to the model icon with equal or higher score than the 
value of the 'Min score' field. Found icons are shown in the image with a box drawn around them.

The value that is shown next to the box is the score for that icon. Score is the measure of how much of the model can be
found from the image. If score is 1 whole model was found, if score is 0.5 half of the model was found etc.

Image is centered to the result with the highest score. If the result with the highest score is so close to an edge of
the image  that the image cannot be fully centered to it, the image will be centered as much as possible.

## Color icon detection

If quantized color detection has been configured in TnT Server, user can select which colors from the icon are used
to determine a color matching score during detection.

To choose the colors that the detection should consider, go to icon edit mode and press "Extract colors" button. A list
of distinct colors from the icon are extracted and listed. Click the checkboxes next to the colors
to indicate that those colors should be used during icon detection. For example if here is a blue icon over black
background, it is usually best to check the blue color but not the black color.

The number of colors to extract can be controlled with the number field "Num colors". The number should match the
number of expected significant colors. For example, a blue icon over black background would have two distinct colors
so the number should be set to 2. If in that case the number is set to e.g. 5, different shades between black and blue
would probably be extracted because there is typically some gradient transition between these colors in the image.

The "Color threshold" value is in range 0 - 1 and is used when comparing the color components of the detected icon
and the colors chosen by user. If all color components are within threshold, then color detection score is 1.
Otherwise the score is 0. The final icon detection score is the product of the shape matching score and color detection
score.
