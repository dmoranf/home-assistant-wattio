# Changelog

Under development !!

Join the conversation @ https://community.wattio.com/portal/community/topic/integrar-wattio-con-home-assistant

It seems that Wattio has shutted down the forums, so, feel free to send any comment or request using the issues of this repo!

## TODO

- Configuration via Config Flow
- Check security devices issues

## [0.2.13] - 2021-06-04

### Fixed

- Reuploaded fix for #9
- Minor fix: CONF_SECURITY_INTERVAL variable is optional again
- More verbosity for security debugging events

## [0.2.12] - 2021-06-03

### Changed

- Simple offset support based on #13 comments

## [0.2.11] - 2021-06-03

### Added

- Offset support for power sensors

### Fixed

- Security device status not getting current state from Wattio API (#9)

## [0.2.10] - 2021-05-19

Tested on HASS 2021.5.4

### Fixed

- #9 Fixed async errors on device status set commands on Hass >2021.4.3
- Restored debugging messages for security devices

### Changed

- Migrated all methors from requests to async aiohttp

## [0.2.9] - 2021-04-14

### Fixed

- #8 Fixed initial configuration notifications due to use of deprecated base_url

## [0.2.8] - 2021-01-20

### Added

- You can now skip adding some devices to HASS using sensor_exclude config entry

## [0.2.7] - 2021-01-13

### Fixed

- Time attribute of climate was not updating correctly (old file uploaded to the repo)

## [0.2.6] - 2021-01-11

### Added

- Consumption attribute added to switch entity. Leaving switch independent consumption sensor for backwards compatibility.
- HACS Support! Now you can install / upgrade this component via HACS :)

### Fixed

- Some console output (error leven) has been changed to its correct level.

## [0.2.5] - 2021-01-06

### Added

- Time attribute to thermic climate integration (seconds heating today)

## [0.2.4] - 2021-01-02

Sorry guys, long time since last update ...

### Added

- Device class added to binary sensors to make them available to HomeKit
- Climate HVAC_ACTION to show current state (Heating or OFF)

### Fixed

- Wrong behaviours on Climate, it seems that work better now ;)

### Changed

- Climate step set to 0.1, you can change it if you want editing climate.py

### Removed

- Removed dynamic vars of max temp and min temp for climate since they were not working as expected. (It will be added again in the future ...)

## [0.2.3] - 2019-10-04

### Fixed

- Managed exception when Wattio API responds with an error 500
- Device Availability was broken in 0.2.2
- Status update change was not showing in interface in 0.2.2
- Siren switch status on preAlarm

### Added

- Siren binary sensor for Pre Alarm state
- Siren switch sensor for making it sound or stop. (Panic button)
- Motion and Door security state support.
- Security separate poll interval

Configuration.yaml example:

```yaml
wattio:
  scan_interval: 60 (OPTIONAL: time in seconds, defaults to 30)
  therm_max_temp: 30 (OPTIONAL: Max temp for climate component, defaults to 30)
  therm_min_temp: 10 (OPTIONAL: Min temp for climate component, defaults to 10)
  security: True (OPTIONAL: Enable security switches, defaults to False)
  security_interval: 60 (OPTIONAL: time in seconds, defaults to scan_interval)
```

### Changed

- Some icons changed
- Black code formatting

## [0.2.2] - 2019-09-20

### Fixed

- #1 redirect_uri was hardcode on authorization process

## [0.2.1] - 2019-09-01

### Fixed

- Climate implementantion on Hass >= 0.96 has changed and it's not backward compatible, new climate.py is compatible on HASS >= 0.96
- There is a copy of backward compatible climate.py (climate.py.pre_096) for HASS >= 0.92 and < 0.96

## [0.2.0] - 2019-09-01

### Added

- Support for Wattio Thermic. Need extra testing on winter time ;)
- Battery status for supported devices

### Changed

- Full Code changed to platform and async methods, only one API request for all devices
- Pod device changed from Light to Switch. Support for power consumption at entity
- Code cleanup and optimization

### IMPORTANT UPGRADE INFO

No need to change wattio.conf or re-authorize the app, but **the way the platform is configured HAS CHANGED**.

New configuration.yaml example:

```yaml
wattio:
  scan_interval: 60 (OPTIONAL: time in seconds, defaults to 30)
  therm_max_temp: 30 (OPTIONAL: Max temp for climate component, defaults to 30)
  therm_min_temp: 10 (OPTIONAL: Min temp for climate component, defaults to 10)
```

## [0.1.2] - 2019-06-05

### Added

- Support for Motion's presence sensor

### Changed

- Better code formatting and linting

## [0.1.1] - 2019-05-31

### Added

- Support for Wattio PODs
- POD state detection (Available / Not available)
- Support for Wattio Doors

### Changed

- Some interface messages changes. (First setup)
- Better debugging/error log messages.
- Some code moved to **init**.py for reutilization in multiple components.

### Fixed

- Some excepcion handling (work pending in progress ...)

## [0.1.0] - 2019-05-26

### Added

- Initial configuracion information from Hass Interface.
- Wattio Oauth2 API authorization throught Hass Interface.
- Sensor discovery and configuration for BATs, PODs (Power consumption), Thermics and Motion (Temp only).
- One API request query for all sensors
