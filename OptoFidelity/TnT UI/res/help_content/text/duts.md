## DUT geometry

DUT geometry is defined by the 3-D positions of its three corners: top right, top left and bottom left.

![DUT corners.](ui_help_images/dut_corners.jpg "DUT corners.")

DUT needs to be rigidly attached to the robot workspace before it can be positioned. The DUT Holder Kit
consists of M4 bolts and washers that can be used for this purpose. Make sure that the bolts don't extend over
the DUT surface to avoid collisions during swipe gestures.

![DUT attachment.](ui_help_images/dut_attachment_detail.jpg "DUT attachment.")

There are multiple ways of defining the DUT corners. In case of an Android device, a fully automatic procedure is available.

## Adding DUT

To add a new DUT press 'Add new DUT' button. DUT name cannot contain spaces, numbers or special characters.

## Positioning DUT manually

![DUT positioning with tip.](ui_help_images/dut_positioning.jpg "DUT positioning with tip.")

The positioning procedure is based on first moving robot tip to each corner to teach corner xyz coordinates and then moving the camera center over
each corner to refine the xy coordinates. This is illustrated in the picture above.

![DUT positioning with camera.](ui_help_images/dut_positioning_camera.jpg "DUT positioning with camera.")

In case of Android device, open OptoTouch-app on the DUT to get the corners visible. If the corners are not visible enough when using the main view use P2I view which can be opened by tapping the 'P2I' button in the app.

1. Select desired DUT from the dropdown menu in TnT UI and press 'Edit' button
1. First position the DUT roughly by using robot's tip.
1. To position the DUT roughly, drive robot over the top right corner of the DUT. Robot's tip must touch the screen.
   - You can use the Probe functionality in robot controls if the system supports it, or
   - You can use a thin piece of paper to determine the exact z-positions. Place the paper on the DUT screen and drive the tip towards DUT surface by small steps (0.1mm) until you can no longer easily move the paper.
1. Press 'Tip' button under the 'Top Right' section. This will save the x, y and z coordinates of the robot's current position.
1. Repeat step 4 and step 5 for top left and bottom left corners.
1. Raise the robot to focus height from the DUT surface by pressing 'Move to Focus Height' button.
1. Get the exact x and y position of the DUT by using the camera. 
1. Move the robot so that bottom left corner of the DUT is seen in the center of the camera image. Camera image
can be zoomed in the 'Camera tab'.
1. Press 'Camera' button under the bottom left corner section. This will update the DUT corner x and y coordinates as determined by the camera center position. The z coordinate determined in the rough positioning remains unchanged.
1. Repeat step 9 ja 10 for top left and top right corners.
1. Press 'Finish' button  to save the positioning.
1. Test that the positioning is correct by using the test buttons on the DUT view.

**Note that you need to do camera calibrations before DUT positioning in order to achieve most accurate positioning results.**

## Positioning DUT automatically

**Automatic positioning might not be supported in all the versions**

1. Connect the DUT to the PC by connecting them to the same wifi network, using USB tethering from the DUT or using USB with adb (android debug bridge). If none of these options is possible manual positioning needs to be used.
2. Open OptoTouch-app on the DUT
3. Make sure that you have created the DUT you want to use in TnT UI. The DUT must have a name but other properties can remain unset.
4. In the OptoTouch-app set correct parameters and tap connect (**The name of the DUT needs to be the same in the
DUT app and computer configuration**). If using adb DUT's IP should be '127.0.0.1'.
5. Select desired DUT from the dropdown menu in TnT UI and press 'Edit' button
6. The connection bar in the 'Edit' page should be green and say "connected". If not, please check connection
information
7. Click 'Autolocate DUT' and follow the instructions of the wizard
8. After wizard is finished press 'Finish' button to save the positioning.
9. Test that the positioning is correct by using the test buttons on the DUT view.