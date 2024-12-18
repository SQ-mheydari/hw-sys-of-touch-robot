## General

Physical button functionality is used when the user wants to press physical buttons on DUT or other devices with robot actuator. Depending on the robot model, the buttons can be pushed not only in up-down direction but also sideways. However, if you are planning to press buttons sideways, please contact OptoFidelity to make sure your robot supports the movement. 

The buttons are usually connected to DUTs. The DUT connection can be selected in the *Select button parent* dropdown menu. If you do not want to connect the button to any DUT, you can select *ws* (workspace) as button parent. All the buttons connected to a certain parent are listed in the view when the parent is selected.

![Physical buttons main view.](ui_help_images/phys_button_main.png "phys_button_main")

## Adding a new button
To add new buttons, please follow these instructions:

1. Select the object parent from the dropdown menu.
2. Click *Add* to enter the *Add button* view. 
3. Fill in the fields (more information about the field contents can be found from 'Editing a button' section below).
4. Click *Finish* to save the button.

## Editing a button

You can edit the button when creating it or by clicking *Edit* in the list view. In edit mode you have the following parameters:

![Physical button edit wizard.](ui_help_images/phys_button_edit.png "phys_button_edit")

- **Name:** the name of the button.
- **Button approach position:** The position where robot will go first before pressing the button. The position can be set by moving the robot to the intended position and then clicking *Set*.
- **Button pressed position:** When the robot is in this position, the button should be pressed down. Basically when pressing a button, the robot first goes to approach position and then linearly moves to the pressed position and then back to the approach position. This position can also be set by moving the robot to the intended position and then clicking the *Set* button.
- **Jump height**: When moving from button to button that have the same parent, robot uses the jump height. Basically the jump height can be set to zero. However, if there are some obstacles in the robot path, the jump height should be set to such value that there is no risk of collision. This is depicted in the figure below:

![Physical button jump motion.](ui_help_images/phys_button_jump.svg "phys_button_jump")

## Testing a button

You can test the button by clicking *Test* in the list view. When 'Test' is clicked the robot presses the button once. In this way you can ensure that you have set all the parameters correctly.

## Deleting a button

You can delete the button in the list view by clicking *Delete*.



