"""Wattio smarthome platform integration."""
import json
import logging
import os
import sys
import time
from datetime import timedelta
import voluptuous as vol

import requests

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval
from homeassistant.util.json import load_json, save_json

from .const import (
    ATTR_ACCESS_TOKEN,
    ATTR_CLIENT_ID,
    ATTR_CLIENT_SECRET,
    ATTR_LAST_SAVED_AT,
    CONF_SECURITY,
    CONF_SECURITY_INTERVAL,
    DATA_UPDATED,
    DEFAULT_CONFIG,
    DOMAIN,
    PLATFORMS,
    SECURITY,
    VERSION,
    WATTIO_AUTH_START,
    WATTIO_AUTH_CALLBACK_PATH,
    WATTIO_CONF_FILE,
)

# Component Version

_LOGGER = logging.getLogger(__name__)

WATTIO_STATUS_URI = "https://api.wattio.com/public/v1/appliances/status"
WATTIO_DEVICES_URI = "https://api.wattio.com/public/v1/appliances"
WATTIO_TOKEN_URI = "https://api.wattio.com/public/oauth2/token"
WATTIO_POD_URI = "https://api.wattio.com/public/v1/appliances/pod/{}/{}"
WATTIO_SIREN_URI = "https://api.wattio.com/public/v1/appliances/siren/{}/{}"
WATTIO_THERMIC_MODE_URI = "https://api.wattio.com/public/v1/appliances/therm/{}/mode/{}"
WATTIO_THERMIC_TEMP_URI = "https://api.wattio.com/public/v1/appliances/therm/{}/target/{}"
WATTIO_SEC_STATUS_URI = "https://api.wattio.com/public/v1/security/{}/{}"
WATTIO_SEC_SET_URI = "https://api.wattio.com/public/v1/security/{}/{}/{}"
WATTIO_AUTH_URI = "https://api.wattio.com/public/oauth2/authorize"
WATTIO_TOKEN_URI = "https://api.wattio.com/public/oauth2/token"


