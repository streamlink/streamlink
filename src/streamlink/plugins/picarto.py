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
        channel, player_id, product, offline_image, online, token, is_flash = \
            map(lambda a: a.strip("' \""), match.group(1).split(","))
        online, is_flash = bool(int(online)), bool(int(is_flash))

        return channel, online, token, is_flash

    def _get_streams(self):
        page = http.get(self.url)

        try:
            channel, online, token, is_flash = self._get_stream_arguments(page)
        except ValueError:
            return

        self.logger.debug("Channel {} is {}, default player tech: {} with token={}",
                          channel,
                          "online" if online else "offline",
                          "RTMP" if is_flash else "HTML5",
                          token)

        if not online:
            self.logger.error("This stream is currently offline")
            return

        channel_server_res = http.post(API_CHANNEL_INFO, data={"loadbalancinginfo": channel})
        server = channel_server_res.text

        self.logger.debug("Using load balancing server: {}", server)

        return HLSStream.parse_variant_playlist(self.session,
                                                HLS_URL.format(server, channel, token),
                                                verify=False)


__plugin__ = Picarto
