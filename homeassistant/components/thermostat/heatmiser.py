"""
homeassistant.components.thermostat.heatmiser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Adds support for the PRT Heatmiser themostats using the V3 protocol.

See https://github.com/andylockran/heatmiserV3 for more info on the
heatmiserV3 module dependency.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermostat.heatmiser/
"""
import logging
import heatmiserV3
from homeassistant.components.thermostat import ThermostatDevice
from homeassistant.const import TEMP_CELCIUS

CONF_IPADDRESS = 'ipaddress'
CONF_PORT = 'port'
CONF_TSTATS = 'tstats'

REQUIREMENTS = ["heatmiserV3==0.9.1"]

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up the heatmiser thermostat. """

    ipaddress = str(config[CONF_IPADDRESS])
    port = str(config[CONF_PORT])

    if ipaddress is None or port is None:
        _LOGGER.error("Missing required configuration items %s or %s",
                      CONF_IPADDRESS, CONF_PORT)
        return False

    serport = heatmiserV3.connection.connection(ipaddress, port)
    serport.open()

    tstats = []
    if CONF_TSTATS in config:
        tstats = config[CONF_TSTATS]

    if tstats is None:
        _LOGGER.error("No thermostats configured.")
        return False

    for tstat in tstats:
        add_devices([
            HeatmiserV3Thermostat(
                tstat.get("id"),
                tstat.get("name"),
                serport)
            ])
    return


class HeatmiserV3Thermostat(ThermostatDevice):
    """ Represents a HeatmiserV3 thermostat. """

    def __init__(self, device, name, serport):
        self.device = device
        self.serport = serport
        self._current_temperature = None
        self._name = name
        self._id = device
        self.dcb = None
        self.update()
        self._target_temperature = int(self.dcb.get("roomset"))

    @property
    def name(self):
        """ Returns the name of the honeywell, if any. """
        return self._name

    @property
    def unit_of_measurement(self):
        """ Unit of measurement this thermostat uses."""
        return TEMP_CELCIUS

    @property
    def current_temperature(self):
        """ Returns the current temperature. """
        if self.dcb is not None:
            low = self.dcb.get("floortemplow ")
            high = self.dcb.get("floortemphigh")
            temp = (high*256 + low)/10.0
            self._current_temperature = temp
        else:
            self._current_temperature = None
        return self._current_temperature

    @property
    def target_temperature(self):
        """ Returns the temperature we try to reach. """
        return self._target_temperature

    def set_temperature(self, temperature):
        """ Set new target temperature """
        temperature = int(temperature)
        heatmiserV3.heatmiser.hmSendAddress(
            self._id,
            18,
            temperature,
            1,
            self.serport)
        self._target_temperature = int(temperature)

    def update(self):
        self.dcb = heatmiserV3.heatmiser.hmReadAddress(
            self._id,
            'prt',
            self.serport)
