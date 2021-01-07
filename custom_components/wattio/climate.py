"""Platform for Wattio integration testing."""
import logging

import homeassistant.helpers.config_validation as cv

try:
    from homeassistant.components.climate import ClimateEntity
except ImportError:
    from homeassistant.components.climate import ClimateDevice as ClimateEntity

from homeassistant.components.climate import PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_HEAT,
    HVAC_MODE_AUTO,
    HVAC_MODE_OFF,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_HEAT,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
)

from . import WattioDevice, wattioApi

from .const import (
    DOMAIN,
    CLIMATE,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    ICON
)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE

TARGET_TEMPERATURE_STEP = 0.1

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Wattio Sensor setup platform."""
    _LOGGER.debug("Wattio Climate component running ...")
    if discovery_info is None:
        _LOGGER.error("No Sensor(s) discovered")
        return
    devices = []
    # Create Updater Object
    for device in hass.data[DOMAIN]["devices"]:
        if device["type"] in CLIMATE:
            devices.append(
                WattioThermic(
                    device["name"],
                    device["type"],
                    ICON[device["type"]],
                    device["ieee"],
                    DEFAULT_MIN_TEMP,
                    DEFAULT_MAX_TEMP
                )
            )
            #_LOGGER.error("AQUI "+str(config.get(CONF_MIN_TEMP)))
            _LOGGER.debug("Adding device: %s", device["name"])
    async_add_entities(devices)


class WattioThermic(WattioDevice, ClimateEntity):
    """Representation of Sensor."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, name, devtype, icon, ieee, min_temp, max_temp):
        """Initialize the sensor."""
        self._pre = "cli_"
        self._name = name
        self._state = None
        self._icon = icon
        self._ieee = ieee
        self._devtype = devtype
        self._data = None
        self._operation_list = [HVAC_MODE_HEAT, HVAC_MODE_AUTO, HVAC_MODE_OFF]
        self._current_temperature = None
        self._current_operation_mode = None
        self._target_temperature = None
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._available = 0
        self._time = 0

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the image of the sensor."""
        return self._icon

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._max_temp

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def hvac_modes(self):
        """List of available operation modes."""
        return self._operation_list

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return current operation mode."""
        if self._current_operation_mode == 1:
            current_mode = HVAC_MODE_HEAT
        elif self._current_operation_mode == 2:
            current_mode = HVAC_MODE_AUTO
        else:
            current_mode = HVAC_MODE_OFF
        return current_mode

    @property
    def hvac_action(self):
        """Return current status."""
        if self._state == 0:
            return CURRENT_HVAC_OFF
        elif self._state == 1:
            return CURRENT_HVAC_HEAT
        else:
            return None

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        attrs = {"time": self._time}
        return attrs

    @property
    def target_temperature_step(self):
        return TARGET_TEMPERATURE_STEP

    async def async_set_temperature(self, **kwargs):
        """Set manual temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("Set target temperature to %s", temperature)
        wattio = wattioApi(self.hass.data[DOMAIN]["token"])
        wattio.set_thermic_temp(self._ieee, temperature)
        self._target_temperature = temperature
        self.schedule_update_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        _LOGGER.debug(hvac_mode)
        if hvac_mode == "auto":
            operation_value = 2
        elif hvac_mode == "heat":
            operation_value = 1
        else:
            operation_value = 0
        _LOGGER.debug("set operation mode to %s: %s", operation_value, hvac_mode)
        wattio = wattioApi(self.hass.data[DOMAIN]["token"])
        wattio.set_thermic_mode(self._ieee, operation_value)
        self._current_operation_mode = operation_value
        self.schedule_update_ha_state()

    @property
    def available(self):
        """Return availability."""
        _LOGGER.debug("Device %s - availability: %s", self._name, self._available)
        return True if self._available == 1 else False

    async def async_update(self):
        """Update sensor data."""
        self._data = self.hass.data[DOMAIN]["data"]
        _LOGGER.debug("ACTUALIZANDO CLIMATE %s - %s", self._name, self._ieee)
        if self._data is not None:
            self._available = 0
            for device in self._data:
                if device["ieee"] == self._ieee:
                    self._available = 1
                    _LOGGER.debug(device["status"])
                    tempvalue = device["status"]
                    self._current_temperature = tempvalue["current"]
                    self._current_operation_mode = tempvalue["mode"]
                    self._target_temperature = tempvalue["target"]
                    self._state = tempvalue["state"]
                    self._state = tempvalue["time"]
                    break
            return 0
        return False
