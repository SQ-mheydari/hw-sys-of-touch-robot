# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

# [5.19.1] - 2023-12-19

## 2023-12-19
### Changed
- Improved Halcon OCR procedure for finding text patterns.
- Updated Pysimplemotion and added parameter for controlling synchronization interval.
- Improved logging of Halcon OCR detection results.

## 2023-12-04
### Fixed
- Incompatibility issue between Halcon 13 and Halcon 22 shape model files.
- Poor shape model quality with Halcon 22 due to missing grayscale conversion.


# [5.19.0] - 2023-10-12

## 2023-10-13
### Fixed
- Movement problems appearing with some systems when using pysimplemotion.
- Halcon OCR initialization procedure when there is no GPU support.
- Halcon OCR detection procedure when no text is found. 

## 2023-10-05
### Added
- Halcon 22 icon teaching and detection. Halcon 13 is still supported. The backend can be
  defined in config with "version" parameter.
- Possibility to pass icon teaching and detection parameters via API.
- Possibility to set all Halcon icon detection parameters with Halcon 22.

# [5.18.0] - 2023-09-13

## 2023-09-13
### Fixed
- Motion issues when capturing images with a Hikvision camera.

## 2023-08-31
### Added
- Halcon OCR detector.

## 2023-08-18
### Removed
- Removed optocamera-basler driver.

# [5.17.3] - 2023-07-25

## 2023-07-25
### Fixed
- Update Hikvision backend to fix memory leaks.

# [5.17.2] - 2023-06-20

## 2023-06-20
### Fixed
- Open loop drag force uncontrolled transient movement.

# [5.17.1] - 2023-05-31

## 2023-05-31
### Fixed
- Simplemotion communication issues by increasing bus timeout.

# [5.17.0] - 2023-04-28

## 2023-04-19
### Changed
- Improved movement performance by reducing amount of queries over bus.
- Improved performance of synchro tap, drag, swipe and pinch gestures.
- Note that the movement procedure of above-mentioned gestures is slightly different from before so this may have some effect on existing usage.

## 2023-03-17
### Changed
- Optomotion packaged was replaced by Pysimplemotion.
- Joint movement enforces movement to exactly the target position.
- Open loop drag force gesture supports a list of forces that are interpolated during movement.
- Open loop drag force gesture supports different force for the two synchro fingers.
### Removed
- Force feedback via scoping from force gestures.
- Fetching firmware version numbers for system information package.

## 2023-02-13
### Added
- Support for dual finger press gesture using differentiating forces for tips.

# [5.16.5] - 2023-04-20

## 2023-02-09
### Changed
- Revert Optofidelity Hikvision camera driver to previous version.

# [5.16.4] - 2023-02-09

## 2023-02-09
### Fixed
- Disabled Camera_Optocamera.close() method when camera vendor is Hikvision/Hikrobot.

# [5.16.3] - 2023-01-30

## 2023-01-30
### Fixed
- Fixed Hikvision backend not closing connection properly.

# [5.16.2] - 2022-11-30

## 2022-11-28
### Fixed
- Excessive speed limiting on synchro rotation before taking a screenshot.

## 2022-11-08
### Changed
- Renamed all instances of tntmini in codebase to tntserver.

## 2022-10-13
### Added
- Added TnTClient.icons() method for getting list of icon resources.

## 2022-09-30
### Added
- Configurable parameter `no_contact_force_stabilization_time` for force actuator driver `opto_std_force`.

# [5.16.1] - 2022-09-26

## 2022-09-22
### Fixed
- Voicecoil drifting on repeated press gestures when using opto_std_force driver.

## 2022-09-21
### Fixed
- Compatibility issue with AlliedVision Alvium camera.

# [5.16.0] - 2022-09-08

## 2022-08-18
### Added
- Log message showing color comparison method for icon detection.
- Added duration parameter to Camera.screenshot().

## 2022-08-11
### Removed
- Several unused modules from the source code repository.

## 2022-08-09
### Added
- Halcon parameters scale_min, scale_max, angle_start and angle_extent in the configuration. These are used when teaching and detecting icons.
- Halcon parameters scale_step and angle_step. Can also be set to "auto". These are used when teaching icons.

# [5.15.0] - 2022-06-29

## 2022-06-14
### Added
- Resolution property added to DUT. If set, screenshots and video are mapped to the native resolution of the display.

# [5.14.0] - 2022-06-14

