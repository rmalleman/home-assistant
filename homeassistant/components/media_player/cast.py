"""
homeassistant.components.media_player.chromecast
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides functionality to interact with Cast devices on the network.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.cast/
"""
# pylint: disable=import-error
import logging

from homeassistant.const import (
    STATE_PLAYING, STATE_PAUSED, STATE_IDLE, STATE_OFF,
    STATE_UNKNOWN, CONF_HOST)

from homeassistant.components.media_player import (
    MediaPlayerDevice,
    SUPPORT_PAUSE, SUPPORT_VOLUME_SET, SUPPORT_VOLUME_MUTE,
    SUPPORT_TURN_ON, SUPPORT_TURN_OFF, SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK, SUPPORT_NEXT_TRACK,
    MEDIA_TYPE_MUSIC, MEDIA_TYPE_TVSHOW, MEDIA_TYPE_VIDEO)

REQUIREMENTS = ['pychromecast==0.7.1']
CONF_IGNORE_CEC = 'ignore_cec'
CAST_SPLASH = 'https://home-assistant.io/images/cast/splash.png'
SUPPORT_CAST = SUPPORT_PAUSE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_PREVIOUS_TRACK | \
    SUPPORT_NEXT_TRACK | SUPPORT_PLAY_MEDIA
KNOWN_HOSTS = []

DEFAULT_PORT = 8009


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up the cast platform. """
    import pychromecast
    logger = logging.getLogger(__name__)

    # import CEC IGNORE attributes
    ignore_cec = config.get(CONF_IGNORE_CEC, [])
    if isinstance(ignore_cec, list):
        pychromecast.IGNORE_CEC += ignore_cec
    else:
        logger.error('CEC config "%s" must be a list.', CONF_IGNORE_CEC)

    hosts = []

    if discovery_info and discovery_info in KNOWN_HOSTS:
        return

    elif discovery_info:
        hosts = [discovery_info]

    elif CONF_HOST in config:
        hosts = [(config[CONF_HOST], DEFAULT_PORT)]

    else:
        hosts = [tuple(dev[:2]) for dev in pychromecast.discover_chromecasts()
                 if tuple(dev[:2]) not in KNOWN_HOSTS]

    casts = []

    for host in hosts:
        try:
            casts.append(CastDevice(*host))
            KNOWN_HOSTS.append(host)
        except pychromecast.ChromecastConnectionError:
            pass

    add_devices(casts)


class CastDevice(MediaPlayerDevice):
    """ Represents a Cast device on the network. """

    # pylint: disable=abstract-method
    # pylint: disable=too-many-public-methods

    def __init__(self, host, port):
        import pychromecast
        self.cast = pychromecast.Chromecast(host, port)

        self.cast.socket_client.receiver_controller.register_status_listener(
            self)
        self.cast.socket_client.media_controller.register_status_listener(self)

        self.cast_status = self.cast.status
        self.media_status = self.cast.media_controller.status

    # Entity properties and methods

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        """ Returns the name of the device. """
        return self.cast.device.friendly_name

    # MediaPlayerDevice properties and methods

    @property
    def state(self):
        """ State of the player. """
        if self.media_status is None:
            return STATE_UNKNOWN
        elif self.media_status.player_is_playing:
            return STATE_PLAYING
        elif self.media_status.player_is_paused:
            return STATE_PAUSED
        elif self.media_status.player_is_idle:
            return STATE_IDLE
        elif self.cast.is_idle:
            return STATE_OFF
        else:
            return STATE_UNKNOWN

    @property
    def volume_level(self):
        """ Volume level of the media player (0..1). """
        return self.cast_status.volume_level if self.cast_status else None

    @property
    def is_volume_muted(self):
        """ Boolean if volume is currently muted. """
        return self.cast_status.volume_muted if self.cast_status else None

    @property
    def media_content_id(self):
        """ Content ID of current playing media. """
        return self.media_status.content_id if self.media_status else None

    @property
    def media_content_type(self):
        """ Content type of current playing media. """
        if self.media_status is None:
            return None
        elif self.media_status.media_is_tvshow:
            return MEDIA_TYPE_TVSHOW
        elif self.media_status.media_is_movie:
            return MEDIA_TYPE_VIDEO
        elif self.media_status.media_is_musictrack:
            return MEDIA_TYPE_MUSIC
        return None

    @property
    def media_duration(self):
        """ Duration of current playing media in seconds. """
        return self.media_status.duration if self.media_status else None

    @property
    def media_image_url(self):
        """ Image url of current playing media. """
        if self.media_status is None:
            return None

        images = self.media_status.images

        return images[0].url if images else None

    @property
    def media_title(self):
        """ Title of current playing media. """
        return self.media_status.title if self.media_status else None

    @property
    def media_artist(self):
        """ Artist of current playing media. (Music track only) """
        return self.media_status.artist if self.media_status else None

    @property
    def media_album(self):
        """ Album of current playing media. (Music track only) """
        return self.media_status.album_name if self.media_status else None

    @property
    def media_album_artist(self):
        """ Album arist of current playing media. (Music track only) """
        return self.media_status.album_artist if self.media_status else None

    @property
    def media_track(self):
        """ Track number of current playing media. (Music track only) """
        return self.media_status.track if self.media_status else None

    @property
    def media_series_title(self):
        """ Series title of current playing media. (TV Show only)"""
        return self.media_status.series_title if self.media_status else None

    @property
    def media_season(self):
        """ Season of current playing media. (TV Show only) """
        return self.media_status.season if self.media_status else None

    @property
    def media_episode(self):
        """ Episode of current playing media. (TV Show only) """
        return self.media_status.episode if self.media_status else None

    @property
    def app_id(self):
        """  ID of the current running app. """
        return self.cast.app_id

    @property
    def app_name(self):
        """  Name of the current running app. """
        return self.cast.app_display_name

    @property
    def supported_media_commands(self):
        """ Flags of media commands that are supported. """
        return SUPPORT_CAST

    def turn_on(self):
        """ Turns on the ChromeCast. """
        # The only way we can turn the Chromecast is on is by launching an app
        if not self.cast.status or not self.cast.status.is_active_input:
            import pychromecast

            if self.cast.app_id:
                self.cast.quit_app()

            self.cast.play_media(
                CAST_SPLASH, pychromecast.STREAM_TYPE_BUFFERED)

    def turn_off(self):
        """ Turns Chromecast off. """
        self.cast.quit_app()

    def mute_volume(self, mute):
        """ mute the volume. """
        self.cast.set_volume_muted(mute)

    def set_volume_level(self, volume):
        """ set volume level, range 0..1. """
        self.cast.set_volume(volume)

    def media_play(self):
        """ Send play commmand. """
        self.cast.media_controller.play()

    def media_pause(self):
        """ Send pause command. """
        self.cast.media_controller.pause()

    def media_previous_track(self):
        """ Send previous track command. """
        self.cast.media_controller.rewind()

    def media_next_track(self):
        """ Send next track command. """
        self.cast.media_controller.skip()

    def media_seek(self, position):
        """ Seek the media to a specific location. """
        self.cast.media_controller.seek(position)

    def play_media(self, media_type, media_id):
        """ Plays media from a URL """
        self.cast.media_controller.play_media(media_id, media_type)

    # implementation of chromecast status_listener methods

    def new_cast_status(self, status):
        """ Called when a new cast status is received. """
        self.cast_status = status
        self.update_ha_state()

    def new_media_status(self, status):
        """ Called when a new media status is received. """
        self.media_status = status
        self.update_ha_state()
