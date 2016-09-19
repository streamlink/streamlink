import re
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream

_url_re = re.compile("(http(s)?://(\w+\.)?antenna.gr)/webtv/watch\?cid=.+")
_playlist_re = re.compile("playlist:\s*\"(/templates/data/jplayer\?cid=[^\"]+)")
_manifest_re = re.compile("jwplayer:source\s+file=\"([^\"]+)\"")
_swf_re = re.compile("<jwplayer:provider>(http[^<]+)</jwplayer:provider>")

class Antenna(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):

        # Discover root
        match = _url_re.search(self.url)
        root = match.group(1)

        # Download main URL
        res = http.get(self.url)

        # Find playlist
        match = _playlist_re.search(res.text)
        playlist_url = root + match.group(1) + "d"

        # Download playlist
        res = http.get(playlist_url)

        # Find manifest
        match = _manifest_re.search(res.text)
        manifest_url = match.group(1)

        # Find SWF
        match = _swf_re.search(res.text)
        swf_url = match.group(1);

        streams = {}
        streams.update(
            HDSStream.parse_manifest(self.session, manifest_url, pvswf=swf_url)
        )
        
        return streams

__plugin__ = Antenna