## 2022-06-13
### Added
- New parameter tool_name for surface probing API to enable probing surface with either finger of the synchro tool.

## 2022-06-07
### Fixed
- Error handling with camera stream via optocamera.

## 2022-05-17
### Added
- Added optional duration parameter to DUT.get_still() and Camera.get_still(). If set, video will be recorded for duration and per-pixel maximum taken over video frames.

## 2022-05-16
### Fixed
- Icon detection failing to detect large icons.

## 2022-05-10
### Changed
- Default console log level changed from debug to info.
- Simplified motion logging.
### Fixed
- Axis configs are restored when homing also after initialization.
- Axis configs are not restored if robot is not homed at init.

# [5.13.0] - 2022-05-18

## 2022-05-06
### Fixed
- Moving camera e.g. when taking a screenshot in case there are multiple cameras that use the same mount point.

## 2022-05-05
### Added
- New icon color detection method "quantized".

## 2022-04-22
### Fixed
- Fixed crash when trying to edit DUT in simulator with visual-simulation=false flag.

## 2022-04-01
### Added
- Added BlinkDetector analyzer for detecting the blinking frequency from a sequence of video frames.
- Added record_video() method to Dut and Camera nodes for recording a video clip.
- Dut.post_find_objects() now takes a duration parameter. If set, video is recorded and objects are searched from per-pixel maximum image.

# [5.12.0] - 2022-04-20

## 2022-04-22
### Fixed
- Tip-tool relation was not preserved in config file.

## 2022-04-14
### Changed
- Added tool_name parameter to robot.detach_tip().
- robot.change_tip() ignores finger_id parameter in case robot has only one tool.

## 2022-04-12
### Fixed
- Smart tool / tip manager initialization error if memory chip is not connected. Requires Optomotion FW >= 0.4.102.

## 2022-04-08
### Fixed
- Fixed log messages not showing with old logging configs.

## 2022-03-28
### Added
- Support for generic 6-DOF error model calibration. Configuration file section under robot `calibration_data:` should 
  have key `generic_error_model:` with an appropriate `coefficients:` dictionary.

## 2022-02-24
### Added
- Smart tool support.

## 2022-01-28
### Changed
- Moved stylus calibration camera implementation to TnT Server.

## 2022-01-25
### Added
- API for attaching and detaching Tool objects.
- STAFF robot tool changing simulation.
### Changed
- Tip changing movements use active tool in motion planning. This affects behavior if non-identity tool is attached.

# [5.11.1] - 2022-01-25

## 2022-01-21
### Fixed
- Fixed path traversal vulnerability in fileserver.

## 2022-01-14
### Changed
- Updated STAFF simulation model to match the latest design.

## 2022-01-12
### Added
- Stylus specific settings to burning test.
### Changed
- Improved API tests.

# [5.11.0] - 2021-12-14

## 2021-12-13
### Changed
- Migrated to Python 3.7.

## 2021-12-08
### Fixed
- Fixed bug of HSUP camera not being triggered correctly on finger touch start and touch end.

# [5.10.0] - 2021-11-16

## 2021-12-09
### Fixed
- Flexture force press gesture limits minimum press duration to avoid an issue with the controller. 

## 2021-12-07
### Fixed
- Flexure force calibration sequence now returns robot back to correct starting position.

## 2021-12-2
### Added
- A new parameter 'voicecoil_probing_current' for surface probing. Setting a low value allows using the probing functionality also on the stylus robot.

## 2021-11-24
### Changed
- Improved force calibration data usage with piecewise linear interpolation instead of one straight-line approximation.

## 2021-11-10
### Changed
- Improved DH model IK performance. At the moment improves STAFF robot motion performance.
- Reduced the number of position queries in motion planning. Improves motion performance of most robots.

## 2021-11-09
### Changed
- Improved smart tip read performance. Requires Optomotion firmware version >= 0.4.93.

# [5.9.0] - 2021-10-13

## 2021-10-12
### Changed
- Installer no longer includes HASP and Pylon drivers. They are installed separately once during delivery setup.

## 2021-10-11
### Fixed
- Jump gesture and dut.screenshot() did not check if DUT orientation is valid which could cause collision.

# [5.8.0] - 2021-09-30

## 2021-09-27
### Changed
- Added parameter return_to_start with default value True to surface probe method probe_z_surface().

## 2021-09-20
### Fixed
- Icon color comparison via template matching triggered OpenCV assertion in case target image was smaller than template.

