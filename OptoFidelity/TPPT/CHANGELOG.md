# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

# [5.9.0] - 2023-03-27

## 2023-03-15
### Fixed
- Robot azimuth and tilt angles being saved as zero even when they are disabled in config.

## 2023-03-10
### Added
- Parameters 'maxdiagoffset' and 'maxdiagjitter' to settings.

## 2023-02-27
### Added
- Parameter 'minavgreportingrate' to settings

## 2023-02-24
### Changed
- Improved touch driver documentation.

## 2023-02-23
### Added
- Added 'name' and 'dut' columns to 'settings' table in database to allow saving dut-specific settings. The primary key
  'id' is now just an integer. This breaks compatibility with old databases.

## 2023-02-10
### Changed
- Drawing speed variable input to support multiple swipe speeds
### Added
- Support for multiple speed tests within test sequence
- Speed parameter to TestItem class

## 2023-02-03
### Added
- Support for results database path name variable use.

## 2022-09-28
### Changed
- Moved grid visualization code to TPPTcommon.visualization module.

## 2022-06-02
### Added
- Added 'Tool' control in ADB driver for selecting which tool to use for getting input events from device.
- Added support for 'getevent' tool in ADB driver.

# [5.8.0] - 2022-04-19

## 2022-04-20
### Added
- Clearance parameter for all one finger tests.
### Changed
- Default clearance values to -0.1 to be safe with STAFF robot.
### Fixed
- Fixed ADB driver not working with multiple ADB devices attached to PC. Now you can select which device to use.

## 2022-04-01
### Added
- Added ADB touch driver for DUT.

## 2022-02-09
### Added
- Possibility to test with varying angles using a stylus robot. This is enabled by setting parameters "tilt_angles" and "azimuth_angles" in config.json. This applies to tap, swipe, stationary jitter and repeatability tests.
### Changed
- Database now stores the azimuth and tilt data from tests. This breaks compatibility with existing databases.

## 2022-02-04
### Fixed
- Fixed tool checking in scripts. Tests now work with STAFF that has changable tools.

# [5.7.0] - 2021-12-14

## 2021-12-14
### Changed
- Migrated to Python 3.7.

# [5.6.0] - 2021-11-12

## 2021-11-12
### Added
- Measurement drivers can define custom controls that are visible in UI.

# [5.5.2] - 2021-11-05

## 2021-11-05
### Fixed
- Removed unnecessary event OK check from tap test that caused issues with some PIT drivers.

# [5.5.1] - 2021-10-13

## 2021-10-07
### Fixed
- PIT driver passes non-OK events in tap-like tests.

# [5.5.0] - 2021-09-17

## 2021-08-03
### Added
- Possibility to use force gestures to perform one finger tests.

# [5.4.0] - 2021-04-21

## 2021-03-31
### Added
- Possibility to use grid file in each test where random points are used by default.
### Changed
- Grid file parameters and PIT driver parameters are only shown when they are relevant.
- DUT resolution is only shown if not fetching resolution automatically.

# [5.3.0] - 2020-12-17

## 2020-09-16
### Added
- Dummy driver visibility is now configurable also a message is issued if dummy driver is used.

## 2020-09-16
### Changed
- Separation test parameters are now more configurable. Separation limits are queried from server.

## 2020-09-11
### Fixed
- Bug that prevented tests to work if PIT was disabled -> if PIT is disabled pit slot id written in database is 0.

## 2020-09-10
### Added
- Tooltips for test configs.

## 2020-09-07
### Fixed
- Correct coordinates sent to UI when axes are flipped.

## 2020-08-26
### Changed
- Default speed from 200 mm/s to 100 mm/s. This is better because VC robot z axis speed is limited to 120 mm/s.

## 2020-08-12
### Fixed
- Separation test used incorrect separation with synchro robot.

## 2020-07-07
### Added
- Expected points for events are calculated and sent to UI.

## 2020-07-01
### Added
- Functionality to fetch resolution automatically from PIT and from Dummy driver
### Changed
- Fetching resolution automatically from TCP socket changed to correspond with the PIT and Dummy versions

## 2020-06-26
### Changed
- TCP socked based touch measurements apply timeout after gesture has completed.
- Configurable measurement timeout values.

## 2020-06-22
### Removed
- Burning test and related code. Currently burning test is maintained in TnT Server.

## 2020-06-16
### Added
- Edge offset parameter to random point grid generation and following one finger tests: first contact latency, repeatability, stationary jitter, stationary reporting rate

## 2020-05-28
### Changed
- Fixes to PIT TEPA and Cypress drivers to make touch events work correctly in all one-finger test cases.

## 2020-05-20
### Changed
- First contact latency to show measurement feedback in UI.
## 2020-04-28
### Added
- One finger tests support for SVG shapes of DUTs

## 2020-04-15
### Added
- The visibility of PIT controls in DUT settings is now configurable, config.json needs to be updated if one wants to use PIT.
### Changed
- Moved PIT driver to new plugin architecture

## 2020-03-31
### Changed
- Moved Dummy and TCP drivers to new plugin architecture. Plugin init function fingerprint changed (**kwargs added for flexibility)

## 2020-03-11
### Changed
- Exposed swipe radius and clearance values as test controls.

## 2020-02-06
### Added
- Possibility to use additional DUT drivers as plugins

## 2020-01-16
### Changed
- Switch to use automatically generated TnT Client. Needed to change TipNode usage of change_tip() to pass tip name as argument instead of tip client object.
- Changed one finger swipe test hardcoded clearance to -0.5 (from 0).
- Changed set_robot_dut_change_speed from hardcoded 250 to 100.
### Added
- Edge offset and possibility to use drag instead of swipe in NonStationaryReportingRate.

