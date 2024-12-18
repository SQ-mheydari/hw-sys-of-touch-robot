Sequence Generator is used for creating sequences of operations that can be executed sequentially.
Sequence Generator allows saving and loading old sequences so they can be run again later.
You can also export the sequence into a python script.

On the left of the UI you can see the list of actions composing a sequence as well as some configurations.
On the right is camera preview and actions that can be inserted into the sequence.
You can select an action and its parameter, and then insert it into the sequence.

This UI uses a lot of tooltips, so in order to get information about functionalities
please move the mouse cursor on top of the functionality of interest to get more information:

![Sequence generator tooltips.](ui_help_images/seq_gen_tooltip_example.png "seq_gen_tooltip_example")

## Adding actions to the sequence

Often it is easiest to insert actions to the sequence by utilizing the camera view. For example, to insert Tap
action, you can click on the camera view to get the tap coordinates and simultaneously insert the Tap action to the sequence. Tap is always performed in DUT context so
in order for the coordinates to be obtained correctly, following must be considered:

- The target DUT should be selected as the active DUT in the dropdown menu on the left side.
- The DUT should be visible in the camera view and the DUT surface must be in camera focus. This can be achieved most easily by clicking the button "Move to imaging position".
- The coordinates are mapped from camera image pixel units to DUT context mm units. For this to be accurate, camera distortion and offset must be well calibrated. The coordinate conversion is most accurate near the center of the camera view.
- Each time the sequence or some robot movement is ran, the DUT most likely becomes out of camera focus. User must then again move to imaging position in order to use the camera view for creating actions.

By default the actions are inserted to the sequence when user clicks on the camera view. If the checkbox "Run action on click" is checked, then the action is ran immediately on click and the action is not inserted to the sequence.

## Creating HSUP sequence

Sequence generator can be used to run HSUP measurement by creating a sequence that has actions for starting the measurement, performing some movements with the robot and then showing the results.

A basic Watchdog sequence is illustrated in the picture below:

![HSUP action in sequence generator.](ui_help_images/seq_gen_hsup.png "seq_gen_hsup")

Robot first jumps near the top left corner of the DUT to get away from the camera view. Then Watchdog measurement is started. Path to camera settings YAML file is given as parameter. The path is relative to TnT Server installation path or an absolute path. Next a tap is performed near the middle of the DUT. Finally the sequence waits for the results to be available.

After the sequence is complete the UI will switch to the HSUP page to show the results. This page switch happens provided that there was a "Get results" HSUP action as part of the sequence.

Note that it is intended to run only one kind of HSUP measurement in one sequence. Attempting to run e.g. Watchdog and SPA measurements in the same sequence is undefined behavior.
