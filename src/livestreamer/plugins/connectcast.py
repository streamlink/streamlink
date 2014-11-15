import re
import json

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HTTPStream, RTMPStream

from livestreamer.plugin.api.support_plugin import common_jwplayer as jwplayer

BASE_VOD_URL = "https://www.connectcast.tv"
SWF_URL = "https://www.connectcast.tv/jwplayer/jwplayer.flash.swf"

_url_re = re.compile("http(s)?://(\w+\.)?connectcast.tv/")

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

        for video in smil["videos"]:
            stream = RTMPStream(self.session, {
                "rtmp": smil["base"],
                "playpath": video,
                "swfVfy": SWF_URL,
                "pageUrl": self.url,
                "live": True
            })
            yield "live", stream

    def _get_streams(self):
        res = http.get(self.url)

        # temporary fix until the jwplayer-parser works for this site again
        # refer to: https://github.com/chrippa/livestreamer/issues/588
        #
        # not working:
        # playlist = jwplayer.parse_playlist(res)

        playlist = re.compile(r"playlist: (\[{.*?}\]),", re.DOTALL + re.IGNORECASE).search(res.content).group(1).strip()
        playlist = playlist.replace('sources:', '"sources":')
        playlist = playlist.replace('file:', '"file":')
        playlist = json.loads(playlist)
        
        if not playlist:
            return

        for item in playlist:
            for source in item["sources"]:
                filename = source["file"]
                if filename.endswith(".smil"):
                    # TODO: Replace with "yield from" when dropping Python 2.
                    for stream in self._get_smil_streams(filename):
                        yield stream
                elif filename.startswith("/"):
                    name = source.get("label", "vod")
                    url = BASE_VOD_URL + filename
                    yield name, HTTPStream(self.session, url)

            break

__plugin__ = ConnectCast
