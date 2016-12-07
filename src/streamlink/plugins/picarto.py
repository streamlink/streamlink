import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream
from streamlink.stream import RTMPStream

API_CHANNEL_INFO = "https://picarto.tv/process/channel"
RTMP_URL = "rtmp://{}:1935/play/"
RTMP_PLAYPATH = "golive+{}?token={}"
HLS_URL = "https://{}/hls/{}/index.m3u8?token={}"

_url_re = re.compile(r"""
    https?://(\w+\.)?picarto\.tv/[^&?/]
""", re.VERBOSE)

# placeStream(channel, playerID, product, offlineImage, online, token, tech)
_channel_casing_re = re.compile(r"""
    <script>\s*placeStream\s*\((.*?)\);?\s*</script>
""", re.VERBOSE)


class Picarto(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url) is not None

    @staticmethod
    def _get_stream_arguments(page):
        match = _channel_casing_re.search(page.text)
        if not match:
            raise ValueError

        # transform the arguments
        channel, player_id, product, offline_image, online, visibility, is_flash = \
            map(lambda a: a.strip("' \""), match.group(1).split(","))
        player_id, product, offline_image, online, is_flash = \
            map(lambda a: bool(int(a)), [player_id, product, offline_image, online, is_flash])

        return channel, player_id, product, offline_image, online, visibility, is_flash

    def _get_streams(self):
        page = http.get(self.url)

        try:
            channel, _, _, _, online, visibility, is_flash = self._get_stream_arguments(page)
        except ValueError:
            return

        if not online:
            self.logger.error("This stream is currently offline")
            return

        channel_server_res = http.post(API_CHANNEL_INFO, data={
            "loadbalancinginfo": channel
        })

        if is_flash:
            return {"live": RTMPStream(self.session, {
                "rtmp": RTMP_URL.format(channel_server_res.text),
                "playpath": RTMP_PLAYPATH.format(channel, visibility),
                "pageUrl": self.url,
                "live": True
            })}
        else:
            return HLSStream.parse_variant_playlist(self.session,
                                                    HLS_URL.format(channel_server_res.text, channel, visibility),
                                                    verify=False)

__plugin__ = Picarto