## 2021-09-07
### Added
- Futek API for buffering force values in server side.

# [5.7.0] - 2021-08-17

## 2021-08-11
### Fixed
- Optostandard force calibration measurement windowing produced incorrect results. This was caused by recent force code reordering.
### Added
- Force calibrator arguments force_threshold, max_rel_variation and max_abs_variation to control force windowing.

## 2021-08-09
### Changed
- Trigger sensor can be configured for all robots instead of just Synchro robot.

## 2021-08-04
### Added
- Robot API for getting joint limits, joint status and enabling/disabling joints.

## 2021-08-03
### Changed
- Added "press_depth" parameter to TnT.Gestures press() method to be compatible with Synchro.Gestures press().

# [5.6.0] - 2021-06-30

## 2021-06-30
### Changed
- Possibility to use partial DH parameter set as STAFF kinematic model calibration.

## 2021-06-29
### Fixed
- Axis enable not working with Optomotion 1.8.3

## 2021-05-25
### Added
- Flexure force driver.
### Changed
- Unified force calibration API by changing "active_voice_coil" parameter to "axis_name".

# [5.5.0] - 2021-06-21

## 2021-06-22
### Fixed
- Camera image streaming occasionally failed when using optocamera-basler driver.
- Camera image stream contained image with incorrect exposure and gain if still image was taken during streaming.

## 2021-05-21
### Added
- optocamera-basler driver. A driver class that mimics yasler API. Should be drivername only change in config.

# [5.4.1] - 2021-06-17

## 2021-06-14
### Fixed
- Voicecoil swipe gesture could not be performed with non-zero tilt or too large radius. Use TnT gesture in those cases.

## 2021-06-02
### Changed
- Compare name and all properties read from smart tip against currently attached TnT tip resource.
### Added
- Smart tips can be initialized in "hot_changing" mode where SW status automatically updates according to smart tip HW status.

## 2021-05-26
### Fixed
- Kinematic xyza_vc_stylus tool calibration result was in wrong coordinate frame. 

## 2021-05-14
### Fixed
- Kinematics used setpoints without applying AP model compensation.

## 2021-05-03
### Fixed
- xyza_vc_stylus kinematics was missing tilt slider offset value in IK and FK.

## 2021-04-26
### Added
- An additional move to robot initialization: orientation after homing will be identity (matrix).

## 2021-04-23
### Changed
- Stylus / pencil kinematics parameters 'sr_link_length' and 'stylus_mount_angle' can now be configured through the 
robot 'calibration_data' properties

# [5.4.0] - 2021-04-21

## 2021-04-20
### Fixed
- Yasler raised exception if some attribute e.g. gain_max was not available.

## 2021-03-25
### Added
- Check for unrealistic rotation when performing movement context transformation to robot coordinates.

## 2021-03-19
### Added
- Support for joint level calibration usage in robot kinematics. Actual model implementation is from the fik library
  axis perturbation (APModel) class.

## 2021-03-15
### Added
- Support for multiple workspaces and possibility to control multiple robots simultaneously.
### Changed
- In configuration file parent and connection values are now full paths from root. The old shorthand names are still supported when config is loaded but once config is saved, full paths are used.

## 2021-02-26
### Changed
- Move force axis smoothly to original position in Optostandard force gestures.
- Force tare parameters are now configurable.
### Fixed
- Drag force gesture with Optostandard force.

## 2021-02-23
### Added
- Kinematics for stylus holder with linear sliding tilt mechanism.
### Changed
- Calibration computation code for stylus offset and synchro offset was moved to TnT GT server.

## 2021-02-12
### Changed
- Robot force is now determined by "force_driver" argument which can be "open_loop_force" or "opto_std_force". Synchro uses by default "open_loop_force". This argument must be added to config if force is used.
- When updating software to system that has optostandard force, following Robot node arguments must be moved inside "force_parameters" argument dict: "voicecoil_name", "press_start_height", "voicecoil_speed", "voicecoil_acceleration", "min_force", "max_force", "force_touch_probing_velocity", "force_touch_probing_threshold", "force_touch_probing_acceleration", "force_calibration_window_size", "no_contact_force_threshold".
- Force parameter "max_no_contact_force" (in milligrams) was renamed to "no_contact_force_threshold" (in grams similar to min_force and max_force).
- Robot API move_joint_position() now waits for motion to be complete and accepts speed and acceleration parameters.

