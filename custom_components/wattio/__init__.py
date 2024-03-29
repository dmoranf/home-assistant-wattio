"""Wattio smarthome platform integration."""
import json
import logging
import os
import sys
import time
from datetime import timedelta

import voluptuous as vol

import aiohttp
import asyncio

from homeassistant.components.http import HomeAssistantView
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.network import get_url
from homeassistant.util.json import load_json, save_json


from .const import (
    ATTR_ACCESS_TOKEN,
    ATTR_CLIENT_ID,
    ATTR_CLIENT_SECRET,
    ATTR_LAST_SAVED_AT,
    CONF_OFFSETS,
    CONF_EXCLUSIONS,
    CONF_SECURITY,
    CONF_SECURITY_INTERVAL,
    DATA_UPDATED,
    DEFAULT_CONFIG,
    DOMAIN,
    PLATFORMS,
    SECURITY,
    VERSION,
    WATTIO_AUTH_START,
    WATTIO_CONF_FILE,
    WATTIO_STATUS_URI,
    WATTIO_DEVICES_URI,
    WATTIO_TOKEN_URI,
    WATTIO_POD_URI,
    WATTIO_SIREN_URI,
    WATTIO_THERMIC_MODE_URI,
    WATTIO_THERMIC_TEMP_URI,
    WATTIO_SEC_STATUS_URI,
    WATTIO_SEC_SET_URI,
    WATTIO_SEC_MODE,
    WATTIO_AUTH_URI,
    WATTIO_TOKEN_URI
)

_LOGGER = logging.getLogger(__name__)

