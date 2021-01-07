"""Platform for Wattio integration testing."""
import logging

try:
    from homeassistant.components.switch import SwitchEntity
except ImportError:
    from homeassistant.components.switch import SwitchDevice as SwitchEntity

from homeassistant.const import STATE_ON

from . import WattioDevice, wattioApi

from .const import DOMAIN, ICON, SECURITY, SWITCHES

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Wattio Sensor setup platform."""
    _LOGGER.debug("Wattio Switch component running ...")
    security_enabled = hass.data[DOMAIN]["security_enabled"]
    if discovery_info is None:
        _LOGGER.error("No Sensor(s) discovered")
        return
    devices = []
    # Create Updater Object
    for device in hass.data[DOMAIN]["devices"]:
        if device["type"] in SWITCHES:
            devices.append(
                WattioSwitch(
                    device["name"], device["type"], ICON[device["type"]], device["ieee"]
                )
            )
            _LOGGER.debug("Adding device: %s", device["name"])

        if device["type"] in SECURITY and security_enabled is True:
            devices.append(
                WattioSecurity(
                    device["name"], device["type"], ICON["security"], device["ieee"]
                )
            )
            _LOGGER.debug("Adding device: %s", device["name"])
    async_add_entities(devices)


class WattioSwitch(WattioDevice, SwitchEntity):
    """Representation of Switch Sensor."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, name, devtype, icon, ieee):
        """Initialize the sensor."""
        self._pre = "sw_"
        self._name = name
        self._state = False
        self._icon = icon
        self._ieee = ieee
        self._data = None
        self._devtype = devtype
        self._current_consumption = None
        self._available = 0

    @property
    def is_on(self):
        """Return is_on status."""
        return self._state

    async def async_turn_on(self):
        """Turn On method."""
        wattio = wattioApi(self.hass.data[DOMAIN]["token"])
        # Cambiar a debug
        _LOGGER.error(
            "Sending ON request to SWITCH device %s (%s)", self._ieee, self._name
        )
        wattio.set_switch_status(self._ieee, "on", self._devtype)
        self._state = True
        self.schedule_update_ha_state()

    async def async_turn_off(self):
        """Turn Off method."""
        wattio = wattioApi(self.hass.data[DOMAIN]["token"])
        # Cambiar a debug
        _LOGGER.error(
            "Sending OFF request to SWITCH device %s (%s)", self._ieee, self._name
        )
        wattio.set_switch_status(self._ieee, "off", self._devtype)
        self._state = False
        self.schedule_update_ha_state()

    @property
    def current_power_w(self):
        """Return current power consumption."""
        if self._devtype == "pod":
            return self._current_consumption
        return False

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the image of the sensor."""
        return self._icon

    @property
    def available(self):
        """Return availability."""
        _LOGGER.debug("Device %s - availability: %s", self._name, self._available)
        return True if self._available == 1 else False

    async def async_update(self):
        """Return sensor state."""
        self._data = self.hass.data[DOMAIN]["data"]
        _LOGGER.debug("ACTUALIZANDO SWITCH %s - %s", self._name, self._ieee)
        self._available = 0
        if self._data is not None:
            for device in self._data:
                if device["ieee"] == self._ieee:
                    self._available = 1
                    if self._devtype == "pod":
                        self._current_consumption = device["status"]["consumption"]
                        if device["status"]["state"] == 1:
                            self._state = STATE_ON
                        else:
                            self._state = False
                    elif self._devtype == "siren":
                        if device["status"]["alarm"] == 1 or device["status"]["preAlarm"] == 1:
                            self._state = STATE_ON
                        else:
                            self._state = False
                    break
            _LOGGER.debug(self._state)
            return self._state
        return False


class WattioSecurity(WattioDevice, SwitchEntity):
    """Representation of Security Sensor."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, name, devtype, icon, ieee):
        """Initialize the sensor."""
        self._pre = "sec_"
        self._name = "sec_" + name
        self._state = False
        self._icon = icon
        self._ieee = ieee
        self._data = None
        self._devtype = devtype
        self._available = 0

    @property
    def is_on(self):
        """Return is_on status."""
        return self._state

    async def async_turn_on(self):
        """Turn On method."""
        wattio = wattioApi(self.hass.data[DOMAIN]["token"])
        _LOGGER.debug(
            "Sending ON request to SECURITY device %s (%s)", self._ieee, self._name
        )
        wattio.set_security_device_status(self._devtype, self._ieee, "on")
        self._state = True
        self.schedule_update_ha_state()

    async def async_turn_off(self):
        """Turn Off method."""
        wattio = wattioApi(self.hass.data[DOMAIN]["token"])
        _LOGGER.debug(
            "Sending OFF request to SECURITY device %s (%s)", self._ieee, self._name
        )
        wattio.set_security_device_status(self._devtype, self._ieee, "off")
        self._state = False
        self.schedule_update_ha_state()

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the image of the sensor."""
        return self._icon

    @property
    def available(self):
        """Return availability."""
        _LOGGER.debug("Device %s - availability: %s", self._name, self._available)
        return True if self._available == 1 else False

    async def async_update(self):
        """Return sensor state."""
        self._data = self.hass.data[DOMAIN]["sec_" + self._ieee]
        if self._data is not None:
            self._available = 1
            if self._data == "true":
                self._state = STATE_ON
            else:
                self._state = False
        else:
            self._state = False
            self._available = 0
        return self._state
