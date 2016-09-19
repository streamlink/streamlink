import re
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream

SWF_URL = "https://www.connectcast.tv/jwplayer/jwplayer.flash.swf"

_url_re = re.compile("http(s)?://(\w+\.)?connectcast.tv/")
_manifest_re = re.compile(".*data-playback=\"([^\"]*)\".*")


class ConnectCast(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = _manifest_re.search(res.text)
        manifest = match.group(1)
        streams = {}
        streams.update(
            HDSStream.parse_manifest(self.session, manifest, pvswf=SWF_URL)
        )
        
        return streams

__plugin__ = ConnectCast