## 2021-02-08
### Fixed
- Pyfutek didn't work with all date formats. Fixed by only using the necessary value returned from futek fast_data_request, thus removing the need to deal with dates.

## 2021-01-22
### Changed
- Faster Halcon icon detection in separate process. Multiprocessing is used by default.

## 2021-01-13
### Added
- Image resize function
### Fixed
- Halcon crashes when user gives path to existing file which is not an SHM file.
- Use separate process when teaching Halcon icons to avoid crash in case of any error.
- Optionally run Halcon icon detection in separate process. See Halcon node config.

## 2021-01-04
### Added
- Smart tip support to make sure correct tip is physically attached to robot before motion in executed.

## 2020-12-17
### Added
- Batch script for automatic client generation.

# [5.3.0] - 2020-12-17

## 2020-12-16
### Added
- Homing sequence for hbot where both x and y motors are homed simultaneously to homing switches.

## 2020-12-10
### Changed
- All screenshot images are saved as uncompressed png instead of numpy array. However, older system with numpy array images are still supported. 
- Debug_images parameter is obsolete.
### Fixed
- Image node now returns a png image when one is requested (returned earlier jpg because of a bug).

## 2020-11-30
### Added
- Simulator for hbot robot.
### Fixed
- Robot position limit check used the effector position instead of tool mount position when workspace limits were specified in config file.

## 2020-11-19
### Added
- Possibility to move robot away from static camera view when capturing image.

## 2020-11-17
### Added
- Homing sequence for hbot kinematics where axes can be disabled and homing switch selected.
- Hbot z-axis current limits can be configured for homing to get more reliable hard-stop detection.
- Example for using a futek client.
### Changed
- Hbot kinematics can be also used without z-axis.
### Fixed
- In images node max_images and debug_images parameters were initialized in wrong place.
- Futek client now works as it should
- Made sure that temporary files are removed.
- More robust configuration backup file time stamp parsing.

## 2020-11-16
### Added
- Voice coil maximum position is fetched from the robot for synchro and voicecoil robots.
### Changed
- Specified Toolbox to use version 0.2.19

## 2020-11-10
### Fixed
- When creating nodes from existing images, wrong path was being used. Image node creation moved to place where the 
configured path can be used.

## 2020-11-06
### Added
- Possibility to choose camera for dut.search_text and dut.find_objects.
### Changed
- "" will now search everything in text detection.

## 2020-11-05
### Fixed
- Open loop force validation was not done properly. For example when there was supposed to be 7 validation points, only
6 was measured. This is now fixed.

## 2020-11-04 
### Changed
- When server is started backup filename has word init in it to separate it from the ones created during the run.
- Backups are created on the run if the latest backup is more than 5 minutes old.
### Fixed
- User manual had bad characters and styling problems.

## 2020-10-29
### Changed
- Camera parameter "ip" causes warning as the correct parameter is "ip_address".

## 2020-10-23
### Added
- DUTs Icon and OCR detection return screenshot name.
### Changed
- Improved API tests

## 2020-10-19
### Changed
- Synchro robot surface probe uses both voicecoils in case multifinger tip is attached.

## 2020-10-16
### Fixed
- Reverted refactoring of synchro separation kinematics which caused incorrect motion planning when using gripping.

## 2020-10-13
### Added
- Camera retries image capture in case of random camera error. Retry count is controlled by camera node argument "retry_count".
### Changed
- MJPEG streaming does not stop in case of capture error. This should be more robust in practice.
### Fixed
- Taking still image (during OCR or icon detection) while camera is streaming images often caused some image capture error.

## 2020-10-07
### Added
- Script for collecting configurations and other system information from configuration folders, FTP and from Optomotion.
- Trajectory time scaling to prevent axis velocity and acceleration violations during motion.
  By default this is not used. To use scaling, add "max_velocity" and "max_acceleration" keys to axis specs in robot config.
### Changed
- Robot velocity is by default clamped to 250 mm/s and acceleration is clamped to 100000 mm/s^2 when set via configuration or API.

## 2020-10-05
### Changed
- Configuration file is used via FTP in case local file is not found or specified. See user manual for command-line options.

## 2020-09-25
### Changed
- Basler camera parameters are now written in specific order as there are interdependent parameters. This should reduce random errors when setting parameters.

