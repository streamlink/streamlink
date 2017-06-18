import re

from streamlink.compat import urlparse, parse_qsl, urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.stream import RTMPStream

_url_re = re.compile(r"http(s)?://(\w+.)?beam.pro/(?P<channel>[^/?]+)")


class Beam(Plugin):
    api_url = "https://beam.pro/api/v1/{type}/{id}"
    channel_manifest = "https://beam.pro/api/v1/channels/{id}/manifest.{type}"

    _vod_schema = validate.Schema({
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
    _assets_schema = validate.Schema(
        validate.union({
            "base": validate.all(
                validate.xml_find("./head/meta"),
                validate.get("base"),
                validate.url(scheme="rtmp")
            ),
            "videos": validate.all(
                validate.xml_findall(".//video"),
                [
                    validate.union({
                        "src": validate.all(
                            validate.get("src"),
                            validate.text
                        ),
                        "height": validate.all(
                            validate.get("height"),
                            validate.text,
                            validate.transform(int)
                        )
                    })
                ]
            )
        })
    )

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_vod_stream(self, vod_id):
        res = http.get(self.api_url.format(type="recordings", id=vod_id))
        for sdata in http.json(res, schema=self._vod_schema):
            if sdata["format"] == "hls":
                hls_url = urljoin(sdata["url"], "manifest.m3u8")
                yield "{0}p".format(sdata["height"]), HLSStream(self.session, hls_url)
            elif sdata["format"] == "raw":
                raw_url = urljoin(sdata["url"], "source.mp4")
                yield "{0}p".format(sdata["height"]), HTTPStream(self.session, raw_url)

    def _get_live_stream(self, channel):
        res = http.get(self.api_url.format(type="channels", id=channel))
        channel_info = http.json(res)

        if not channel_info["online"]:
            return

        res = http.get(self.channel_manifest.format(id=channel_info["id"], type="smil"))
        assets = http.xml(res, schema=self._assets_schema)

        for video in assets["videos"]:
            name = "{0}p".format(video["height"])
            stream = RTMPStream(self.session, {
                "rtmp": "{0}/{1}".format(assets["base"], video["src"])
            })
            yield name, stream

        for s in HLSStream.parse_variant_playlist(self.session,
                                                  self.channel_manifest.format(id=channel_info["id"], type="m3u8")).items():
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


__plugin__ = Beam
