"""
homeassistant.components.light.zwave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Support for Z-Wave lights.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.zwave/
"""
# Because we do not compile openzwave on CI
# pylint: disable=import-error
from threading import Timer
import logging

from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.light import (Light, ATTR_BRIGHTNESS)
import homeassistant.components.zwave as zwave

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Find and add Z-Wave lights. """
    if discovery_info is None:
        return

    node = zwave.NETWORK.nodes[discovery_info[zwave.ATTR_NODE_ID]]
    value = node.values[discovery_info[zwave.ATTR_VALUE_ID]]

    if value.command_class != zwave.COMMAND_CLASS_SWITCH_MULTILEVEL:
        return
    if value.type != zwave.TYPE_BYTE:
        return
    if value.genre != zwave.GENRE_USER:
        return

    value.set_change_verified(False)
    add_devices([ZwaveDimmer(value)])


def brightness_state(value):
    """
    Returns the brightness and state according to the current data of given
    value.
    """
    if value.data > 0:
        return (value.data / 99) * 255, STATE_ON
    else:
        return 0, STATE_OFF


class ZwaveDimmer(Light):
    """ Provides a Z-Wave dimmer. """
    # pylint: disable=too-many-arguments
    def __init__(self, value):
        from openzwave.network import ZWaveNetwork
        from pydispatch import dispatcher

        self._value = value
        self._node = value.node

        self._brightness, self._state = brightness_state(value)

        # Used for value change event handling
        self._refreshing = False
        self._timer = None

        dispatcher.connect(
            self._value_changed, ZWaveNetwork.SIGNAL_VALUE_CHANGED)

    def _value_changed(self, value):
        """ Called when a value has changed on the network. """

        if self._value.value_id != value.value_id:
            return

        # Log old and new data.
        updated_brightness, updated_state = brightness_state(value)
        _LOGGER.info('node="%s" label="%s" at=value_changed old=%s/%s '
                     'new=%s/%s data=%s refreshing=%s timer="%s"',
                     self._node.name, value.label,
                     self._state, self._brightness,
                     updated_state, updated_brightness, value.data,
                     self._refreshing, self._timer)

        # Cancel all existing timers. Last write wins.
        self.cancel_existing_timer()

        if self._refreshing:
            # Only update brightness and state if we solicited a refresh.
            _LOGGER.info('node="%s" label="%s" at=updating_state old=%s/%s '
                         'new=%s/%s data=%s refreshing=%s timer="%s"',
                         self._node.name, value.label,
                         self._state, self._brightness,
                         updated_state, updated_brightness, value.data,
                         self._refreshing, self._timer)
            self._refreshing = False
            self._timer = None
            self._state = updated_state
            self._brightness = updated_brightness
        else:
            def _refresh_value():
                """Used timer callback for delayed value refresh."""
                _LOGGER.info('node="%s" label="%s" at=refreshing timer="%s"',
                             self._node.name, self._value.label, self._timer)
                self._value.refresh()

            self._refreshing = True
            self._timer = Timer(2, _refresh_value)
            self._timer.start()
            # Otherwise, schedule a refresh soon in the future.
            _LOGGER.info('node="%s" label="%s" at=scheduling_timer old=%s/%s '
                         'new=%s/%s data=%s refreshing=%s timer="%s"',
                         self._node.name, value.label,
                         self._state, self._brightness,
                         updated_state, updated_brightness, value.data,
                         self._refreshing, self._timer)


        self.update_ha_state()

    def cancel_existing_timer(self):
        """ Cancel existing timer. """
        if self._timer is not None and self._timer.isAlive():
            _LOGGER.info('node="%s" label="%s" at=cancel_existing_timer '
                         ' timer="%s"',
                         self._node.name, self._value.label, self._timer)
            self._timer.cancel()
            self._timer = None

    @property
    def should_poll(self):
        """ No polling needed for a light. """
        return False

    @property
    def name(self):
        """ Returns the name of the device if any. """
        name = self._node.name or "{}".format(self._node.product_name)

        return "{}".format(name or self._value.label)

    @property
    def brightness(self):
        """ Brightness of this light between 0..255. """
        return self._brightness

    @property
    def is_on(self):
        """ True if device is on. """
        return self._state == STATE_ON

    def turn_on(self, **kwargs):
        """ Turn the device on. """

        _LOGGER.info('%s %s turn_on old=%s/%s new=%s/%s',
                     self._node.name, self._value.label,
                     self._state, self._brightness,
                     'on', kwargs)

        self._state = STATE_ON
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            self._brightness = 255

        # Zwave multilevel switches use a range of [0, 99] to control
        # brightness.
        brightness = (self._brightness / 255) * 99

        if self._node.set_dimmer(self._value.value_id, brightness):
            self.update_ha_state()

    def turn_off(self, **kwargs):
        """ Turn the device off. """

        _LOGGER.info('%s %s turn_off old=%s/%s new=%s/%s',
                     self._node.name, self._value.label,
                     self._state, self._brightness,
                     'off', kwargs)

        self._state = STATE_OFF
        self._brightness = 0

        if self._node.set_dimmer(self._value.value_id, 0):
            self.update_ha_state()
