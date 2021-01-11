# Wattio Smart Home
[![GitHub Release](https://img.shields.io/github/release/dmoranf/home-assistant-wattio.svg?style=for-the-badge)](https://github.com/dmoranf/home-assistant-wattio/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/github/license/dmoranf/home-assistant-wattio.svg?style=for-the-badge)](https://github.com/dmoranf/home-assistant-wattio/LICENSE)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/dmoranf/home-assistant-wattio?style=for-the-badge)](https://github.com/dmoranf/home-assistant-wattio/commits/main)

Wattio Smart Home platform integration for Home Assistant throught Wattio's API. This component is *under development*. 

<p align="center">
<img src="https://raw.githubusercontent.com/dmoranf/home-assistant-wattio/main/_screenshots/wattio_integration.png" width="500px"></p>

Currently Supported Devices: **Bat, Thermic, Motion, Door, Pod and Siren**

---
### Changelog
Please check [CHANGELOG.md](https://github.com/dmoranf/home-assistant-wattio/blob/main/custom_components/wattio/CHANGELOG.md) for full details.

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
 - Works on Home Assistant >= 0.90.2 (Tested on 0.98.2)
 
## HACS (Prefered)

 - Since this repo is not added to HACS defaults repos yey, you hace to add it manually to HACS:
   - Go to any of the sections (integrations, frontend, automation).
   - Click on the 3 dots in the top right corner.
   - Select "Custom repositories"
   - Add the URL to the repository.
   - Select the correct category.
   - Click the "ADD" button.
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
```

Vars:

| Var | Description |
| --- | --- |
| *scan_interval* | OPTIONAL - Time (in seconds) between data updates , defaults to 30 seconds |
| *security* | OPTIONAL - Enable or disable security devices, defaults to False |
| *security_interval* | OPTIONAL - Time (in seconds) between security devices data updates, defaults to *scan_interval* |


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
<img src="https://raw.githubusercontent.com/dmoranf/home-assistant-custom-components/master/_screenshots/wattio_config.gif"></p>

  

