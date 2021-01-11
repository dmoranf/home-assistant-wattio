# Wattio Smart Home
[![GitHub Release](https://img.shields.io/github/release/dmoranf/home-assistant-wattio.svg?style=for-the-badge)](https://github.com/dmoranf/home-assistant-wattio/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/github/license/dmoranf/home-assistant-wattio.svg?style=for-the-badge)](https://github.com/dmoranf/home-assistant-wattio/LICENSE)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/dmoranf/home-assistant-wattio?style=for-the-badge)](https://github.com/dmoranf/home-assistant-wattio/commits/main)

Wattio Smart Home platform integration for Home Assistant throught Wattio's API. This component is under development, please check [CHANGELOG.md](https://github.com/dmoranf/home-assistant-wattio/blob/main/custom_components/wattio/CHANGELOG.md) for last updates.

[![Wattio SmartHome](https://brands.home-assistant.io/wattio/logo.png | width=50%)](https://wattio.com)

### Supported devices

This component currently supports:

- Bat
- Thermic
- Motion
- Door
- Pod
- Siren

### Important Info

Since Hass 0.96, the way climate devices work has been changed and it is NOT backward compatible. Default (included) climate.py works for HASS versions >= 0.96, but a file called climate.py_pre_096 is available (but not mantained) for use if you are using HASS between 0.92 and 0.96. Just make a backup of climate.py and rename climate.py_pre_096 to climate.py

### Screenshots

 - Wattio Sensors (Bat & Thermic examples):

<p align="center">
<img src="https://raw.githubusercontent.com/dmoranf/home-assistant-custom-components/master/_screenshots/wattio_bat_sensor.png" width="300px">   &nbsp;&nbsp;  <img src="https://raw.githubusercontent.com/dmoranf/home-assistant-custom-components/master/_screenshots/wattio_thermic_sensor.png" width="300px"></p>

- Wattio Binary Sensors (Door example):

<p align="center">
<img src="https://raw.githubusercontent.com/dmoranf/home-assistant-custom-components/master/_screenshots/wattio_door_sensor.png" width="300px"></p>

- Wattio Switch (Pod example):

<p align="center">
<img src="https://raw.githubusercontent.com/dmoranf/home-assistant-custom-components/master/_screenshots/wattio_pod_switch.png" width="300px"></p>

### Requisites

 - Client ID and Secret for Wattio Platform (Request to wattio Support)
 - Works on Home Assistant >= 0.90.2 (Tested on 0.98.2)

### Installation

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

  

