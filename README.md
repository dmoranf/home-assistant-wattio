# Wattio Smart Home

[![GitHub Release](https://img.shields.io/github/release/dmoranf/home-assistant-wattio.svg?style=for-the-badge)](https://github.com/dmoranf/home-assistant-wattio/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/github/license/dmoranf/home-assistant-wattio.svg?style=for-the-badge)](https://github.com/dmoranf/home-assistant-wattio/LICENSE)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/dmoranf/home-assistant-wattio?style=for-the-badge)](https://github.com/dmoranf/home-assistant-wattio/commits/main)

Wattio Smart Home platform integration for Home Assistant throught Wattio's API. This component is _under development_.

<p align="center">
<img src="https://raw.githubusercontent.com/dmoranf/home-assistant-wattio/main/_screenshots/wattio_integration.png" width="500px"></p>

Currently Supported Devices: **Bat, Thermic, Motion, Door, Pod and Siren**

You can use this devices via _HomeKit_ using _Home Assistant's HomeKit bridge_ (Bat is not supported right now).

---

### Changelog

Please check [CHANGELOG.md](https://github.com/dmoranf/home-assistant-wattio/blob/main/custom_components/wattio/CHANGELOG.md) for full details.

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

---

### Installation

## Pre-Requisites

- Client ID and Secret for Wattio Platform (Request to wattio Support)
- Works on Home Assistant >= 0.90.2 (Tested up to 2021.1.1)

## HACS (Prefered)

- If you have previously installed this component manually, please remove it, but **keep your wattio.conf file** so you don't have to setup the platform again.
- Search for Wattio integration in HACS and install it.
- Follow adittional configuration steps.

## Manual Installation

- Copy "wattio" folder to your `<config dir>/custom_components/wattio` directory.
- Configure as shown below.
- Restart HASS.
- Follow the adittional configuration steps.

### Configuration

Add the following to your `configuration.yaml`.

> From version 0.2.0 the way of Wattio component is configured has been changed. If you are upgrading for a previous version you **MUST CHANGE YOUR CONFIG FILE**

```yaml
# Wattio Platform
wattio:
  scan_interval: 60
  security: true
  security_interval: 300
  sensor_exclude: ['ieee1']
```

Vars:

| Var                 | Description                                                                                     |
| ------------------- | ----------------------------------------------------------------------------------------------- |
| _scan_interval_     | OPTIONAL - Time (in seconds) between data updates , defaults to 30 seconds                      |
| _security_          | OPTIONAL - Enable or disable security devices, defaults to False                                |
| _security_interval_ | OPTIONAL - Time (in seconds) between security devices data updates, defaults to _scan_interval_ |
| _sensor_exclude_    | OPTIONAL - List with IEEEs to exclude, for example: ["ieee1","ieee2"]                           |

### Adittional steps

- At first launch a new notification is shown at the UI requesting the user to configure de user id and the secret.
- The configuration file "wattio.conf" is created automatically.
- Change user id and secret in "wattio-conf".

  > User id and secret MUST be supplied by wattio team (This is not your user and password!)

- After changing the configuration file, another notification should appear asking the user to authorize home assistant at wattio.
- Follow the link for authorization, a page requesting username and password from Wattio should be shown.
- Finally, close the notification and refresh your GUI.
- Once devices has been added to HASS, first data update will take place after the configured scan_interval.

<p align="center">
<img src="https://raw.githubusercontent.com/dmoranf/home-assistant-wattio/main/_screenshots/wattio_config.gif"></p>
