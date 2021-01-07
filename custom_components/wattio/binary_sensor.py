"""Platform for Wattio integration testing."""
import logging

try:
    from homeassistant.components.binary_sensor import BinarySensorEntity
except ImportError:
    from homeassistant.components.binary_sensor import BinarySensorDevice as BinarySensorEntity
from homeassistant.const import ATTR_BATTERY_LEVEL

from . import WattioDevice

from .const import BINARY_SENSORS, DOMAIN, ICON


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Configure Wattio Binary Sensor."""
    _LOGGER.debug("Wattio Binary Sensor component running ...")
    if discovery_info is None:
        _LOGGER.error("No Binary Sensor device(s) discovered")
        return
    devices = []
    for device in hass.data[DOMAIN]["devices"]:
        icon = None
        if device["type"] in BINARY_SENSORS:
            icon = ICON[device["type"]]
            devices.append(
                WattioBinarySensor(device["name"], device["type"], icon, device["ieee"])
            )
            _LOGGER.debug("Adding device: %s", device["name"])

    async_add_entities(devices)


class WattioBinarySensor(WattioDevice, BinarySensorEntity):
    """Representation of Sensor."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, name, devtype, icon, ieee):
        """Initialize the sensor."""
        self._pre = "bs_"
        self._name = name
        self._state = None
        self._icon = icon
        self._apidata = None
        self._ieee = ieee
        self._devtype = devtype
        self._battery = None
        self._data = None
        self._available = 0

    @property
    def available(self):
        """Return availability."""
        _LOGGER.debug("Device %s - availability: %s", self._name, self._available)
        return True if self._available == 1 else False

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
    def is_on(self):
        """Return state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes of this device."""
        attr = {}
        if self._battery is not None:
            attr[ATTR_BATTERY_LEVEL] = self.get_battery_level()
        return attr

    @property
    def device_class(self):
        """Return device class."""
        if self._devtype is not None:
            if self._devtype == "motion":
                return "motion"
            if self._devtype == "door":
                return "door"
        return None

    def get_battery_level(self):
        """Return device battery level."""
        if self._battery is not None:
            battery_level = round((self._battery * 100) / 4)
            return battery_level
        return False

    async def async_update(self):
        """Update sensor data."""
        # Parece que no tira con las CONST devolver 0 o 1
        self._data = self.hass.data[DOMAIN]["data"]
        _LOGGER.debug("ACTUALIZANDO SENSOR BINARIO %s - %s", self._name, self._ieee)
        if self._data is not None:
            self._available = 0
            for device in self._data:
                if device["ieee"] == self._ieee:
                    self._available = 1
                    if device["type"] == "motion":
                        _LOGGER.debug(device["status"]["presence"])
                        self._battery = device["status"]["battery"]
                        self._state = device["status"]["presence"]
                    elif device["type"] == "door":
                        self._battery = device["status"]["battery"]
                        self._state = device["status"]["opened"]
                        _LOGGER.debug(device["status"]["opened"])
                    elif device["type"] == "siren":
                        self._state = device["status"]["preAlarm"]
                        _LOGGER.debug(device["status"]["preAlarm"])
                    break
            _LOGGER.debug(self._state)
            return self._state
        return False
