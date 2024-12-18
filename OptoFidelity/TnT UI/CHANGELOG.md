# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

# [5.18.0] - 2023-12-22

## 2023-11-23
### Added
- Checkbox for enabling and disabling voicecoil


# [5.17.0] - 2023-04-12

## 2023-02-23
### Added
- Ability to load and save a named TPPT script parameter set.

## 2023-02-03
### Added
- Ability to select results database name in TPPT scripts.

# [5.16.2] - 2022-11-30

## 2022-10-21
### Fixed
- Incorrect handling of "per" units in icon teaching and testing.

# [5.16.0] - 2022-09-08

## 2022-08-31
### Fixed
- Results image not showing when testing icons with a high resolution camera on some systems. The maximum image size
  shown can be configured by setting "max_image_size" under the "icon" section in start.yaml.

## 2022-08-18
### Fixed
- Fixed icons being reloaded from server when pressing test.
- Fixed icons, tips and tools being reloaded when opening the edit view.
- Fixed icon test button not using the duration parameter.

## 2020-08-10
### Removed
- Obsolete camera-based robot characterization and validation implementation.
### Added
- Refresh button for updating the robot control UI position and speed values in accordance to the robot.

# [5.15.0] - 2022-06-29

## 2022-06-23
### Added
- Crop box coordinates are shown in icon teaching view. The units can be chosen to be mm, pixels or percentage.
### Changed
- When testing icon detection the test area is cropped to the crop box, if it is enabled.

## 2022-06-22
### Added
- The contours image is shown in the icon editor.
- Absolute pose control tab in robot controls. Can be enabled by setting 'pose: true' in the config.
### Changed
- When adding a new icon the icon editor is now opened directly, allowing all the icon properties to be set right away.

## 2022-06-15
### Changed
- Camera exposure control to be limited by configurable max_exposure setting

## 2022-06-14
### Added
- DUT resolution can be set from Edit DUT menu. Can also be left blank if you don't want to set a resolution.

## 2022-05-25
### Added
- Ability to filter icons by name in icon teaching view.
### Fixed
- Icon view scroll position no longer resets after editing an icon.

# [5.14.0] - 2022-06-14

## 2022-06-13
### Fixed
- Surface probing with voicecoil 2 during force calibration.

## 2022-06-9
### Added
- Added feature for selecting both tools for synchro force calibration

## 2022-06-07
### Added
- Help for icon color settings.

## 2022-06-06
### Added
- Added step in wizard for setting synchro mechanism to 0 during finger offset calibration.

## 2022-05-24
### Added
- Score threshold, camera gain and exposure input fields to edit view of icon teaching

## 2022-05-17
### Added
- Added duration parameter to icon teaching view for teaching blinking icons.

## 2022-05-16
### Changed
- `Move to DUT` button in icon teaching view jumps to robot max height, then down to focus height instead of fixed 10 mm.

# [5.13.0] - 2022-05-18

## 2022-05-11
### Fixed
- Context drop-down menu now updates after adding or deleting a DUT

## 2022-05-05
### Added
- Icon color detection options.
### Fixed
- Icon teaching and testing with multiple cameras when using DUT context.

## 2022-05-02
### Fixed
- Fixed chess pattern dimensions being too far from target for certain inputs.

## 2022-04-22
### Added
- Automatic DUT positioning without using the Android application. The user can download the positioning pattern as an image and manually show it on the DUT.

# [5.12.0] - 2022-04-20

## 2022-04-19
### Changed
- Reprojection error acceptance limit in calibration view from 1.0 to 2.0 pixels.

## 2022-04-14
### Fixed
- Tips view was using hard coded tool names tool1 and tool2. Now uses tools available in server.

## 2022-03-14
### Added
- "Weight to current orientation" button in stylus calibration view. This allows the calculation of a more accurate tip offset for a specific orientation.
- Ability to copy tips in the tip editor.

## 2022-02-24
### Added
- Smart tool controls.

## 2022-02-17
### Added
- Regex validation for TPPT script controls where the "validate" field is defined.

## 2022-01-28
### Changed
- Moved stylus calibration camera implementation to TnT Server.

## 2022-01-25
### Changed
- Assign robot tool pose to tip slot positions instead of head pose. This changes behavior if non-identity tool is attached.

# [5.11.1] - 2022-01-25

## 2022-01-20
### Fixed
- Fixed wrong initial value for OCR detector.

# [5.11.0] - 2021-12-14

## 2021-12-13
### Changed
- Migrated to Python 3.7.

# [5.10.0] - 2021-12-08

## 2021-12-09
### Fixed
- Joint view did not work if there was an IO axis.

## 2021-12-07
### Fixed
- Force validation did not maintain current robot orientation in movements.

# [5.9.0] - 2021-10-13

## 2021-10-12
### Changed
- Installer no longer includes HASP and Pylon drivers. They are installed separately once during delivery setup.

# [5.8.0] - 2021-09-30

## 2021-09-27
### Added
- Tip property validation to prevent creating / editing tip with e.g. None length that causes issues in server.
- Robot control tab for using surface probing.
### Changed
- Separated camera focus height calibration into separate wizard for clarity.
- Improved instructions.

# [5.7.1] - 2021-10-04

