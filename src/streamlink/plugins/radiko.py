"""
$description Japanese live radio simulcasts and time-shifted broadcasts for over 100 stations.
$url radiko.jp
$type live, vod
$region Japan
"""

import base64
import datetime
import hashlib
import random
import re
from urllib.parse import urlencode

from lxml.etree import XML

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    re.compile(r"https?://radiko\.jp/(#!/)?(?P<state>live|ts)/(?P<station_id>[a-zA-Z0-9-]+)/?(?P<start_at>\d+)?"),
)
class Radiko(Plugin):
    _api_auth_1 = "https://radiko.jp/v2/api/auth1"
    _api_auth_2 = "https://radiko.jp/v2/api/auth2"
    _auth_key = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"

    def _get_streams(self):
        state = self.match.group("state")
        station_id = self.match.group("station_id").upper()
        if state == "live":
            url, token = self._live(station_id)
        else:
            start_at = self.match.group("start_at")
            url, token = self._timefree(station_id, start_at)
        headers = {
            "X-Radiko-AuthToken": token,
        }
        self.session.http.headers = headers
        yield from HLSStream.parse_variant_playlist(self.session, url).items()

    def _live(self, station_id):
        live_url = "http://f-radiko.smartstream.ne.jp/{}/_definst_/simul-stream.stream/playlist.m3u8".format(station_id)
        token, _area_id = self._authorize()
        lsid = hashlib.md5(str(random.random()).encode("utf-8")).hexdigest()
        live_params = {
            "station_id": station_id,
            "l": 15,
            "lsid": lsid,
            "type": "b",
        }
        url = f"{live_url}?{urlencode(live_params)}"
        return url, token

    def _timefree(self, station_id, start_at):
        m3u8_url = "https://tf-rpaa.smartstream.ne.jp/tf/playlist.m3u8"
        token, _area_id = self._authorize()
        lsid = hashlib.md5(str(random.random()).encode("utf-8")).hexdigest()
        end_at = self._get_xml(start_at, station_id)
        m3u8_params = {
            "station_id": station_id,
            "start_at": start_at,
            "ft": start_at,
            "end_at": end_at,
            "to": end_at,
            "l": 15,
            "lsid": lsid,
            "type": "b",
        }
        url = f"{m3u8_url}?{urlencode(m3u8_params)}"
        return url, token

    def _authorize(self):
        headers = {
            "x-radiko-app": "pc_html5",
            "x-radiko-app-version": "0.0.1",
            "x-radiko-device": "pc",
            "x-radiko-user": "dummy_user",
        }
        self.session.http.headers.update(headers)
        r = self.session.http.get(self._api_auth_1)
        token = r.headers.get("x-radiko-authtoken")
        offset = int(r.headers.get("x-radiko-keyoffset"))
        length = int(r.headers.get("x-radiko-keylength"))
        partial_key = base64.b64encode(self._auth_key[offset : offset + length].encode("ascii")).decode("utf-8")
        headers = {
            "x-radiko-authtoken": token,
            "x-radiko-device": "pc",
            "x-radiko-partialkey": partial_key,
            "x-radiko-user": "dummy_user",
        }
        self.session.http.headers.update(headers)
        r = self.session.http.get(self._api_auth_2)
        if r.status_code == 200:
            return token, r.text.split(",")[0]

    def _get_xml(self, start_at, station_id):
        today = datetime.date(int(start_at[:4]), int(start_at[4:6]), int(start_at[6:8]))
        yesterday = today - datetime.timedelta(days=1)
        if int(start_at[8:10]) < 5:
            date = yesterday.strftime("%Y%m%d")
        else:
            date = today.strftime("%Y%m%d")
        api = "http://radiko.jp/v3/program/station/date/{}/{}.xml".format(date, station_id)
        r = self.session.http.get(api)
        tree = XML(r.content)
        for x in tree[2][0][1].findall("prog"):
            if x.attrib["ft"] == start_at:
                return x.attrib["to"]


__plugin__ = Radiko