## 2020-09-28
### Fixed
- Surface probe determined incorrect position for 3-axis-voicecoil robot. This caused collision risk when using surface probing for e.g. DUT positioning.
- 3-axis-voicecoil gestures performed watchdog tap incorrectly using voicecoil for z-movement.

## 2020-09-23
### Added
- Generic rename method (put_name) for Node class.
### Removed
- put_name method removed from tip class.

## 2020-09-16
### Changed
- Upgraded ruamel.yaml to version 0.16.12 to fix build issue. May have some effect on config saving and loading. Make sure existing config has backup before using this version.

## 2020-08-31
### Fixed
- Voicecoil robot was using too high speed and acceleration when zeroing voicecoil after gesture. This fixes specifically clatter noise after swipe gesture on tilted DUT.

## 2020-08-27
### Added
- Robot API get_finger_separation_limits() for synchro and two-finger-dt robots.
### Fixed
- Two-finger-dt API put_finger_separation() was missing kinematic_name parameter.

## 2020-08-26
### Added
- Robot arguments "max_tip_change_speed" and "max_tip_change_acceleration" to be able to configure these for different robots.
### Changed
- Default tip change speed was changed from 150 mm / s to 100 mm / s to cope with speed limitation of 120 mm / s of the z axis used with VC robots.

## 2020-08-25
### Changed
- Kinematics xyza_voicecoil defines "voicecoil1" kinematics. Tap, double tap and swipe now use VC for z movement when using Voicecoil.Gestures with this kinematics.
  NOTE: If existing tips have voicecoil parameter defined, they must be repositioned due to VC kinematics change. Otherwise there is risk of collision.
### Fixed
- Voicecoil gesture double_tap() interval was not used (duration was mistakenly used as interval).

## 2020-08-24
### Changed
- Tip changing movements will first move over slot-out position even when picking tip. User can then set slot-out position farther away from slot-in to get extra safety in case tip is exceptionally tall.
- Tip changing movements use lower speed for azimuth rotation to avoid exceeding axis speed limits. Azimuth rotation is now done at safe rotation position instead of during movement over slot-position.

## 2020-08-18
### Added
- Scaling for DUT SVGs.
### Changed
- Use buffered motion instead of move_absolute() to move voicecoils when picking and dropping multifinger. This should fix motion issue noticed with one robot.

## 2020-08-17
### Added
- Robot parameters "home_axes" and "restore_axis_configs".
### Changed
- Goldenmov robots now by default restore axis configurations from non-volatile memory before homing.

## 2020-08-14
### Added
- Robot argument "separation_gripping_mode" which can be either "position" (for position controlled gripping) or "torque" (for torque controlled gripping).
- Robot argument "separation_gripping_torque_setpoint" to specify the torque setpoint during gripping.
### Changed
- Replaced robot argument "separation_gripping_current" by "continuous_separation_gripping_current" and "peak_separation_gripping_current" to be able to specify both values.
- Removed robot arguments "default_separation_continuous_torque_limit", "default_separation_position_tracking_error_threshold", "default_separation_velocity_tracking_error_threshold". Drive card values are used instead.

## 2020-08-11
### Added
- Parameter "kinematic_name" to synchro tap gesture.
- 2-finger-dt gestures class to implement "tool_name" and "kinematic_name" parameters for tap gesture similar to synchro tap.
### Changed
- Default value of "tool_name" was changed from "tool1" to None for synchro gestures. This has no effect on existing use cases as None is interpreted as "tool1". This is to be compatible with e.g, one-finger robot where such parameter is absent.
### Fixed
- Insufficient check for zero-length swipe gesture to avoid corrupted trajectory planning.

## 2020-08-04
### Added
- Videosensor triggering threshold can be set in configuration file.
- Gripping distance can be set in config file.

## 2020-07-09
### Added
- Configurable current for voicecoils in homing
### Changed
- Hard coded values given in INIT_CURRENT, VOICE_COIL_MAX_CONT_TORQUE_CURRENT come now from configuration

## 2020-07-01
### Added
- Configurable current for separation axis when gripping

## 2020-06-29
### Added
- Position limit checking after homing for voice coils on synchro robots.
- Configuration backup functionality
- Possibility to use either one or both fingers in circle, drag, multiswipe, path, press and drag_force synchro gestures. 2-finger force usage requires calibration data for voicecoil2 in config.

## 2020-06-24
### Fixed
- Ximea 64-bit libs missing in build