CONFIGURING = {}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {vol.Optional(CONF_SECURITY, default=False): cv.boolean},
            {vol.Optional(CONF_SECURITY_INTERVAL, default=None): cv.positive_int},
            extra=vol.ALLOW_EXTRA,
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Configure Wattio platform."""
    update_interval = config[DOMAIN].get(CONF_SCAN_INTERVAL)
    security_enabled = config[DOMAIN].get(CONF_SECURITY)
    if config[DOMAIN].get(CONF_SECURITY_INTERVAL) is None:
        security_interval = update_interval
    else:
        security_interval = config[DOMAIN].get(CONF_SECURITY_INTERVAL)

    _LOGGER.debug(
        "=> Wattio platform v%s started | Update Interval %s seconds | Security Interval %s seconds <=",
        VERSION,
        update_interval,
        security_interval,
    )

    def poll_wattio_security_update(event_time):
        """Schedule updates for security appliances, one request for each one."""
        for device in hass.data[DOMAIN]["devices"]:
            if device["type"] in SECURITY:
                _LOGGER.debug(
                    "Scheduled device security update running for %s - %s",
                    device["type"],
                    device["ieee"],
                )
                device_id = "sec_" + device["ieee"]
                hass.data[DOMAIN][device_id] = apidata.get_security_device_status(
                    device["type"], device["ieee"]
                )
                async_dispatcher_send(hass, DATA_UPDATED.format(device_id))

    def poll_wattio_update(event_time):
        _LOGGER.debug("Scheduled device status update running ...")
        data = apidata.update_wattio_data()
        _LOGGER.debug("API response data: %s", data)
        if data is not None:
            json_data = json.loads(data)
            hass.data[DOMAIN]["data"] = json_data
            for device in json_data:
                # Channel required for BATs
                if device["type"] == "bat":
                    channelid = 0
                    for _ in device["status"]["consumption"]:
                        device_id = "s_" + device["ieee"] + "_" + str(channelid)
                        _LOGGER.debug("Updating callback %s", device_id)
                        async_dispatcher_send(hass, DATA_UPDATED.format(device_id))
                        channelid = channelid + 1
                else:
                    # Generate sensors for all devices
                    device_id = "s_" + device["ieee"]
                    _LOGGER.debug("Updating callback %s", device_id)
                    async_dispatcher_send(hass, DATA_UPDATED.format(device_id))

                # Binary Sensors
                if (
                        device["type"] == "door"
                        or device["type"] == "motion"
                        or device["type"] == "siren"
                ):
                    device_id = "bs_" + device["ieee"]
                    _LOGGER.debug("Updating callback %s", device_id)
                    async_dispatcher_send(hass, DATA_UPDATED.format(device_id))

                # Climate
                if device["type"] == "therm":
                    device_id = "cli_" + device["ieee"]
                    _LOGGER.debug("Updating callback %s", device_id)
                    async_dispatcher_send(hass, DATA_UPDATED.format(device_id))

                # Switches
                if device["type"] == "pod" or device["type"] == "siren":
                    device_id = "sw_" + device["ieee"]
                    _LOGGER.debug("Updating callback %s", device_id)
                    async_dispatcher_send(hass, DATA_UPDATED.format(device_id))
        else:
            _LOGGER.error(
                "Couldn't fetch data from WATTIO API, retrying on next scheduled update ..."
            )

    config_path = hass.config.path(WATTIO_CONF_FILE)
    _LOGGER.debug("Wattio config file: %s", (config_path))
    config_status = check_config_file(config_path)
    # Check Wattio file configuration status
    if config_status == 2:
        request_app_setup(hass, config, config_path)
        return True
    if config_status == 1:
        _LOGGER.error("Config file doesn't exist, creating ...")
        save_json(config_path, DEFAULT_CONFIG)
        request_app_setup(hass, config, config_path)
        return True
    if "wattio" in CONFIGURING:
        hass.components.configurator.request_done(CONFIGURING.pop("wattio"))
    config_file = load_json(config_path)
    token = config_file.get(ATTR_ACCESS_TOKEN)
    # Wattio Token does not expire
    # expires_at = config_file.get(ATTR_LAST_SAVED_AT)
    if token is not None:
        apidata = wattioApi(token)
        hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["data"] = None
        hass.data[DOMAIN]["devices"] = apidata.get_devices()
        hass.data[DOMAIN]["token"] = token
        hass.data[DOMAIN]["security_enabled"] = security_enabled
        # Create Updater Object
        for platform in PLATFORMS:
            load_platform(hass, platform, DOMAIN, {}, config)

        track_time_interval(hass, poll_wattio_update, timedelta(seconds=update_interval))

        if security_enabled is True:
            _LOGGER.debug("Adding security callbacks")
            track_time_interval(
                hass, poll_wattio_security_update, timedelta(seconds=security_interval)
            )
        return True
    # Not Authorized, need to complete OAUTH2 process
    auth_uri = get_auth_uri(hass, config_file.get("client_id"))
    start_uri = "{}{}".format(hass.config.api.base_url, WATTIO_AUTH_START)
    _LOGGER.error("No token configured, complete OAUTH2 authorization: %s", auth_uri)
    hass.http.register_view(
        WattioRegisterView(
            hass,
            config,
            config_file.get("client_id"),
            config_file.get("client_secret"),
            auth_uri,
            start_uri,
        )
    )
    request_oauth_completion(hass, config, auth_uri, setup)
    return True


def request_app_setup(hass, config, config_path):
    """Request user configure integration parameters."""
    global CONFIGURING
    _LOGGER.debug("Request APP Setup")
    configurator = hass.components.configurator

    def wattio_configuration_callback(callback_data):
        config_status = check_config_file(hass.config.path(WATTIO_CONF_FILE))
        if config_status == 2:
            configurator.notify_errors(
                CONFIGURING["wattio"],
                "Por favor, revisa el fichero y vuelve a intentarlo.",
            )
            # configurator.request_done(CONFIGURING["wattio"])
        elif config_status == 1:
            configurator.notify_errors(
                CONFIGURING["wattio"], "No se puede leer el fichero wattio.conf"
            )
        else:
            configurator.request_done(CONFIGURING.pop("wattio"))
            setup(hass, config)

    description = "Wattio SmartHome no configurado</span>.<br /><br /> - Solicita tu Client y Secret ID a soporte de Wattio.<br />- Edita manualmente el fichero wattio.conf<br />- Añade el Client y Secret al fichero<br /><br />- Una vez finalizado, pulsa Siguiente<br /><br />Si algo no va bien revisa los logs de HA :)<br />"
    submit = "Siguiente"
    CONFIGURING["wattio"] = configurator.request_config(
        "Wattio - Paso 1/2",
        wattio_configuration_callback,
        description=description,
        submit_caption=submit,
    )


def request_oauth_completion(hass, config, auth_uri, setup):
    """Request user complete WATTIO OAuth2 flow."""
    global CONFIGURING
    configurator = hass.components.configurator

    def wattio_configuration_callback(callback_data):
        """Check if token is configured else show the notification."""
        config_file = load_json(hass.config.path(WATTIO_CONF_FILE))
        token = config_file.get(ATTR_ACCESS_TOKEN)
        if token is None:
            configurator.notify_errors(
                CONFIGURING["wattio"], "No se ha obtenido el token, inténtalo de nuevo."
            )
            return False
        setup(hass, config)

    if "wattio" in CONFIGURING:
        configurator.notify_errors(
            CONFIGURING["wattio"], "Fallo el registro, intentalo de nuevo."
        )
        return

    start_url = "{}{}".format(hass.config.api.base_url, WATTIO_AUTH_START)
    description = 'Para finalizar autoriza el componente en Wattio:<br /><br /> <a href="{}" target="_blank">{}</a>'.format(
        start_url, start_url
    )
    CONFIGURING["wattio"] = configurator.request_config(
        "Wattio - Paso 2/2",
        wattio_configuration_callback,
        description=description,
        submit_caption="Finalizar",
    )


def get_auth_uri(hass, client_id):
    """Return Wattio Auth URI."""
    # state = "WATTIOHASSIOTESTING2" # Change to RANDOM
    redirect_uri = "{}{}".format(hass.config.api.base_url, WATTIO_AUTH_START)
    authorize_uri = (
        WATTIO_AUTH_URI
        + "?response_type=code&client_id="
        + client_id
        + "&redirect_uri="
        + redirect_uri
    )
    return authorize_uri


def check_config_file(configpath):
    """Check if config file exists | 0 All OK | 1 File does not exist | 2 Not configued."""
    if os.path.isfile(configpath):
        try:
            config_file = load_json(configpath)
            if config_file == DEFAULT_CONFIG:
                _LOGGER.error("Wattio is not configured, check %s", configpath)
                return 2
            return 0
        except:
            _LOGGER.error(
                "Can't read %s file, please check owner / permissions", configpath
            )
            return 2
    return 1


class WattioRegisterView(HomeAssistantView):
    """Register View for Oauth2 Authorization."""

    requires_auth = False
    url = WATTIO_AUTH_START
    requires_auth = False
    name = "api:wattio"

    def __init__(self, hass, config, client_id, client_secret, auth_uri, start_uri):
        """Init Wattio view for OAUTH registration."""
        self.config = config
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_uri = auth_uri
        self.start_uri = start_uri
        self.hass = hass

    @callback
    def get(self, request):
        """Oauth2 completion View."""
        data = request.query
        text = "<h2>WATTIO</h2>"
        # Check if TOKEN previously exists.
        config_file = load_json(self.hass.config.path(WATTIO_CONF_FILE))
        if "access_token" in config_file:
            text += "Acceso previamente autorizado, si necesitar volver a actualizarlo borra el fichero {} y vuelve a iniciar el proceso.".format(
                self.hass.config.path(WATTIO_CONF_FILE)
            )
            return web.Response(text=text, content_type="text/html")
        if data.get("code") is None:
            _LOGGER.error("SIN AUTORIZAR")
            text += """<p>Por favor, <a href="{}">autoriza a Home Assistant</a> para que pueda acceder a la informacion de WATTIO</p>
                """.format(
                    self.auth_uri
                )
            return web.Response(text=text, content_type="text/html")
        api = wattioApi()
        token = api.get_token(
            str(data.get("code")),
            str(self.client_id),
            str(self.client_secret),
            str(self.start_uri),
        )
        if token:
            config_contents = {
                ATTR_ACCESS_TOKEN: token,
                ATTR_CLIENT_ID: self.client_id,
                ATTR_CLIENT_SECRET: self.client_secret,
                ATTR_LAST_SAVED_AT: int(time.time()),
            }
            try:
                save_json(self.hass.config.path(WATTIO_CONF_FILE), config_contents)

                return web.Response(text="Autorizado :)")
            except:
                _LOGGER.error("Error guardando TOKEN %s ", sys.exc_info()[0])
                return web.Response(
                    text="No se ha podido almacenar TOKEN revisar permisos"
                )
        else:
            return web.Response(text="Algo fue un poco mal :/")


class WattioDevice(Entity):
    """Wattio Device Common Object."""

    def __init__(self, ieee):
        """Log WattioDevice initialization."""
        _LOGGER.error("WattioDevice %s", ieee)

    async def async_added_to_hass(self):
        """Add Callbacks for update."""
        if self._devtype == "bat" and self._channel is not None:
            device_id = str(self._pre) + str(self._ieee) + "_" + str(self._channel)
        else:
            device_id = str(self._pre) + str(self._ieee)
        _LOGGER.debug(
            "Callback added for %s, %s",
            DATA_UPDATED.format(device_id),
            DATA_UPDATED.format(self._name),
        )
        async_dispatcher_connect(self.hass, DATA_UPDATED.format(device_id), self._refresh)

    @callback
    def _refresh(self):
        self.async_schedule_update_ha_state(True)


class wattioApi:
    """Wattio API Class to retrieve data."""

    def __init__(self, token=None):
        """Init function."""
        self._value = None
        self._data = None
        self._token = token

    def get_token(self, code, client_id, client_secret, redirect_uri):
        """Get Token from Wattio API, requieres Auth Code, Client ID and Secret."""
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        try:
            access_token_response = requests.post(
                WATTIO_TOKEN_URI, data=data, allow_redirects=False
            )
            if "404" in access_token_response.text:
                _LOGGER.error("Token expired, restart the process")
                return 0
            try:
                token_json = json.loads(access_token_response.text)
                token = token_json["access_token"]
                self._token = token
                return token
            except:
                _LOGGER.error("Error getting token")
                return 0
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Could't get TOKEN from Wattio API")
            _LOGGER.error(err)

    def get_devices(self):
        """Get device info from Wattio API."""
        api_call_headers = {"Authorization": "Bearer " + self._token}
        try:
            api_call_response = requests.get(
                WATTIO_DEVICES_URI, headers=api_call_headers
            )
            registered_devices = json.loads(api_call_response.text)
            return registered_devices
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Couldn't get device info from Wattio API")
            _LOGGER.error(err)
            return None

    def update_wattio_data(self):
        """Get Data from WattioApi."""
        api_call_headers = {"Authorization": "Bearer " + self._token}
        try:
            api_call_response = requests.get(
                WATTIO_STATUS_URI, headers=api_call_headers
            )
            if api_call_response.status_code == 200:
                _LOGGER.debug("API call status code %s", api_call_response.status_code)
                return api_call_response.text
            _LOGGER.error("API call Status code %s", api_call_response.status_code)
            return None
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Couldn't get device status data from Wattio API")
            _LOGGER.error(err)
            return None

    def get_security_device_status(self, devtype, ieee):
        """Gets Security appliances status."""
        api_call_headers = {"Authorization": "Bearer " + self._token}
        try:
            uri = WATTIO_SEC_STATUS_URI.format(str(devtype), str(ieee))
            api_call_response = requests.get(uri, headers=api_call_headers)
            if api_call_response.status_code == 200:
                _LOGGER.debug(
                    "API security call status code %s", api_call_response.status_code
                )
                return api_call_response.text
            if api_call_response.status_code == 404:
                return False
            _LOGGER.error(
                "API security call Status code %s", api_call_response.status_code
            )
            return None
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Couldn't get security device status data from Wattio API")
            _LOGGER.error(err)
            return None

    def set_security_device_status(self, devtype, ieee, status):
        """Change security appliance status on / off."""
        _LOGGER.debug("Security Status change for %s - %s", str(ieee), str(status))
        _LOGGER.debug("Peticion API Security")
        api_call_headers = {"Authorization": "Bearer " + self._token}
        try:
            uri = WATTIO_SEC_SET_URI.format(str(devtype), str(ieee), str(status))
            api_call_response = requests.put(uri, headers=api_call_headers)
            _LOGGER.debug(api_call_response.text)
            return 1 if status == "on" else 0
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Couldn't change device security status data from Wattio API")
            _LOGGER.error(err)

    def set_switch_status(self, ieee, status, devtype="pod"):
        """Change switch status on / off."""
        if devtype == "pod":
            wattio_uri = WATTIO_POD_URI
        else:
            wattio_uri = WATTIO_SIREN_URI
        _LOGGER.debug("Status change for %s - %s", str(ieee), str(status))
        _LOGGER.debug("Peticion API")
        api_call_headers = {"Authorization": "Bearer " + self._token}
        try:
            uri = wattio_uri.format(str(ieee), str(status))
            api_call_response = requests.put(uri, headers=api_call_headers)
            _LOGGER.debug(api_call_response.text)
            return 1 if status == "on" else 0
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Couldn't change device status data from Wattio API")
            _LOGGER.error(err)

    def set_thermic_temp(self, ieee, temp):
        """Change thermic target temp."""
        _LOGGER.debug("Updated request for %s - %s", str(ieee), str(temp))
        api_call_headers = {"Authorization": "Bearer " + self._token}
        try:
            uri = WATTIO_THERMIC_TEMP_URI.format(str(ieee), str(temp))
            api_call_response = requests.put(uri, headers=api_call_headers)
            _LOGGER.debug(api_call_response.text)
            return 1
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Couldn't change device status data from Wattio API")
            _LOGGER.error(err)
            return 0

    def set_thermic_mode(self, ieee, status):
        """Change thermic working mode."""
        _LOGGER.debug("Updated request for %s - %s", str(ieee), str(status))
        api_call_headers = {"Authorization": "Bearer " + self._token}
        try:
            uri = WATTIO_THERMIC_MODE_URI.format(str(ieee), str(status))
            api_call_response = requests.put(uri, headers=api_call_headers)
            _LOGGER.debug(api_call_response.text)
            return 1
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Couldn't change device status data from Wattio API")
            _LOGGER.error(err)
            return 0
