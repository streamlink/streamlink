from __future__ import print_function

import logging
import re

from streamlink import PluginError
from streamlink.compat import urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import DASHStream, HLSStream

log = logging.getLogger(__name__)


class TF1(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?(?:tf1\.fr/([\w-]+)/direct|(lci).fr/direct)/?")
    api_url_base = "https://delivery.tf1.fr/mytf1-wrd/"
    token = "07e45841-a17a-47cf-af64-a42311bdcc3d"

    def api_call(self, channel, useragent=useragents.CHROME):
        url = urljoin(self.api_url_base, "L_"+channel.upper())
        req = self.session.http.get(url,
                                    params=dict(token=self.token),
                                    headers={"User-Agent": useragent})
        return self.session.http.json(req)

    def get_stream_urls(self, channel):
        for useragent in [useragents.CHROME, useragents.IPHONE_6]:
            data = self.api_call(channel, useragent)

            if data.get("error"):
                log.error("Failed to get stream for {0}: {error} ({code})".format(channel, **data))
            else:
                log.debug("Got {format} stream {url}".format(**data))
                yield data['format'], data['url']

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        m = self.url_re.match(self.url)
        if m:
            channel = m.group(1) or m.group(2)
            self.logger.debug("Found channel {0}", channel)
            for sformat, url in self.get_stream_urls(channel):
                try:
                    if sformat == "dash":
                        for s in DASHStream.parse_manifest(self.session, url, headers={"User-Agent": useragents.CHROME}).items():
                            yield s
                    if sformat == "hls":
                        for s in HLSStream.parse_variant_playlist(self.session, url).items():
                            yield s
                except PluginError as e:
                    log.error("Could not open {0} stream".format(sformat))
                    log.debug("Failed with error: {0}".format(e))

__plugin__ = TF1
