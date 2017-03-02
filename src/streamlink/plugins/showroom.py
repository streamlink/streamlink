# -*- coding: utf-8 -*-
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream

_url_re = re.compile(r'''^https?://
        (?:\w*.)?
        showroom-live.com/
        (?:
            (?P<room_title>[\w-]+$)
            |
            room/profile\?room_id=(?P<room_id>\d+)$
        )
''', re.VERBOSE)

_room_id_re = re.compile(r'"roomId":(?P<room_id>\d+),')
_room_id_alt_re = re.compile(r'content="showroom:///room\?room_id=(?P<room_id>\d+)"')
_room_id_lookup_failure_log = 'Failed to find room_id for {0} using {1} regex'

_api_status_url = 'https://www.showroom-live.com/room/is_live?room_id={room_id}'
_api_data_url = 'https://www.showroom-live.com/room/get_live_data?room_id={room_id}'

_api_data_schema = validate.Schema(
    {
        "streaming_url_list_rtmp": validate.all([
            {
                "url": validate.text,
                "stream_name": validate.text,
                "id": int,
                "label": validate.text,
                "is_default": int
            }
        ]),
        "is_live": int,
        "room": {
            "room_url_key": validate.text
        },
        "telop": validate.any(None, validate.text)
    }
)
_rtmp_quality_lookup = {
    "オリジナル画質": "high",
    "original spec": "high",
    "低画質": "low",
    "low spec": "low"
}
# changes here must also be updated in test_plugin_showroom
_quality_weights = {
    "high": 720,
    "other": 360,
    "low": 160
}
# pages that definitely aren't rooms
_info_pages = set((
    "onlive",
    "campaign",
    "timetable",
    "event",
    "news",
    "article",
    "ranking",
    "follow",
    "search",
    "mypage",
    "payment",
    "user",
    "notice",
    "s",
    "organizer_registration",
    "lottery"
))


class Showroom(Plugin):
    @staticmethod
    def _get_stream_info(room_id):
        res = http.get(_api_data_url.format(room_id=room_id))
        return http.json(res, schema=_api_data_schema)

    @classmethod
    def can_handle_url(cls, url):
        match = _url_re.match(url)
        if not match or match.group("room_title") in _info_pages:
            return False
        return True

    @classmethod
    def stream_weight(cls, stream):
        if stream in _quality_weights:
            return _quality_weights.get(stream), "quality"

        return Plugin.stream_weight(stream)

    def __init__(self, url):
        Plugin.__init__(self, url)
        self._room_id = None
        self._info = None
        self._title = None

    @property
    def telop(self):
        if self._info:
            return self._info['telop']
        else:
            return ""

    @property
    def room_id(self):
        if self._room_id is None:
            self._room_id = self._get_room_id()
        return self._room_id

    def _get_room_id(self):
        """
        Locates unique identifier ("room_id") for the room.

        Returns the room_id as a string, or None if no room_id was found
        """
        match_dict = _url_re.match(self.url).groupdict()

        if match_dict['room_id'] is not None:
            return match_dict['room_id']
        else:
            res = http.get(self.url)
            match = _room_id_re.search(res.text)
            if not match:
                title = self.url.rsplit('/', 1)[-1]
                self.logger.debug(_room_id_lookup_failure_log.format(title, 'primary'))
                match = _room_id_alt_re.search(res.text)
                if not match:
                    self.logger.debug(_room_id_lookup_failure_log.format(title, 'secondary'))
                    return  # Raise exception?
            return match.group('room_id')

    def _get_title(self):
        if self._title is None:
            if 'profile?room_id=' not in self.url:
                self._title = self.url.rsplit('/', 1)[-1]
            else:
                if self._info is None:
                    # TODO: avoid this
                    self._info = self._get_stream_info(self.room_id)
                self._title = self._info.get('room').get('room_url_key')
        return self._title

    def _get_rtmp_stream(self, stream_info):
        rtmp_url = '/'.join((stream_info['url'], stream_info['stream_name']))
        quality = _rtmp_quality_lookup.get(stream_info['label'], "other")

        params = dict(rtmp=rtmp_url, live=True)
        return quality, RTMPStream(self.session, params=params)

    def _get_streams(self):
        self._info = self._get_stream_info(self.room_id)
        if not self._info or not self._info['is_live']:
            return

        self.logger.debug("Getting streams for {0}".format(self._get_title()))

        for stream_info in self._info.get("streaming_url_list_rtmp", []):
            yield self._get_rtmp_stream(stream_info)


__plugin__ = Showroom
