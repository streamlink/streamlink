from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream


class TF1(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?(?:tf1\.fr/(\w+)/direct|(lci).fr/direct)/?")
    embed_url = "http://www.wat.tv/embedframe/live{0}"
    embed_re = re.compile(r"urlLive.*?:.*?\"(http.*?)\"", re.MULTILINE)
    api_url = "http://www.wat.tv/get/{0}/591997"
    swf_url = "http://www.wat.tv/images/v70/PlayerLite.swf"
    hds_channel_remap = {"tf1": "androidliveconnect", "lci": "androidlivelci"}
    hls_channel_remap = {"lci": "LCI", "tf1": "V4"}

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_hds_streams(self, channel):
        channel = self.hds_channel_remap.get(channel, "{0}live".format(channel))
        manifest_url = http.get(self.api_url.format(channel),
                                params={"getURL": 1},
                                headers={"User-Agent": useragents.FIREFOX}).text

        for s in HDSStream.parse_manifest(self.session,
                                          manifest_url,
                                          pvswf=self.swf_url,
                                          headers={"User-Agent": useragents.FIREFOX}).items():
            yield s

    def _get_hls_streams(self, channel):
        channel = self.hls_channel_remap.get(channel, channel)
        embed_url = self.embed_url.format(channel)
        self.logger.debug("Found embed URL: {0}", embed_url)
        # page needs to have a mobile user agent
        embed_page = http.get(embed_url, headers={"User-Agent": useragents.ANDROID})

        m = self.embed_re.search(embed_page.text)
        if m:
            hls_stream_url = m.group(1)

            try:
                for s in HLSStream.parse_variant_playlist(self.session, hls_stream_url).items():
                    yield s
            except Exception:
                self.logger.error("Failed to load the HLS playlist for {0}", channel)

    def _get_streams(self):
        m = self.url_re.match(self.url)
        if m:
            channel = m.group(1) or m.group(2)
            self.logger.debug("Found channel {0}", channel)
            for s in self._get_hds_streams(channel):
                yield s

            for s in self._get_hls_streams(channel):
                yield s


__plugin__ = TF1
