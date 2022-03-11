"""
$description Live TV channels and video on-demand service from ORF, an Austrian public, state-owned broadcaster.
$url tvthek.orf.at
$type live, vod
"""

import json
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.stream.hls import HLSStream

_json_re = re.compile(r'<div class="jsb_ jsb_VideoPlaylist" data-jsb="(?P<json>[^"]+)">')

MODE_STREAM, MODE_VOD = 0, 1


@pluginmatcher(re.compile(
    r"https?://tvthek\.orf\.at/(index\.php/)?live/(?P<title>[^/]+)/(?P<id>\d+)"
))
@pluginmatcher(re.compile(r"""
    https?://tvthek\.orf\.at/pro(gram|file)
    /(?P<showtitle>[^/]+)/(?P<showid>\d+)
    /(?P<episodetitle>[^/]+)/(?P<epsiodeid>\d+)
    (/(?P<segmenttitle>[^/]+)/(?P<segmentid>\d+))?
""", re.VERBOSE))
class ORFTVThek(Plugin):
    def _get_streams(self):
        if self.matches[0]:
            mode = MODE_STREAM
        else:
            mode = MODE_VOD

        res = self.session.http.get(self.url)
        match = _json_re.search(res.text)
        if match:
            data = json.loads(_json_re.search(res.text).group('json').replace('&quot;', '"'))
        else:
            raise PluginError("Could not extract JSON metadata")

        streams = {}
        try:
            if mode == MODE_STREAM:
                sources = data['playlist']['videos'][0]['sources']
            elif mode == MODE_VOD:
                sources = data['selected_video']['sources']
        except (KeyError, IndexError):
            raise PluginError("Could not extract sources")

        for source in sources:
            try:
                if source['delivery'] != 'hls':
                    continue
                url = source['src'].replace(r'\/', '/')
            except KeyError:
                continue
            stream = HLSStream.parse_variant_playlist(self.session, url)
            # work around broken HTTP connection persistence by acquiring a new connection
            self.session.http.close()
            streams.update(stream)

        return streams


__plugin__ = ORFTVThek
