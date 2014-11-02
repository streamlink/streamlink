import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream, HLSStream

CHANNEL_INFO_URL = "http://live.afreeca.com:8057/api/get_broad_state_list.php"
KEEP_ALIVE_URL = "{server}/stream_keepalive.html"
STREAM_INFO_URLS = {
    "rtmp": "http://sessionmanager01.afreeca.tv:6060/broad_stream_assign.html",
    "hls": "http://resourcemanager.afreeca.tv:9090/broad_stream_assign.html"
}

CHANNEL_RESULT_ERROR = 0
CHANNEL_RESULT_OK = 1


_url_re = re.compile("http(s)?://(\w+\.)?afreeca.com/(?P<username>\w+)")

_channel_schema = validate.Schema(
    {
        "CHANNEL": {
            "RESULT": validate.transform(int),
            "BROAD_INFOS": [{
                "list": [{
                    "nBroadNo": validate.text
                }]
            }]
        }
    },
    validate.get("CHANNEL")
)
_stream_schema = validate.Schema(
    {
        validate.optional("view_url"): validate.url(
            scheme=validate.any("rtmp", "http")
        )
    }
)


class AfreecaTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_channel_info(self, username):
        headers = {
            "Referer": self.url
        }
        data = {
            "uid": username
        }
        res = http.post(CHANNEL_INFO_URL, data=data, headers=headers)

        return http.json(res, schema=_channel_schema)

    def _get_stream_info(self, broadcast, type):
        params = {
            "return_type": "gs_cdn",
            "broad_key": "{broadcast}-flash-hd-{type}".format(**locals())
        }
        res = http.get(STREAM_INFO_URLS[type], params=params)
        return http.json(res, schema=_stream_schema)

    def _get_hls_stream(self, broadcast):
        info = self._get_stream_info(broadcast, "hls")
        if "view_url" in info:
            return HLSStream(self.session, info["view_url"])

    def _get_rtmp_stream(self, broadcast):
        info = self._get_stream_info(broadcast, "rtmp")
        if "view_url" in info:
            params = dict(rtmp=info["view_url"])
            return RTMPStream(self.session, params=params, redirect=True)

    def _get_streams(self):
        match = _url_re.match(self.url)
        username = match.group("username")

        channel = self._get_channel_info(username)
        if channel["RESULT"] != CHANNEL_RESULT_OK:
            return

        broadcast = channel["BROAD_INFOS"][0]["list"][0]["nBroadNo"]
        if not broadcast:
            return

        flash_stream = self._get_rtmp_stream(broadcast)
        if flash_stream:
            yield "live", flash_stream

        mobile_stream = self._get_hls_stream(broadcast)
        if mobile_stream:
            yield "live", mobile_stream


__plugin__ = AfreecaTV
