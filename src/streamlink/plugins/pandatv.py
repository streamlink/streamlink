"""Plugin for panda.tv by Fat Deer"""

import re
import types
import time
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

ROOM_API = "http://www.panda.tv/api_room_v3?roomid={0}&roomkey={1}&_={2}"
SD_URL_PATTERN = "http://pl{0}.live.panda.tv/live_panda/{1}.flv?sign={2}&ts={3}&rid={4}"
HD_URL_PATTERN = "http://pl{0}.live.panda.tv/live_panda/{1}_mid.flv?sign={2}&ts={3}&rid={4}"
OD_URL_PATTERN = "http://pl{0}.live.panda.tv/live_panda/{1}_small.flv?sign={2}&ts={3}&rid={4}"

_url_re = re.compile(r"http(s)?://(\w+.)?panda.tv/(?P<channel>[^/&?]+)")
_sd_re = re.compile(r'"SD"\s*:\s*"(\d+)"')
_hd_re = re.compile(r'"HD"\s*:\s*"(\d+)"')
_od_re = re.compile(r'"OD"\s*:\s*"(\d+)"')
_status_re = re.compile(r'"status"\s*:\s*"(\d+)","display_type"')
_room_key_re = re.compile(r'"room_key"\s*:\s*"(.+?)"')

_room_schema = validate.Schema(
    {
        "data": validate.any(
            validate.text,
            dict,
            {
                "videoinfo": validate.any(
                    validate.text,
                    {
                        "plflag_list": validate.text,
                        "plflag": validate.text
                    }
                )
            }
        )
    },
    validate.get("data")
)

_sd_schema = validate.Schema(
    validate.all(
        validate.transform(_sd_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(int)
            )
        )
    )
)

_hd_schema = validate.Schema(
    validate.all(
        validate.transform(_hd_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(int)
            )
        )
    )
)

_od_schema = validate.Schema(
    validate.all(
        validate.transform(_od_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(int)
            )
        )
    )
)

_status_schema = validate.Schema(
    validate.all(
        validate.transform(_status_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(int)
            )
        )
    )
)

_room_key_schema = validate.Schema(
    validate.all(
        validate.transform(_room_key_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.text
            )
        )
    )
)


class Pandatv(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        status = http.get(self.url, schema=_status_schema)
        if status != 2:
            self.logger.info("Channel offline now!")
            return

        ts = int(time.time())
        room_key = http.get(self.url, schema=_room_key_schema)

        url = ROOM_API.format(channel, room_key, ts)
        res = http.get(url)
        data = http.json(res, schema=_room_schema)
        if not isinstance(data, dict):
            self.logger.info("Please Check PandaTV Room API")
            return

        videoinfo = data.get('videoinfo')
        plflag_list = videoinfo.get('plflag_list')
        if not videoinfo or not plflag_list:
            self.logger.info("Please Check PandaTV Room API")
            return

        streams = {}
        plflag = videoinfo.get('plflag')
        if not plflag or not '_' in plflag:
            self.logger.info("Please Check PandaTV Room API")
            return

        plflag = plflag.split('_')[1]

        plflag_list = json.loads(plflag_list)
        rid = plflag_list["auth"]["rid"]
        sign = plflag_list["auth"]["sign"]
        ts = plflag_list["auth"]["time"]

        sd = http.get(self.url, schema=_sd_schema)
        if sd == 1:
            streams['ehq'] = HTTPStream(self.session, SD_URL_PATTERN.format(plflag, room_key, sign, ts, rid))

        hd = http.get(self.url, schema=_hd_schema)
        if hd == 1:
            streams['hq'] = HTTPStream(self.session, HD_URL_PATTERN.format(plflag, room_key, sign, ts, rid))

        od = http.get(self.url, schema=_od_schema)
        if od == 1:
            streams['sq'] = HTTPStream(self.session, OD_URL_PATTERN.format(plflag, room_key, sign, ts, rid))

        return streams


__plugin__ = Pandatv
