"""Plugin for panda.tv by Fat Deer"""

import re
import types
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HTTPStream

ROOM_API = "http://www.panda.tv/api_room?roomid="
SD_URL_PATTERN = "http://pl{0}.live.panda.tv/live_panda/{1}.flv"
HD_URL_PATTERN = "http://pl{0}.live.panda.tv/live_panda/{1}_mid.flv"
# I don't know ordinary-definition url pattern, sorry for ignore it.
OD_URL_PATTERN = "http://pl{0}.live.panda.tv/live_panda/{1}_mid.flv"

_url_re = re.compile("http(s)?://(\w+.)?panda.tv/(?P<channel>[^/&?]+)")

_room_schema = validate.Schema(
        {
            "data": validate.any(
                validate.text,
                dict,
                {
                    "videoinfo": validate.any(
                        validate.text,
                        {
                            "room_key": validate.text,
                            "plflag": validate.text,
                            "status": validate.text,
                            "stream_addr": {
                                "HD": validate.text,
                                "OD": validate.text,
                                "SD": validate.text
                            }
                        }
                    )
                }
            )
        },
        validate.get("data"))


class pandatv(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        url = ROOM_API + channel
        res = http.get(url)
        data = http.json(res, schema=_room_schema)
        if type(data) is not types.DictionaryType or data['videoinfo']['status'] != "2":
            return

        streams = {}
        plflag = data['videoinfo']['plflag'].split('_')[1]
        room_key = data['videoinfo']['room_key']

        # SD(Super high Definition) has higher quality than HD(High Definition) which
        # conflict with existing code, use ehq and hq instead.
        if data['videoinfo']['stream_addr']['SD'] == '1':
            streams['ehq'] = HTTPStream(self.session, SD_URL_PATTERN.format(plflag, room_key))

        if data['videoinfo']['stream_addr']['HD'] == '1':
            streams['hq'] = HTTPStream(self.session, HD_URL_PATTERN.format(plflag, room_key))

        return streams

__plugin__ = pandatv

