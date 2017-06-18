"""Plugin for panda.tv by Fat Deer"""

import re
import types
import time
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

ROOM_API = "http://www.panda.tv/api_room_v3?roomid={0}&roomkey={1}&_={2}"
ROOM_API_V2 = "http://www.panda.tv/api_room_v2?roomid={0}&_={1}"
SD_URL_PATTERN = "http://pl{0}.live.panda.tv/live_panda/{1}.flv?sign={2}&ts={3}&rid={4}"
HD_URL_PATTERN = "http://pl{0}.live.panda.tv/live_panda/{1}_mid.flv?sign={2}&ts={3}&rid={4}"
OD_URL_PATTERN = "http://pl{0}.live.panda.tv/live_panda/{1}_small.flv?sign={2}&ts={3}&rid={4}"

_url_re = re.compile(r"http(s)?://(\w+.)?panda.tv/(?P<channel>[^/&?]+)")
_room_id_re = re.compile(r'data-room-id="(\d+)"')
_status_re = re.compile(r'"status"\s*:\s*"(\d+)"\s*,\s*"display_type"')
_room_key_re = re.compile(r'"room_key"\s*:\s*"(.+?)"')
_sd_re = re.compile(r'"SD"\s*:\s*"(\d+)"')
_hd_re = re.compile(r'"HD"\s*:\s*"(\d+)"')
_od_re = re.compile(r'"OD"\s*:\s*"(\d+)"')

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
    validate.get("data"))


class Pandatv(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        res = http.get(self.url)

        try:
            channel = int(channel)
        except ValueError:
            channel = _room_id_re.search(res.text).group(1)
            ts = int(time.time())
            url = ROOM_API_V2.format(channel, ts)
            res = http.get(url)

        try:
            status = _status_re.search(res.text).group(1)
            room_key = _room_key_re.search(res.text).group(1)
            sd = _sd_re.search(res.text).group(1)
            hd = _hd_re.search(res.text).group(1)
            od = _od_re.search(res.text).group(1)
        except AttributeError:
            self.logger.info("Not a valid room url.")
            return

        if status != '2':
            self.logger.info("Stream currently unavailable.")
            return

        ts = int(time.time())
        url = ROOM_API.format(channel, room_key, ts)
        room = http.get(url)
        data = http.json(room, schema=_room_schema)
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
        if not plflag or '_' not in plflag:
            self.logger.info("Please Check PandaTV Room API")
            return

        plflag0 = plflag.split('_')[1]
        if plflag0 != '3':
            plflag1 = '4'
        else:
            plflag1 = '3'

        plflag_list = json.loads(plflag_list)
        rid = plflag_list["auth"]["rid"]
        sign = plflag_list["auth"]["sign"]
        ts = plflag_list["auth"]["time"]

        if sd == '1':
            streams['ehq'] = HTTPStream(self.session, SD_URL_PATTERN.format(plflag1, room_key, sign, ts, rid))

        if hd == '1':
            streams['hq'] = HTTPStream(self.session, HD_URL_PATTERN.format(plflag1, room_key, sign, ts, rid))

        if od == '1':
            streams['sq'] = HTTPStream(self.session, OD_URL_PATTERN.format(plflag1, room_key, sign, ts, rid))

        return streams


__plugin__ = Pandatv
