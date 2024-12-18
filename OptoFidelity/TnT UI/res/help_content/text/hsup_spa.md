## SPA analysis

Scroll Performance Analysis (SPA) detects display content update rate from a stream of images captured with a
high-speed camera. A typical use case of SPA is to scroll content, a list of contacts for example, on the DUT display. 
During scrolling, the update rate is measured to determine if change is smooth and constant, or if there are unexpected 
glitches and pauses. 

Update rate or frames per second count is calculated from time instances at which change in the
content was detected. In a manner similar to Watchdog analysis, the variance of pixels between successive images (or 
variance image) is added up to a single value. A time series of these values creates signal, from which
content change time instances are detected.

### Basic usage tips

- Before starting a measurement, set the measurement configuration as desired, see the tooltip help for explanation of 
each configuration setting.
- Position the camera to ideally show only the DUT screen. You can further narrow down the analysed area by enabling
the ROI and specifying a region of interest within the camera view.
- Make sure that the robot movements are not visible inside the ROI.
- Make sure that there aren't any reflections of the moving robot visible inside the ROI. These could be falsely 
detected as changes in the DUT screen content. Example image below shows robot finger reflected on DUT screen.

![Robot reflection visible on DUT.](ui_help_images/wd_finger_reflection.jpg "Robot reflection visible on DUT")

- Make sure that the robot movements do not cause the camera to shake. A shaking camera will register as detected change
in the DUT screen content.
- Camera capture rate will determine the temporal resolution of change detection and framerate calculation. With higher 
camera capture framerates, the time instances of changes events are more accurately determined. This results in a more
accurate determination of the DUT content update rate.
- To increase the camera capture framerate, reduce the image size to already approximate your region of interest for the 
measurement and reduce exposure time if possible. Please note that the ROI size doesn't affect the camera framerate.
- Change detection uses a normalized scale in which the largest detected change has the value 1. Therefore, some of the
smaller changes may drop below the set threshold. Lower the event detection threshold to detect the changes as required.  

### SPA Troubleshooting
This section offers solution proposals to most commonly encountered problems with SPA measurements.

**1. All content changes are not detected**

- Make sure the image is not too bright or dark. Over or under exposure can remove details from image making it harder 
to detect changes. Adjust lens aperture to change the image brightness. Changing camera exposure value can help too, but 
increasing exposure time will lower the acquisition frame rate. 

- During measurement, every time the screen is updated, content in the area of interest should change. Very small 
changes might be undetected. 

- If content is constantly changing in each camera frame then changes are not detected correctly. For this reason 
acquisition frame rate must be higher than screen refresh rate. If camera or DUT is constantly shaking this might cause 
constant changes in the image. Shadows or other changes in illumination can cause the same effect. Try to eliminate any 
changes in the image other than DUT content changes. 

**2. Changes are detected even if screen content does not change**

- Vibrations, shadows or other sources might cause temporary sudden change to the image even if no changes are visible 
on the screen. Try to eliminate accidental movements of the DUT and changes in illumination. Increasing event detection
threshold level can also help if change signal level from error sources is close to the level of actual content change
signal levels. 

**3. Content change is detected multiple times when screen is refreshed**

- The whole screen might not get updated at the same time, but in sections or in a progressive "rolling" manner. If the 
measurement area includes large area of the screen, then it is possible to detect multiple changes from different 
sections of the screen. Decrease the size of area of interest (ROI) to avoid this. 

**4. FPS graph shows drops in content update rate**

- If you see a dip in the FPS graph, you can examine the data more closely to verify the dips in FPS graph correspond to 
dropped frames in the content. Clicking on the low FPS value on the graph will show the image number which was the last 
detected DUT content update before a dip in the FPS values. Zooming in on the change graph around this frame number 
should reveal something similar to the example image below, in which a frame update is missing at around frame 144.

![Dropped frame in SPA measurement.](ui_help_images/spa_dropped_frame.png "Dropped frame in SPA measurement")

**5. FPS graph shows too high values**

- FPS values that are too high and "impossible" for the DUT in question are caused by the nature of the measurement. 
Because the DUT display frame buffer is not directly accessed, no accurate timing data for the display update time
instances is available. Instead, the update time instances are determined from a camera view with a limited capture 
frame rate and therefore limited temporal resolution. Moreover, the capture camera is _not_ synchronized to the update 
rate of the DUT content. The lack of synchronization means that the time instances where content update is detected in
the SPA analysis can vary in time, i.e. it exhibits jitter. Due to the relatively low sampling rates used, a detection
jitter of even one frame can have a dramatic effect in the resulting FPS value. In the example image below, the camera 
capture rate was 235.8 Hz with the DUT having approximately 60 Hz content update rate. This means that the content 
update period is approximately 4 frames. If the detected time instance of the content update is off by just one frame 
and the content update is detected after 3 frames, the calculated FPS value jumps to 78.6 FPS. Increase the camera
capture rate to lower the amplitude of possible spikes on the FPS graph.

![Spikes in SPA measurement.](ui_help_images/spa_framerate_spikes.png "Spikes in SPA measurement")
