This UI uses a lot of tooltips, so in order to get information about functionalities
please move the mouse cursor on top of the functionality of interest to get more information:

![Example of HSUP tooltip.](ui_help_images/tooltip_example.png "tooltip_example")

## General Information

The UI has been organized into views that have two modes, namely _Measurement Mode_ and _Result Mode_.

Views for different analysis types can be changed from the navigation bar on the left, where **W** stands for Watchdog,
**S** for Scroll Performance Analysis and **P** for Pen to Ink.

You can change between Measurement Mode and Result Mode by pressing the right arrow next to the mode text in the
title bar of the view.

Measurement Mode is used to configure the system for the given analysis. The left pane has title bar with analysis name
and currently selected mode, camera viewer for showing live camera stream, buttons to perform operations and then
analysis specific configurations. The right pane contains configuration for the measurement, i.e., mainly camera parameters.

For starting a measurement, set parameters and then press `Start` button.

`Load data` button can be used to load existing analysis data that has been earlier stored with `Save data` button.

Result Mode is used to visualize the results to be able to determine that the analysis worked fine. The left pane has
the same content as in the Measurement Mode except the camera viewer is now image viewer showing analyzed images. The
right pane will have analysis specific content including graphs and statistics. You can click any of the graphs and
corresponding image will be shown in the image viewer on the left. More details about the content of the Result Mode in
analysis specific parts.

## HSUP configuration

Measurement mode is used to configure the analysis. You should adjust the parameters to have a clear camera image and
get a rather high FPS value of around 250 or more.

Try to limit the image size as much as possible to achieve better FPS. You can see the resulting frame rate with the
given parameters when the parameters have been applied to the camera with `Set Camera Parameters`.

As there are many interdependent parameters, all the combinations might not be allowed. See the log window in the lower left corner to see if there are any errors or warnings that would require your attention.


If display backlight synchronization is enabled, you should set exposure time at least 5% lower than display backlight period.

## HSUP Troubleshooting

### Camera image not shown after clicking "Enable Camera"
This might be caused by not getting proper sync signal for backlight synchronization if that is enabled. You can check the signal quality by clicking "Update display backlight period". If you get a number, the signal is ok. If you get, for example, "Full persistence mode" you should check the fiber installation.


