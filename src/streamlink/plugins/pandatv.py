import re
import types
import time
import json

from streamlink.compat import quote
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HTTPStream

ROOM_API = "https://www.panda.tv/api_room_v3?token=&hostid={0}&roomid={1}&roomkey={2}&_={3}&param={4}&time={5}&sign={6}"
ROOM_API_V2 = "https://www.panda.tv/api_room_v2?roomid={0}&_={1}"
SD_URL_PATTERN = "https://pl{0}.live.panda.tv/live_panda/{1}.flv?sign={2}&ts={3}&rid={4}"
HD_URL_PATTERN = "https://pl{0}.live.panda.tv/live_panda/{1}_mid.flv?sign={2}&ts={3}&rid={4}"
OD_URL_PATTERN = "https://pl{0}.live.panda.tv/live_panda/{1}_small.flv?sign={2}&ts={3}&rid={4}"

_url_re = re.compile(r"http(s)?://(\w+.)?panda.tv/(?P<channel>[^/&?]+)")
_room_id_re = re.compile(r'data-room-id="(\d+)"')
_status_re = re.compile(r'"status"\s*:\s*"(\d+)"\s*,\s*"display_type"')
_room_key_re = re.compile(r'"room_key"\s*:\s*"(.+?)"')
_hostid_re = re.compile(r'\\"hostid\\"\s*:\s*\\"(.+?)\\"')
_param_re = re.compile(r'"param"\s*:\s*"(.+?)"\s*,\s*"time"')
_time_re = re.compile(r'"time"\s*:\s*(\d+)')
_sign_re = re.compile(r'"sign"\s*:\s*"(.+?)"')
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
    def can_handle_url(cls, url):
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
            hostid = _hostid_re.search(res.text).group(1)
            param = _param_re.search(res.text).group(1)
            tt = _time_re.search(res.text).group(1)
            sign = _sign_re.search(res.text).group(1)
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
        param = param.replace("\\", "")
        param = quote(param)
        url = ROOM_API.format(hostid, channel, room_key, ts, param, tt, sign)
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

        plflag_list = json.loads(plflag_list)
        backup = plflag_list["backup"]
        rid = plflag_list["auth"]["rid"]
        sign = plflag_list["auth"]["sign"]
        ts = plflag_list["auth"]["time"]

        backup.append(plflag)
        plflag0 = backup
        plflag0 = [i.split('_')[1] for i in plflag0] 

        # let wangsu cdn priority, flag can see here in "H5PLAYER_CDN_LINES":
        # https://www.panda.tv/cmstatic/global-config.js
        lines = ["3", "4"]
        try:
            plflag1 = [i for i in plflag0 if i in lines][0]
        except IndexError:
            plflag1 = plflag0[0]

        if sd == '1':
            streams['ehq'] = HTTPStream(self.session, SD_URL_PATTERN.format(plflag1, room_key, sign, ts, rid))

        if hd == '1':
            streams['hq'] = HTTPStream(self.session, HD_URL_PATTERN.format(plflag1, room_key, sign, ts, rid))

        if od == '1':
            streams['sq'] = HTTPStream(self.session, OD_URL_PATTERN.format(plflag1, room_key, sign, ts, rid))

        return streams


__plugin__ = Pandatv
