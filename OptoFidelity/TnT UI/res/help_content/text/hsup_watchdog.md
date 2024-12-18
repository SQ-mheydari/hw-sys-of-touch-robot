## Watchdog analysis

WatchDog is a tool for measuring response times and latencies of user interfaces. It can be used for example to define 
the starting time of an application. This is achieved by measuring the time from tapping the icon to the point when the 
application appears fully loaded on the display.

Watchdog analysis detects changes in the display content based on changes in the captured image content. The variance
of pixels (or variance image) is added up to a single value. A time series of these values creates signal, from which
content change start and end time instances are detected. These are called events.

### Basic usage tips

- Before starting a measurement, set the measurement configuration as desired, see the tooltip help for explanation of 
each configuration setting.
- Position the camera to ideally show only the DUT screen. You can further narrow down the analysed area by enabling
the ROI and specifying a region of interest within the camera view.
- Make sure that the robot movements are not visible inside the ROI.
- Make sure that there aren't any reflections of the moving robot visible inside the ROI. These could be falsely 
detected as change events in the DUT screen content. Example image below shows robot finger reflected on DUT screen.

![Robot reflection visible on DUT.](ui_help_images/wd_finger_reflection.jpg "Robot reflection visible on DUT")

- Make sure that the robot movements do not cause the camera to shake. A shaking camera will register as detected change
in the DUT screen content.
- Camera capture rate will determine the temporal resolution of event detection. With higher framerates, the time instances
of events are more accurately determined. 
- To increase the capture framerate, reduce the image size to already approximate your region of interest for the 
measurement and reduce exposure time if possible. Please note that the ROI size doesn't affect the camera framerate.
- With a high capture framerate slow transitions in the DUT content will appear as sawtooth-like waveform in the change
signal, as illustrated in the image below. This can lead to many events being detected. In this case you should increase 
the minimum intra-event duration time to ignore the short-duration transients in the signal analysis.

![Slow events may appear as multiple single events.](ui_help_images/wd_slow_transition_event.png "Slow events may appear as multiple single events")

- Note that minimum-intra event duration must be at least equal to the duration of one frame capture (the reciprocal of 
the camera capture frame rate).
- Change detection uses a normalized scale in which the largest detected change has the value 1. Therefore, some of the
smaller changes may drop below the set threshold, as highlighted in the figure below. Lower the event detection 
threshold to detect the events as required.  

![Change signal is always normalized to 1.](ui_help_images/wd_event_scaling_normalized.png "Change signal is always normalized to 1")

### Watchdog events

Watchdog events are defined as parts of the content change signal where the signal value first rises above the threshold 
value and then returns to a level below it. During an event the change signal value remains above the threshold value. 
The end of one event and the beginning of the next one must be separated at least by the specified minimum intra-event 
duration. However, there is no defined minimum or maximum duration for the event itself. 