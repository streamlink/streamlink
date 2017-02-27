# -*- coding: utf-8 -*-
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream, HLSStream

_url_re = re.compile(r'''^https?://
        (?:\w*.)?
        showroom-live.com/
        (?:
            (?P<room_title>\w+$)
            |
            room/profile\?room_id=(?P<room_id>\d+)$
        )
''', re.VERBOSE)

_room_id_re = re.compile(r'"roomId":(?P<room_id>\d+),')

_api_status_url = 'https://www.showroom-live.com/room/is_live?room_id={room_id}'
_api_data_url = 'https://www.showroom-live.com/room/get_live_data?room_id={room_id}'

_api_status_schema = validate.Schema(
    {
        "ok": int
    }
)
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
        "streaming_url_list": validate.all([
            {
                "url": validate.text,
                "id": int,
                "label": validate.text,
                "default": int
            }
        ]),
        "is_live": int
    }
)
_rtmp_quality_lookup = {
    "オリジナル画質": "original",
    "original spec": "original",
    "低画質": "low",
    "low spec": "low"
}
# original is usually 360p, but may also be 720p, 398p, or 198p
# regardless it is the best quality available at the time
_quality_weights = {
    "original": 720,
    "other": 360,
    "low": 198
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
        self.room_id = self._find_room_id()

    def _find_room_id(self):
        match_dict = _url_re.match(self.url).groupdict()
        if not match_dict:
            return '0'
        if match_dict['room_id'] is not None:
            return match_dict['room_id']
        else:
            res = http.get(self.url)
            match = _room_id_re.search(res.text)
            if not match:
                return '0'
            return match.group('room_id')

    def _get_stream_info(self):
        res = http.get(_api_data_url.format(room_id=self.room_id))
        return http.json(res, schema=_api_data_schema)

    def _get_hls_stream(self, stream_info):
        hls_url = stream_info['url']
        return HLSStream.parse_variant_playlist(self.session,
                                                hls_url,
                                                name_key='pixels')

    def _get_rtmp_stream(self, stream_info):
        rtmp_url = '/'.join((stream_info['url'], stream_info['stream_name']))
        quality = _rtmp_quality_lookup.get(stream_info['label'], "other")

        params = dict(rtmp=rtmp_url, live=True)
        return quality, RTMPStream(self.session, params=params)

    def _get_streams(self):
        self.logger.debug("Getting streams for {0}".format(self.url.rsplit('/', 1)[1]))
        info = self._get_stream_info()
        if not info or not info['is_live']:
            return

        for stream_info in info.get("streaming_url_list_rtmp", []):
            yield self._get_rtmp_stream(stream_info)

        for stream_info in info.get("streaming_url_list", []):
            streams = self._get_hls_stream(stream_info)

            # TODO: Replace with "yield from" when dropping Python 2.
            for stream in streams.items():
                yield stream


__plugin__ = Showroom