## 2021-10-04
### Fixed
- Saving synchro finger offset calibration removed existing AP calibration.

# [5.7.0] - 2021-08-17

## 2021-08-09
### Added
- Show force slope value in force calibration results for adjusting the controller spring constant.
- New view "joints" for controlling individual robot joints.
- New view "rest" for issuing REST API commands.
### Changed
- View "extra" is now known as view "robot" and has robot error inspection in addition to homing.

# [5.6.0] - 2021-06-30

## 2021-06-29
### Changed
- Changes to force calibration view to make it work with flexure force.

# [5.5.0] - 2021-06-21


# [5.4.1] - 2021-06-14

## 2021-06-02
### Changed
- Configurable smart tip property list.

## 2021-05-10
### Added
- New configuration value z_step_confirm_threshold under ui section to show confirmation modal window if user moves z to negative direction by a large step.

## 2021-04-22
### Changed
- STAFF stylus calibration view improvements.

# [5.4.0] - 2021-04-21

## 2021-04-20
### Fixed
- After DUT edit or rename was finished another DUT was selected.
- Tip view raised error if "edit_smart_tip" was missing in config.

## 2021-03-31
### Added
- Possibility to hide script control visibility based on value of other controls.

## 2021-03-24
### Added
- Possibility to specify host address in network to operate UI from remote machine via browser.

## 2021-02-23
### Added
- A new view 'stylus' for stylus tool offset calibration
### Changed
- Calibration computation code for stylus offset and synchro offset was moved to TnT GT server.

## 2021-01-14
### Changed
- Improved help for DUT positioning.

## 2021-01-13
### Added
- Function for renaming icons.

## 2021-01-04
### Added
- A check to see if robot position is within DUT bounds. Jump to DUT if it is not.

## 2020-12-23
### Fixed
- UI freezes during tap tppt test if there is a lot of events (for example 100000 taps). Fixed by updating png image
instead of SVG.

# [5.3.0] - 2020-12-17

## 2020-11-05
### Fixed
- In icon teaching view and sequence generator camera context was not applied after camera was enabled by user.
- In sequence generator camera context and active DUT were reset during page change.

## 2020-11-03
### Added
- Surface probing for force calibration.
### Changed
- Camera controls were moved from Config page tab to new camera view overlay. They are thus now also visible in sequence generator.
- MJPEG stream is now used in all camera views.
- Refactored crop box usage in camera view.
### Fixed 
- Open loop force calibration had problems with instructions, logging and finding the correct position for the actions. These are now changed.

## 2020-10-30
### Added
- Ability to choose tesseract for OCR detection.

## 2020-10-22
### Fixed
- Recent change to add TPPT tooltips was not working with DoubleNumber input fields (such as DUT resolution) if they didn't have tooltip parameter.

## 2020-09-10
### Added
- Help button to Script-page.
- Handling for tooltips coming from the script.

## 2020-09-09
### Added
- Calibration target generator to camera view.

## 2020-09-23
### Changed
- Tip name change done with set_name method.

## 2020-08-28
### Fixed
- Recent change to TPPT script API add_dut_point() was not compatible with forked project TPPT scripts.

## 2020-08-28
### Added
- Resetting HSUP camera parameters before writing new values to avoid binning-resolution mismatches
- Better error handling in HSUP camera paremeter setting

# 2020-08-24
### Fixed
- Camera parameters not affecting stream camera views (e.g. in icon teaching view).

## 2020-08-27
### Added
- UI shows which page is selected.
  
## 2020-08-14
### Added
- Ability to stretch SVG denoting DUT's analysis area if the SVG size does not match the DUT size. Also a notification
  when the sizes don't match.

## 2020-08-04
### Changed
- Kinematic selector no longer affects active kinematic state in server. It only affects the motion executed via UI robot controls.
- Tip slot positioning now uses tool1 position regardless of active kinematic state in server side.

## 2020-07-07
### Added
- Expected points for events shown in UI.

## 2020-07-01
### Added
- Synchro finger calibration wizard help

## 2020-04-22
## Changed
- Sequence generator changes to HSUP page if sequence has "Get results" action.

## 2020-04-16
### Added
- Clearance and azimuth paramters for sequence generator tap and swipe actions.
- Tap type for tap action to support Watchdog tap.
### Fixed
- Sequence generator swipe was erroneously ran after first click on the camera image.

## 2020-03-24
### Added
- Button for using surface level z-probing in DUT autolocation view if the robot supports it

## 2020-03-11
### Changed
- Icon teaching view now uses MJPEG stream and new crop overlay

### Added
- Dragging crop overlay box from the box edges is now possible
- Added configuration option for icon teaching view image scaling factor

## 2020-02-28
### Changed
- Decreased default radius of Sequence Generator swipe from 10mm to 6mm to enable voicecoil swipes by default
- When UI starts, it no longer sets robot speed nor camera exposure and gain values.

## 2020-02-21
### Added
- Added control tab for voice coils
- Grippable property for multifinger tips
- Voice coil position for tips

## 2020-02-19
### Added
- Icon teaching view: Added possibility to crop icons from the rotated DUTs.

## 2020-02-19
### Added

## 2020-02-18
### Added
- added swipe to sequence generator