CONFIGURING = {}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {vol.Optional(CONF_SECURITY, default=False): cv.boolean,
             vol.Optional(CONF_SECURITY_INTERVAL, default=0): cv.positive_int,
             vol.Optional(CONF_EXCLUSIONS, default=[]): vol.All(cv.ensure_list, [cv.string]),
             vol.Optional(CONF_OFFSETS, default=[]): vol.All(cv.ensure_list)},
            extra=vol.ALLOW_EXTRA,
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Configure Wattio platform."""
    update_interval = config[DOMAIN].get(CONF_SCAN_INTERVAL)
    security_enabled = config[DOMAIN].get(CONF_SECURITY)
    if config[DOMAIN].get(CONF_SECURITY_INTERVAL) == 0:
        security_interval = update_interval
    else:
        security_interval = config[DOMAIN].get(CONF_SECURITY_INTERVAL)

    _LOGGER.info(
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
                    "Scheduled device SECURITY update running for %s - %s",
                    device["type"],
                    device["ieee"],
                )
                device_id = "sec_" + device["ieee"]
                hass.data[DOMAIN][device_id] = asyncio.run_coroutine_threadsafe(apidata.async_get_security_device_status(
                    device["type"], device["ieee"]
                ), hass.loop).result()
                async_dispatcher_send(hass, DATA_UPDATED.format(device_id))

    def poll_wattio_update(event_time):
        _LOGGER.debug("Scheduled device status update running ...")
        data = asyncio.run_coroutine_threadsafe(
            apidata.async_update_wattio_data(), hass.loop).result()
        _LOGGER.debug("API response data: %s", data)
        if data is not None:
            json_data = json.loads(data)
            hass.data[DOMAIN]["data"] = json_data
            for device in json_data:
                # Channel required for BATs
                if device["type"] == "bat":
                    channelid = 0
                    for _ in device["status"]["consumption"]:
                        device_id = "s_" + \
                            device["ieee"] + "_" + str(channelid)
                        _LOGGER.debug("Updating callback %s", device_id)
                        async_dispatcher_send(
                            hass, DATA_UPDATED.format(device_id))
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
        session = async_get_clientsession(hass)
        apidata = wattioApi(token, session)
        hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["data"] = None
        hass.data[DOMAIN]["devices"] = asyncio.run_coroutine_threadsafe(
            apidata.async_get_devices(), hass.loop).result()
        hass.data[DOMAIN]["token"] = token
        hass.data[DOMAIN]["security_enabled"] = security_enabled
        hass.data[DOMAIN][CONF_EXCLUSIONS] = config[DOMAIN].get(
            CONF_EXCLUSIONS)
        hass.data[DOMAIN][CONF_OFFSETS] = config[DOMAIN].get(CONF_OFFSETS)
        # Create Updater Object
        for platform in PLATFORMS:
            load_platform(hass, platform, DOMAIN, {}, config)

        track_time_interval(hass, poll_wattio_update,
                            timedelta(seconds=update_interval))

        if security_enabled is True:
            _LOGGER.debug("Adding security callbacks")
            track_time_interval(
                hass, poll_wattio_security_update, timedelta(
                    seconds=security_interval)
            )
        return True
    # Not Authorized, need to complete OAUTH2 process
    auth_uri = get_auth_uri(hass, config_file.get("client_id"))
    start_uri = "{}{}".format(get_url(hass), WATTIO_AUTH_START)
    _LOGGER.error(
        "No token configured, complete OAUTH2 authorization: %s", auth_uri)
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

    start_url = "{}{}".format(get_url(hass), WATTIO_AUTH_START)
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
    redirect_uri = "{}{}".format(get_url(hass), WATTIO_AUTH_START)
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
    async def get(self, request):
        """Oauth2 completion View."""
        data = request.query
        text = "<h2>WATTIO</h2>"
        # Check if TOKEN previously exists.
        config_file = load_json(self.hass.config.path(WATTIO_CONF_FILE))
        if "access_token" in config_file:
            text += "Acceso previamente autorizado, si necesitar volver a actualizarlo borra el fichero {} y vuelve a iniciar el proceso.".format(
                self.hass.config.path(WATTIO_CONF_FILE)
            )
            return aiohttp.web.Response(text=text, content_type="text/html")
        if data.get("code") is None:
            _LOGGER.error("SIN AUTORIZAR")
            text += """<p>Por favor, <a href="{}">autoriza a Home Assistant</a> para que pueda acceder a la informacion de WATTIO</p>
                """.format(
                    self.auth_uri
            )
            return aiohttp.web.Response(text=text, content_type="text/html")
        session = async_get_clientsession(self.hass)
        api = wattioApi(None, session)
        token = await api.async_get_token(
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
                save_json(self.hass.config.path(
                    WATTIO_CONF_FILE), config_contents)

                return aiohttp.web.Response(text="Autorizado :)")
            except:
                _LOGGER.error("Error guardando TOKEN %s ", sys.exc_info()[0])
                return aiohttp.web.Response(
                    text="No se ha podido almacenar TOKEN revisar permisos"
                )
        else:
            return aiohttp.web.Response(text="Algo fue un poco mal :/")


class WattioDevice(Entity):
    """Wattio Device Common Object."""

    def __init__(self, ieee):
        """Log WattioDevice initialization."""
        _LOGGER.error("WattioDevice %s", ieee)

    async def async_added_to_hass(self):
        """Add Callbacks for update."""
        if self._devtype == "bat" and self._channel is not None:
            device_id = str(self._pre) + str(self._ieee) + \
                "_" + str(self._channel)
        else:
            device_id = str(self._pre) + str(self._ieee)
        _LOGGER.debug(
            "Callback added for %s, %s",
            DATA_UPDATED.format(device_id),
            DATA_UPDATED.format(self._name),
        )
        async_dispatcher_connect(
            self.hass, DATA_UPDATED.format(device_id), self._refresh)

    @callback
    def _refresh(self):
        self.async_schedule_update_ha_state(True)


class wattioApi:
    """Wattio API Class to retrieve data."""

    def __init__(self, token=None, session=None):
        """Init function."""
        self._value = None
        self._data = None
        self._token = token
        self._session = session
        self._headers = None

        if self._token is not None:
            self._headers = {"Authorization": "Bearer " + self._token}

    async def async_api_request(self, httpmethod, uri, output=False, payload=None):
        try:
            async with getattr(self._session, httpmethod)(uri, headers=self._headers, data=payload) as api_call_response:
                _LOGGER.debug(str(uri) + " - Response Code:" +
                              str(api_call_response.status))
                if output:
                    data = await api_call_response.text()
                    return data
                return 1
        except (aiohttp.ClientConnectorError, aiohttp.ClientResponseError) as err:
            _LOGGER.error(
                "Error getting response from Wattio API")
            _LOGGER.error(err)
            if output:
                return None
            return 0

    async def async_get_token(self, code, client_id, client_secret, redirect_uri):
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        response = await self.async_api_request("post", WATTIO_TOKEN_URI, True, data)
        if response:
            try:
                token_json = json.loads(response)
                token = token_json["access_token"]
                self._token = token
                return token
            except:
                _LOGGER.error("Error getting token")
                return 0

    async def async_get_devices(self):
        """Get device info from Wattio API."""
        response = await self.async_api_request("get", WATTIO_DEVICES_URI, True)
        registered_devices = json.loads(response)
        _LOGGER.debug("Wattio registered devices:")
        _LOGGER.debug(registered_devices)
        return registered_devices

    async def async_update_wattio_data(self):
        """Get Data from WattioApi."""
        response = await self.async_api_request("get", WATTIO_STATUS_URI, True)
        _LOGGER.debug("Wattio STATUS data: " + str(response))
        return response

    async def async_get_security_device_status(self, devtype, ieee):
        """Gets Security appliances status."""
        uri = WATTIO_SEC_STATUS_URI.format(str(devtype), str(ieee))
        response = await self.async_api_request("get", uri, True)
        _LOGGER.debug("Wattio SECURITY STATUS data for "+str(ieee) + " - " + str(devtype) + " : "+str(response))
        return response

    async def async_set_security_device_status(self, devtype, ieee, status):
        """Change security appliance status on / off."""
        _LOGGER.debug("SECURITY Status change for %s - %s",
                      str(ieee), str(status))
        uri = WATTIO_SEC_SET_URI.format(
            str(devtype), str(ieee), str(status))
        response = await self.async_api_request("put", uri)
        if response == 1:
            return 1 if status == "on" else 0
        return response

    async def async_set_switch_status(self, ieee, status, devtype="pod"):
        """Change switch status on / off."""
        if devtype == "pod":
            wattio_uri = WATTIO_POD_URI
        else:
            wattio_uri = WATTIO_SIREN_URI
        _LOGGER.debug("Status change for %s - %s", str(ieee), str(status))
        uri = wattio_uri.format(str(ieee), str(status))
        response = await self.async_api_request("put", uri)
        if response == 1:
            return 1 if status == "on" else 0
        return response

    async def async_set_thermic_temp(self, ieee, temp):
        """Change thermic target temp."""
        _LOGGER.debug("Updated request for %s - %s", str(ieee), str(temp))
        uri = WATTIO_THERMIC_TEMP_URI.format(str(ieee), str(temp))
        response = await self.async_api_request("put", uri)
        return response

    async def async_set_thermic_mode(self, ieee, status):
        """Change thermic working mode."""
        _LOGGER.debug("Updated request for %s - %s", str(ieee), str(status))
        uri = WATTIO_THERMIC_MODE_URI.format(str(ieee), str(status))
        response = await self.async_api_request("put", uri)
        return response
