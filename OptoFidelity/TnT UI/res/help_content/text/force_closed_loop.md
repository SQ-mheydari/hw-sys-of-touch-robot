## Closed loop force calibration

Before starting the procedure, make sure that the tool is slightly (about 1mm) above the center of the calibrator surface.

![Tip 1mm from tool.](ui_help_images/force_tip_1mm_from_surface.svg "Tip 1mm above calibration tool")

Force calibration procedure runs automatically after pressing 'Start calibration' button.
This will take few minutes to complete.

The results are shown in the graph on the right hand side as progress occurs.

After the calibration procedure is finished the results can be saved by pressing the 'Save Calibration'
button that appears when the procedure is completed.

If surface probing is enabled it is possible to automatically find the proper starting height for the calibration. Just check the "Use surface probe" box and probing will be done when starting calibration. Correct x and y positions still need to be given manually. There should also be enough space between the finger tip and the calibration tool (for example 40mm would be safe). This position is saved to be used in validation.

![Tip in safe distance.](ui_help_images/force_tip_40mm_from_surface.svg "Tip is in safe distance")


## Closed loop force validation

Calibration should be saved before validation. The saved calibration can be validated using the force calibrator. Software will automatically move the tool to the correct position for validation.

Select the amount of points to use in validation with the 'Validation points' setting. Minimum number of points is 2, the beginning of the saved force scale and the end.

Force validation procedure runs automatically after pressing 'Start validation' button.
This will take few minutes to complete.

The results are shown in the graph on the right hand side as progress occurs.

After the validation procedure is finished 95% and 99,7% confidence intervals, and the mean error are shown in the result text box below the buttons.

Robot automatically moves to the correct position when starting validation based on the position saved in the calibration. If calibration was not done and user wants to validate the existing calibration, robot must be moved so that the tool touches the center of the sensor.