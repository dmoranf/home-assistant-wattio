"""Wattio component constants"""
from homeassistant.const import TEMP_CELSIUS

DOMAIN = "wattio"
VERSION = "0.2.5"

ATTR_ACCESS_TOKEN = "access_token"
ATTR_CLIENT_ID = "client_id"
ATTR_CLIENT_SECRET = "client_secret"
ATTR_LAST_SAVED_AT = "last_saved_at"
DATA_UPDATED = "wattio_{}_data_updated"
DEFAULT_CONFIG = {"client_id": "CLIENT_ID_HERE", "client_secret": "CLIENT_SECRET_HERE"}

BINARY_SENSORS = ["door", "motion", "siren"]
CLIMATE = ["therm"]
PLATFORMS = ["binary_sensor", "climate", "sensor", "switch"]
SECURITY = ["door", "motion", "siren"]
SENSORS = ["bat", "motion", "pod", "therm"]
SWITCHES = ["pod", "siren"]

WATTIO_AUTH_START = "/api/wattio"
WATTIO_AUTH_CALLBACK_PATH = "/api/wattio/callback"
WATTIO_CONF_FILE = "wattio.conf"

# Icons
ICON = {
    "bat" : None,
    "door": "mdi:door",
    "motion": "mdi:adjust",
    "pod": "mdi:power-socket-eu",
    "therm": None,
    "siren": "mdi:alert",
    "siren_sec" : "mdi:security",
    "security": "mdi:security"
}

MEASUREMENT = {
    "bat" : "Watt",
    "door": None,
    "motion": TEMP_CELSIUS,
    "pod": "Watt",
    "therm": TEMP_CELSIUS,
    "siren": None,
    "security": None
}

ICON_DOOR = "mdi:door"
ICON_MOTION = "mdi:adjust"
ICON_POD = "mdi:power-socket-eu"
ICON_SIREN = "mdi:alert"
ICON_SECURITY = "mdi:security"

# Climate
CONF_MAX_TEMP = "therm_max_temp"
CONF_MIN_TEMP = "therm_min_temp"
CONF_SECURITY = "security"
CONF_SECURITY_INTERVAL ="security_interval"
DEFAULT_MAX_TEMP = 30
DEFAULT_MIN_TEMP = 10
