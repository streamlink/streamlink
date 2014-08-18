import re

from functools import partial

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.plugin.api.utils import parse_json
from livestreamer.stream import HTTPStream, RTMPStream

BASE_VOD_URL = "https://www.connectcast.tv"
SWF_URL = "https://www.connectcast.tv/jwplayer/jwplayer.flash.swf"

_url_re = re.compile("http(s)?://(\w+\.)?connectcast.tv/")
_playlist_re = re.compile("playlist: (\[.+?\]),", re.DOTALL)
_js_to_json = partial(re.compile("(\w+):\s").sub, r'"\1":')

_playlist_schema = validate.Schema(
    validate.transform(_playlist_re.search),
    validate.any(
        None,
        validate.all(
            validate.get(1),
            validate.transform(_js_to_json),
            validate.transform(parse_json),
            [{
                "sources": [{
                    "file": validate.text,
                    validate.optional("label"): validate.text
                }]
            }]
        )
    )
)
_smil_schema = validate.Schema(
    validate.union({
        "base": validate.all(
            validate.xml_find("head/meta"),
            validate.get("base"),
            validate.url(scheme="rtmp")
        ),
        "videos": validate.all(
            validate.xml_findall("body/video"),
            [validate.get("src")]
        )
    })
)


class ConnectCast(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_smil_streams(self, url):
        res = http.get(url, verify=False)
        smil = http.xml(res, schema=_smil_schema)

        streams = {}
        for video in smil["videos"]:
            stream = RTMPStream(self.session, {
                "rtmp": smil["base"],
                "playpath": video,
                "swfVfy": SWF_URL,
                "pageUrl": self.url,
                "live": True
            })
            if streams:
                name = "live_alt"
            else:
                name = "live"

            streams[name] = stream

        return streams

    def _get_streams(self):
        playlist = http.get(self.url, schema=_playlist_schema)
        streams = {}
        for item in playlist:
            for source in item["sources"]:
                filename = source["file"]
                if filename.endswith(".smil"):
                    streams.update(self._get_smil_streams(filename))
                elif filename.startswith("/"):
                    name = source.get("label", "vod")
                    url = BASE_VOD_URL + filename
                    streams[name] = HTTPStream(self.session, url)

            break

        return streams

__plugin__ = ConnectCast
