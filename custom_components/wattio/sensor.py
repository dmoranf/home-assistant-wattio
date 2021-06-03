"""Platform for Wattio integration testing."""
import logging


from homeassistant.const import (
    ATTR_BATTERY_LEVEL
)
from homeassistant.helpers.entity import Entity


from . import WattioDevice

from .const import CONF_EXCLUSIONS, CONF_OFFSETS, DOMAIN, ICON, MEASUREMENT, SENSORS

_LOGGER = logging.getLogger(__name__)


def get_device_offset(offset, ieee, name):
    for value in offset:
        if value["sensor_ieee"] == ieee and value["sensor_name"].lower() == name.lower():
            _LOGGER.debug("OFFSET of type %s and value %s configured for %s - %s", str(
                value["offset_type"]), str(value["sensor_offset"]), str(ieee), str(name))
            offsettype = value["offset_type"]
            offsetvalue = value["sensor_offset"]
            return [offsettype, offsetvalue]
    return None


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Wattio Sensor setup platform."""
    _LOGGER.debug("Wattio Sensor component running ...")
    if discovery_info is None:
        _LOGGER.error("No Sensor(s) discovered")
        return
    devices = []
    for device in hass.data[DOMAIN]["devices"]:
        if device["type"] in SENSORS:
            if device["type"] == "bat":
                channel = device["channel"]
            else:
                channel = None
            if device["ieee"] in hass.data[DOMAIN][CONF_EXCLUSIONS]:
                _LOGGER.error("Excluding device with IEEE %s",
                              hass.data[DOMAIN][CONF_EXCLUSIONS])
            else:
                offset = None
                if hass.data[DOMAIN][CONF_OFFSETS]:
                    _LOGGER.debug("OFFSETs configured")
                    offset = get_device_offset(
                        hass.data[DOMAIN][CONF_OFFSETS], device["ieee"], device["name"])
                else:
                    _LOGGER.debug("No OFFSETS configured")
                devices.append(
                    WattioSensor(
                        device["name"],
                        device["type"],
                        MEASUREMENT[device["type"]],
                        ICON[device["type"]],
                        device["ieee"],
                        offset,
                        channel
                    )
                )
                _LOGGER.debug("Adding device: %s", device["name"])

    async_add_entities(devices)


class WattioSensor(WattioDevice, Entity):
    """Representation of Sensor."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, name, devtype, measurement, icon, ieee, offset, channel=None):
        """Initialize the sensor."""
        self._pre = "s_"
        self._name = name
        self._state = None
        self._measurement = measurement
        self._icon = icon
        self._ieee = ieee
        self._devtype = devtype
        self._channel = None
        self._battery = None
        self._data = None
        self._available = 0
        self._offsetvalue = None
        self._offsettype = None

        if offset is not None:
            self._offsetvalue = offset[1]
            self._offsettype = offset[0]
        if channel is not None:
            self._channel = channel - 1

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def available(self):
        """Return availability."""
        _LOGGER.debug("Device %s - availability: %s",
                      self._name, self._available)
        return True if self._available == 1 else False

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._measurement

    @property
    def icon(self):
        """Return the image of the sensor."""
        return self._icon

    @property
    def state(self):
        """Return sensor state."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {}
        if self._battery is not None:
            attr[ATTR_BATTERY_LEVEL] = self.get_battery_level()
        return attr

    def get_battery_level(self):
        """Return device battery level."""
        if self._battery is not None:
            battery_level = round((self._battery * 100) / 4)
            return battery_level
        return False

    def get_calculated_sensorvalue(self, sensorvalue):
        originalvalue = sensorvalue
        if self._offsettype == 1 and sensorvalue == self._offsetvalue:
            sensorvalue = 0
        elif self._offsettype == 2 and sensorvalue >= self._offsetvalue:
            sensorvalue = sensorvalue - self._offsetvalue
        _LOGGER.debug("Original sensor value: %s - Offset sensor value: %s",
                      str(originalvalue), str(sensorvalue))
        return sensorvalue

    async def async_update(self):
        """Update sensor data."""
        self._data = self.hass.data[DOMAIN]["data"]
        _LOGGER.debug("ACTUALIZANDO SENSOR %s - %s", self._name, self._ieee)
        if self._data is not None:
            self._available = 0
            for device in self._data:
                if device["ieee"] == self._ieee:
                    self._available = 1
                    if self._channel is not None and self._devtype == "bat":
                        sensorvalue = device["status"]["consumption"][self._channel]
                        if self._offsetvalue is not None and self._offsettype is not None:
                            sensorvalue = self.get_calculated_sensorvalue(
                                sensorvalue)

                    elif self._devtype == "therm":
                        sensorvalue = device["status"]["current"]
                    elif self._devtype == "motion":
                        sensorvalue = device["status"]["temperature"]
                        self._battery = device["status"]["battery"]
                    elif self._devtype == "pod":
                        sensorvalue = device["status"]["consumption"]
                    else:
                        sensorvalue = None
                    self._state = sensorvalue
                    break
            _LOGGER.debug("Valor: %s", self._state)
            return self._state
        return False
