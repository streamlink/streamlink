import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import DASHStream, HLSStream

log = logging.getLogger(__name__)


class TF1(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?(?:tf1\.fr/([\w-]+)/direct|(lci).fr/direct)/?")
    api_url = "https://player.tf1.fr/mediainfocombo/{}?context=MYTF1&pver=4001000"

    def api_call(self, channel, useragent=useragents.CHROME):
        url = self.api_url.format("L_" + channel.upper())
        req = self.session.http.get(url,
                                    headers={"User-Agent": useragent})
        return self.session.http.json(req)

    def get_stream_urls(self, channel):
        for useragent in [useragents.CHROME, useragents.IPHONE_6]:
            data = self.api_call(channel, useragent)

            if 'delivery' not in data or 'url' not in data['delivery']:
                continue

            log.debug("Got {format} stream {url}".format(**data['delivery']))
            yield data['delivery']['format'], data['delivery']['url']

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        m = self.url_re.match(self.url)
        if m:
            channel = m.group(1) or m.group(2)
            log.debug("Found channel {0}".format(channel))
            for sformat, url in self.get_stream_urls(channel):
                try:
                    if sformat == "dash":
                        yield from DASHStream.parse_manifest(
                            self.session,
                            url,
                            headers={"User-Agent": useragents.CHROME}
                        ).items()
                    if sformat == "hls":
                        yield from HLSStream.parse_variant_playlist(
                            self.session,
                            url
                        ).items()
                except PluginError as e:
                    log.error("Could not open {0} stream".format(sformat))
                    log.debug("Failed with error: {0}".format(e))


__plugin__ = TF1
