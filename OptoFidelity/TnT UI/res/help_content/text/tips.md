## Adding new tip

- To add new tip, press 'Add' button. Tip name cannot contain spaces or special characters, underscores are allowed. The name cannot start with a number.
- Fill in tip properties. Different tip models may have different set of required properties.
- To be able to use automatic tip pick and drop feature, 'Slot in' and 'Slot out' properties need to be set.
    - 'Slot in' and 'Slot out' properties can be set either manually or by using the automatic slot positioning wizard.

## Editing tips

- To edit an existing tip, click 'Edit' button next to the tip name. This will bring up a view similar to when adding a new tip.

## Copying tips

- To copy an existing tip, click 'Edit' and the 'Copy'. This will open a view where you can give the copy a new name and change other properties before saving.

## Positioning tips

Tips can be automatically picked from and dropped to slots in tip racks. For this to work, user must
first position slot-in and slot-out positions in a rack by moving the robot effector to those positions.

Note that with 2-finger / synchro robot, tool 1 i.e. the left finger is always used to position the slots. The correct finger is encircled in the figure below.

![Tip slot positioning.](ui_help_images/tip_positioning.jpg "Tip slot positioning.")

Tip can be then picked to either finger but the slot positioning is always done with the left finger to avoid confusion.

### One finger tips
- Manually
    - Slot in: Drive the robot head into the tip mount hole while the tip is attached to the tip rack. Click 'Set' button.
    - Slot out: Continuing from the previous step, drive the robot until the tip is completely out of the rack. Click 'Set' button.
- Automatically
    - Click the 'Automatic slot positioning' button to open a wizard and follow the instructions to set slot in and slot out positions automatically. The automatic slot xy-positioning relies of rack fiducials which together with the tip constitute a triangle pattern illustrated below.
![Tip fiducials.](ui_help_images/tip_fiducials.svg "tip_fiducials")

### Multifinger tips
Only manual positioning is available for multifinger tips.

- 'Slot in' and 'Slot out' are defined in a similar manner to one finger tips.
    - With multifinger tip positioning the difference to one finger positioning is that you have to line up both holes on the tip with the two tools on the robot head.
- The separation property of the tip needs to be set to the correct finger separation value which can be read from the UI position data in the lower left corner of the screen.
    - Best way is to drive the robot heads inside the tool and then copy the separation value immediately.

## Picking and dropping tips

- To be able to pick or drop a tip automatically, the tip 'Slot in' and 'Slot out' positions must have been defined.
- After tip 'Slot in' and 'Slot out' positions are defined the tip changing will be automatic 
unless the 'Manual tip changing' option is selected.
- If using two-finger robot, use the axial finger to teach the slot positions. If using synchro robot, use the primary
finger (labeled '1') to teach the slot positions.
- Click 'Drop' or 'Pick' button next to the tip name to drop or pick. If 'Manual tip changing' is selected or the tip position has not been saved,
then manually attach/detach the tip to/from the robot, otherwise the tip changing will be automatically handled.
- Multifinger tips have an additional property 'Grippable' which if selected moves the finger separation closer and thus pinches the multifinger tool for better stability.

## Tip dimensions

Tip has diameter and length both measured in millimeters. Tip diameter doesn't have any effect on robot motion but it can be accessed
via TnT Client. Tip length is important as it is taken into account by motion planning. If tip length is incorrect, there is a risk of
collision when performing e.g. gestures on a DUT.

![Tip dimensions.](ui_help_images/tip_dimensions.svg "tip_dimensions")

Multifingers have additional dimensions that need to be defined:

- Separation is the distance between the two holes in the multifinger tip.
- Tip distance describes the distance between each of the individual tips on the multifinger.
- Number of tips is the count of individual tips on the multifinger tip.
- First finger offset defines the distance between the middle point of the first finger and the middle point of the whole multifinger tool. The first finger is normally the tip that is closest to the primary robot head. Defining the first finger offset is important because the robot kinematics uses the first finger as position reference for the whole multifinger tool.

First finger offset is better described in the following figure.

![Multifinger dimensions.](ui_help_images/multifinger_dimensions.svg "multifinger_dimensions")

## Smart tips

Smart tip is a specific tip hardware that has a PCB for data storage. Tip properties such as length and diameter can be written to the data storage.
This information is then used in motion planning to validate tip status. If the data stored on the PCB does not match data properties of currently
attached tip in TnT Server book-keeping, an exception is raised and motion is not executed.

This feature can prevent collisions in error cases. For example, if robot attempts to drop currently attached tip but for some reason the physical
tip is not removed from the robot head, any subsequent gesture or tip change procedure would result in collision. With smart tips, the system
can verify if the physical tip attached to the robot matches the software book-keeping.

Smart tip property can be enabled in the tip edit UI. Once it is enabled, any subsequent motion planning that uses the tip will perform validation. OptoFidelity personnel will write
the correct properties to the smart tip data storage as part of robot delivery.
