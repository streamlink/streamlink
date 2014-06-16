import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HDSStream
from livestreamer.utils import parse_xml


class ard_live(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return "live.daserste.de/" in url.lower()

    def _get_streams(self):
        self.logger.debug("Fetching stream info")

        res = http.get("http://live.daserste.de/de/livestream.xml")
        root = parse_xml(res.text.encode("utf8"))

        res = http.get(self.url)
        player_version = re.search(r"livestream\.microloader\.jsp\?v=([\d\.]+)", res.text)

        streams = {}
        for url in root.iter('streamingUrlLive'):
            if re.search('f4m', url.text):
                pvswf = 'http://live.daserste.de/lib/br-player/swf/main.swf?v={0}'.format(player_version.group(1))
                hds_streams = HDSStream.parse_manifest(self.session, url.text, pvswf=pvswf)
                streams.update(hds_streams)

        return streams


__plugin__ = ard_live
