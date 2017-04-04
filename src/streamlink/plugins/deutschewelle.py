import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.compat import urlparse, parse_qsl
from streamlink.stream import HLSStream


class DeutscheWelle(Plugin):
    default_channel = "1"
    url_re = re.compile(r"https?://(?:www\.)?dw\.com/en/media-center/live-tv/s-\d+")

    channel_re = re.compile(r'''<a.*?data-id="(\d+)".*?class="ici"''')
    stream_div = re.compile(r'''
        <div\s+class="mediaItem"\s+data-channel-id="(\d+)".*?>.*?
        <input\s+type="hidden"\s+name="file_name"\s+value="(.*?)"\s*>.*?<div
    ''', re.DOTALL | re.VERBOSE)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        # check if a different language has been selected
        qs = dict(parse_qsl(urlparse(self.url).query))
        channel = qs.get("channel")

        page = http.get(self.url)
        if not channel:
            m = self.channel_re.search(page.text)
            channel = m and m.group(1)

        self.logger.debug("Using sub-channel ID: {0}", channel)

        # extract the streams from the page, mapping between channel-id and stream url
        media_items = self.stream_div.finditer(page.text)
        stream_map = dict([m.groups((1, 2)) for m in media_items])

        stream_url = stream_map.get(str(channel) or self.default_channel)
        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = DeutscheWelle
