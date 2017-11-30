"""
    Mixer API 1.0 documentation
    https://dev.mixer.com/rest.html
"""
import re

from streamlink import NoStreamsError
from streamlink.compat import urlparse, parse_qsl, urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

_url_re = re.compile(r"http(s)?://(\w+.)?mixer\.com/(?P<channel>[^/?]+)")


class Mixer(Plugin):
    api_url = "https://mixer.com/api/v1/{type}/{id}"

    _vod_schema = validate.Schema(
        {
            "state": "AVAILABLE",
            "vods": [{
                "baseUrl": validate.url(),
                "data": validate.any(None, {
                    "Height": int
                }),
                "format": validate.text
            }]
        },
        validate.get("vods"),
        validate.filter(lambda x: x["format"] in ("raw", "hls")),
        [validate.union({
            "url": validate.get("baseUrl"),
            "format": validate.get("format"),
            "height": validate.all(validate.get("data"), validate.get("Height"))
        })])

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_api_res(self, api_type, api_id):
        try:
            res = http.get(self.api_url.format(type=api_type, id=api_id))
            return res
        except Exception as e:
            if "404" in str(e):
                self.logger.error("invalid {0} - {1}".format(api_type, api_id))
            elif "429" in str(e):
                self.logger.error("Too Many Requests, API rate limit exceeded.")
            raise NoStreamsError(self.url)

    def _get_vod_stream(self, vod_id):
        res = self._get_api_res("recordings", vod_id)

        for sdata in http.json(res, schema=self._vod_schema):
            if sdata["format"] == "hls":
                hls_url = urljoin(sdata["url"], "manifest.m3u8")
                yield "{0}p".format(sdata["height"]), HLSStream(self.session, hls_url)

    def _get_live_stream(self, channel):
        res = self._get_api_res("channels", channel)

        channel_info = http.json(res)
        if not channel_info["online"]:
            return

        user_id = channel_info["id"]
        hls_url = self.api_url.format(type="channels", id="{0}/manifest.m3u8".format(user_id))
        for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
            yield s

    def _get_streams(self):
        params = dict(parse_qsl(urlparse(self.url).query))
        vod_id = params.get("vod")
        match = _url_re.match(self.url)
        channel = match.group("channel")

        if vod_id:
            self.logger.debug("Looking for VOD {0} from channel: {1}", vod_id, channel)
            return self._get_vod_stream(vod_id)
        else:
            self.logger.debug("Looking for channel: {0}", channel)
            return self._get_live_stream(channel)


__plugin__ = Mixer
