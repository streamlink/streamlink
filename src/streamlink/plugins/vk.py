import json
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.compat import urlparse, unquote
from streamlink.stream import HTTPStream, HLSStream
from streamlink.utils import parse_json, update_scheme
from streamlink.utils.crypto import unpad_pkcs5

class VK(Plugin):
    _url_re = re.compile(r"http(?:s)?://(\w+\.)?vk.com/video-[0-9]*_[0-9]*")
    _url_catalog_re = re.compile(r"http(?:s)?://(\w+\.)?vk.com/videos-[0-9]*")
    _livestream_sources_re = re.compile(r"<source src=\\\"(.*?)\\\" type=\\\"application\\\/vnd\.apple\.mpegurl\\\">")
    _vod_sources_re = re.compile(r"<source src=\\\"(.*?)\\\" type=\\\"video\\\/mp4\\\">")
    _vod_quality_re = re.compile(r"\.([0-9]*?)\.mp4")

    @classmethod
    def can_handle_url(cls, url):
        if cls._url_catalog_re.match(url) is not None:
            url = cls.follow_vk_redirect(url)
            if url is None:
                return False
        return cls._url_re.match(url) is not None

    @classmethod
    def follow_vk_redirect(cls, url):
        # If this is a 'videos' catalog URL with an video ID in the GET request, get that instead
        parsed_url = urlparse(url)
        if parsed_url.path.startswith('/videos-'):
            query = {v[0]:v[1] for v in [q.split('=') for q in parsed_url.query.split('&')] if v[0] == 'z'}
            try:
                true_path = unquote(query['z']).split('/')[0]
                return parsed_url.scheme + '://' + parsed_url.netloc + '/' + true_path
            except KeyError:
                # No redirect found in query string, so return the catalog url and fail later
                return url
        else:
            return url

    def _get_streams(self):
        """
        Find the streams for vk.com
        :return:
        """
        # If this is a 'videos' catalog URL with an video ID in the GET request, get that instead
        url = self.follow_vk_redirect(self.url)
        if url != self.url:
            self.logger.debug('Grabbing data from real video page at {}', url)

        headers = {}
        res = http.get(url, headers=headers)
        headers["Referer"] = url

        # Try and find an HLS source (livestream)
        stream_urls = self._livestream_sources_re.findall(res.text)
        if len(stream_urls):
            stream_url = stream_urls[0].replace('\/', '/')
            self.logger.debug("Found live stream at {}", stream_url)
            try:
                # try to parse the stream as a variant playlist
                variant = HLSStream.parse_variant_playlist(self.session, stream_url, headers=headers)
                if variant:
                    for q, s in variant.items():
                        yield q, s
                else:
                    # and if that fails, try it as a plain HLS stream
                    yield 'live', HLSStream(self.session, stream_url, headers=headers)
            except IOError:
                self.logger.warning("Could not open the stream, perhaps the channel is offline")
            return

        # Try and find a set of MP4 sources (VOD)
        vod_urls = self._vod_sources_re.findall(res.text)
        if len(vod_urls):
            vod_urls = [v.replace('\/', '/') for v in vod_urls]
            # Try to get quality from URL
            qualities = {}
            for s in vod_urls:
                q = self._vod_quality_re.findall(s)
                if not len(q):
                    break
                qualities[s] = q[0]

            try:
                if len(qualities) == len(vod_urls):
                    for s in vod_urls:
                        yield qualities[s] + 'p', HTTPStream(self.session, s)
                else:
                    # Fall back to numerical ranking
                    for q, s in enumerate(vod_urls):
                        yield str(q), HTTPStream(self.session, s)
            except IOError:
                self.logger.warning("Could not open the stream, perhaps the channel is offline")

__plugin__ = VK
