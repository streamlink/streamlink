"""
$description French live TV channels from TF1 Group, including LCI and TF1.
$url tf1.fr
$url lci.fr
$type live
$region France
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import useragents
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?(?:tf1\.fr/(?P<live>[\w-]+)/direct/?|(?P<lci>tf1info|lci)\.fr/direct/?|tf1.fr/stream/(?P<stream>[\w-]+))"
))
class TF1(Plugin):
    api_url = "https://mediainfo.tf1.fr/mediainfocombo/{}?context=MYTF1&pver=4001000"

    def api_call(self, channel_id, useragent=useragents.CHROME):
        url = self.api_url.format(channel_id)
        req = self.session.http.get(url,
                                    headers={"User-Agent": useragent})
        return self.session.http.json(req)

    def get_stream_urls(self, channel_id):
        for useragent in [useragents.CHROME, useragents.IPHONE_6]:
            data = self.api_call(channel_id, useragent)

            if 'delivery' not in data or 'url' not in data['delivery']:
                continue

            log.debug("Got {format} stream {url}".format(**data['delivery']))
            yield data['delivery']['format'], data['delivery']['url']

    def _get_streams(self):
        m = self.match
        if m:
            channel = ""
            channel_id = ""
            if m.group("live"):
                channel = m.group("live")
                channel_id = "L_" + channel.upper()
            elif m.group("lci"):
                channel = "LCI"
                channel_id = "L_LCI"
            elif m.group("stream"):
                channel = m.group("stream")
                channel_id = "L_FAST_v2l-" + m.group("stream")
            log.debug("Found channel {0}".format(channel))
            for sformat, url in self.get_stream_urls(channel_id):
                try:
                    if sformat == "dash":
                        if m.group("stream") is not None:
                            # DASH stream is invalid for 'stream' live
                            log.debug("TF1 'Stream' channel, DASH skipped")
                        else:
                            yield from DASHStream.parse_manifest(
                                self.session,
                                url,
                                headers={"User-Agent": useragents.CHROME}
                            ).items()
                    if sformat == "hls":
                        yield from HLSStream.parse_variant_playlist(
                            self.session,
                            url,
                            headers={"User-Agent": useragents.IPHONE},
                        ).items()
                except PluginError as e:
                    log.error("Could not open {0} stream".format(sformat))
                    log.debug("Failed with error: {0}".format(e))


__plugin__ = TF1
