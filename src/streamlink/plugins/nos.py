"""Plugin for NOS: Nederlandse Omroep Stichting

Supports:
   MP$: http://nos.nl/uitzending/nieuwsuur.html
   Live: http://www.nos.nl/livestream/*
   Tour: http://nos.nl/tour/live
"""
import logging
import re

from streamlink.compat import urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class NOS(Plugin):
    _url_re = re.compile(r"https?://(?:\w+\.)?nos.nl/")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _resolve_stream(self):
        res = self.session.http.get(self.url)
        for video in itertags(res.text, 'video'):
            stream_url = video.attributes.get("data-stream")
            log.debug("Stream data: {0}".format(stream_url))
            return HLSStream.parse_variant_playlist(self.session, stream_url)

    def _get_source_streams(self):
        res = self.session.http.get(self.url)

        for atag in itertags(res.text, 'a'):
            if "video-play__link" in atag.attributes.get("class", ""):
                href = urljoin(self.url, atag.attributes.get("href"))
                log.debug("Loading embedded video page")
                vpage = self.session.http.get(href, params=dict(ajax="true", npo_cc_skip_wall="true"))
                for source in itertags(vpage.text, 'source'):
                    return HLSStream.parse_variant_playlist(self.session, source.attributes.get("src"))

    def _get_streams(self):
        if "/livestream/" in self.url or "/tour/" in self.url:
            log.debug("Finding live streams")
            return self._resolve_stream()
        else:
            log.debug("Finding VOD streams")
            return self._get_source_streams()


__plugin__ = NOS