## 2020-06-22
### Added
- Added parameter touch_duration to touch_and_tap gesture.
- Added parameters delay and touch_duration to touch_and_drag gesture.
- Possibility to use either one or both fingers in tap, double_tap and swipe synchro gestures.
### Changed
- Fixed incorrect rapid motion when attempting to rotate synchro tool azimuth >= 180 degrees within one continuous motion.
### Removed
- Rocktomotion API. Use Optomotion instead.

## 2020-06-15
### Added
- mjpeg stream compatibility to Ximea driver

## 2020-06-01
### Added
- Watchdog tap to the Gestures base class
- Tesseract OCR engine available for text detection
- Tesseract OCR requires [tesserocr_dependencies.exe](https://jenkins-master.optofidelity.net/job/PUBLIC%20-%20tesserocr/) to be installed
### Changed
- default parameters for search_text changed
### Fixed
- handling None value in tnt_http.py

## 2020-05-05
### Added
- Image API for cropping, saving and inverting image. Image API to convert image to grayscale.
### Changed
- Dut search_text() and find_objects() check that detection results are within DUT limits.

## 2020-04-24
### Changed
- Cropping parameter 0 for crop_right and crop_lower is no longer allowed. Use None instead to use maximum values.

## 2020-04-17
### Changed
- Removed HSUP stop_measurement() from client config. Made HSUP results() blocking with an optional timeout. HSUP results() now internally calls _stop_measurement().

## 2020-04-16
### Added
- Image filtering API for Image node and Dut.search_text().

## 2020-03-19
### Added
- Image.search_text() and Image.find_objects().
### Changed
- Removed AbbyyLegacy and HalconLegacy detectors. Use Abbyy and Halcon instead. Need to remove them from existing config files.
- Deprecated Camera.detect_icon() and Camera.search_text().

## 2020-03-13
### Changed
- Changed icon API: Icons can be created and converted via TnT Client. Removed separate IconConverter node, which must be removed from the configuration file. Icons are no longer stored in config (existing icon nodes should be removed from config).

## 2020-03-11
### Added
- Possibility to rotate MJEPG stream to a DUT context

## 2020-03-06
### Changed
- Modified use of Halcon w.r.t. icon conversion to get simpler shape models. Also adjusted the way score works when finding icons.

## 2020-03-05
### Changed
- 2020-03-05: Added possibility to add and remove resources via client API. Added possibility to define image data via client API.

## 2020-02-19
### Added
- Added support for manually changing tips even if the slot in and slot out positions are stored

## 2020-02-17
### Changed
- Fixed moving of camera when target context (DUT) is rotated.

## 2020-02-07
### Changed
- Voicecoil robot has kinematics that is taking into account voicecoil movements + updated gestures (tap/swipe) that use voicecoil to avoid z-axis speed limitation

## 2020-01-10
### Changed
- Automatic TnT Client generation. From now on the generated client must be used with TnT Server. Old client is not compatible with the server. The generated client has following breaking changes that must be fixed for client users:
  - tnt_camera_client: get_mjpeg_stream_url() removed. See documenentation of start_continuous().
  - tnt_dut_client: Corner position getters now return dict {"x": x, "y": y, "z", z} instead of list [x, y, z].
  - tnt_dut_client: press_physical_button() removed.
  - tnt_microphone_client: Property latest_recording replaced by method get_latest_recording().
  - tnt_robot_client: change_tip() parameter tip must be a string (before also TnTTipClient was accepted).
  - General: With old client, None parameter in client was translated to default parameter in server. In case user has given explicit None value in client, this does not work correctly with generated client if the default value in server is something else than None (.e.g 0).
  - See client_differences.md for more information and rationale for changes.

## 2019-12-19
### Changed
- Fixed voicecoil drifting after repeated tap motion. Change happened at very low level in motion planning and can potentially affect all robot motion.

## 2019-11-27
### Changed
- Updated Optomotion from 1.6.1.14 to 1.7.0.1. The update fixed issues with uneven robot movements (simplemotion update)

## 2019-11-18
### Added
- Motherboard and motherboards nodes example configuration in configuration/simulation_3axis_voicecoil.yaml
- exposed generic set_device_parameter method from optomotion >= 1.6.1.14

## 2019-11-12
### Changed
- Updated Optomotion from 1.5.2.11 to 1.6.1.14. The update has many changes but should be compatible with current TnT Server.

## 2019-11-6
### Changed
- Dut node `find_objects` and `search_text` return coordinates in un-cropped DUT frame even if cropping is defined.
