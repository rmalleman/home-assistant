"""
homeassistant.components.media_player.mpr_6zhmaut
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides an interface to mpr-6zhmaut-api
"""
import logging
import requests

from homeassistant.components.media_player import (
    MediaPlayerDevice, SUPPORT_VOLUME_SET,
    SUPPORT_TURN_ON, SUPPORT_TURN_OFF,
    SUPPORT_VOLUME_MUTE, DOMAIN)
from homeassistant.const import (
    STATE_OFF, STATE_ON)

_LOGGER = logging.getLogger(__name__)

SUPPORT_MPR = SUPPORT_VOLUME_SET | SUPPORT_TURN_ON | \
              SUPPORT_VOLUME_MUTE | SUPPORT_TURN_OFF

DOMAIN = 'mpr_6zhmaut'

# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up the mpr_6zhmaut platform. """

    zone = MprZone(
        config.get("name"),
        config.get("host"),
        config.get("port"),
        config.get("zone"),
        config.get("proto", "http"),
    )
    if zone.update():
        add_devices([zone])
        return True
    else:
        return False


class MprZone(MediaPlayerDevice):
    """ Represents a mpr_6zhmaut zone. """

    # pylint: disable=too-many-public-methods

    def __init__(self, name, host, port, zone, proto):
        self._name = name
        self._host = host
        self._port = port
        self._zone = zone
        self._proto = proto
        self._state_hash = {}

    @property
    def _base_url(self):
        """ Returns the base url for endpoints. """
        return self._proto + "://" + self._host + ":" + str(self._port) + "/zones/" + str(self._zone)

    def _request(self, method, path="", d=""):
        """ Makes the actual request and returns the parsed response. """
        url = self._base_url + path

        if method == 'GET':
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, data=str(d), headers={'content-type': 'text/plain'})

        return response.json()

    def update(self):
        self._state_hash = self._request('GET')

        if int(self._state_hash.get("zone")) != int(self._zone):
            return False

        self._pwstate = (int(self._state_hash.get("pr")) == 1)
        self._volume = int(self._state_hash.get("vo")) / 38
        self._muted = (int(self._state_hash.get("mu")) == 1)
        self._mediasource = self._state_hash.get("ch")

        return True

    @property
    def name(self):
        """ Returns the name of the device. """
        return self._name

    @property
    def state(self):
        """ Returns the state of the device. """
        if self._pwstate:
            return STATE_ON

        return STATE_OFF

    @property
    def volume_level(self):
        """ Volume level of the media player (0..1). """
        return self._volume

    @property
    def is_volume_muted(self):
        """ Boolean if volume is currently muted. """
        return self._muted

    @property
    def media_title(self):
        """ Current media source. """
        return self._mediasource

    @property
    def supported_media_commands(self):
        """ Flags of media commands that are supported. """
        return SUPPORT_MPR

    def turn_on(self):
        """ turn the media player on. """
        self._request("POST", "/pr", "01")

    def turn_off(self):
        """ turn_off media player. """
        self._request("POST", "/pr", "00")

    def set_volume_level(self, volume):
        """ set volume level, range 0..1. """
        self._request("POST", "/vo", str(round(volume * 38)).zfill(2))

    def mute_volume(self, mute):
        """ mute (true) or unmute (false) media player. """
        if mute:
            self._request("POST", "/mu", "01")
        else:
            self._request("POST", "/mu", "00")
