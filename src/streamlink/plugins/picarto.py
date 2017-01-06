from __future__ import print_function

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream
from streamlink.stream import RTMPStream


class Picarto(Plugin):
    API_CHANNEL_INFO = "https://picarto.tv/process/channel"
    RTMP_URL = "rtmp://{server}:1935/play/"
    RTMP_PLAYPATH = "golive+{channel}?token={token}"
    HLS_URL = "https://{server}/hls/{channel}/index.m3u8?token={token}"

    _url_re = re.compile(r"""
        https?://(?:\w+\.)?picarto\.tv/([^&?/]+)
    """, re.VERBOSE)

    # divs with tech_switch class
    _tech_switch_re = re.compile(r"""
    <div\s+class=".*?tech_switch.*?"(.*?)>
    """, re.VERBOSE)
    # placeStream(channel, playerID, product, offlineImage, online, token, tech)
    _place_stream_re = re.compile(r"""
        <script>\s*placeStream\s*\((.*?)\);?\s*</script>
    """, re.VERBOSE)

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @classmethod
    def _stream_online(cls, page):
        match = cls._place_stream_re.search(page.text)
        if match:
            return match.group(1).split(",")[4].strip() == "1"
        return False

    @classmethod
    def _get_steam_list(cls, page):
        for match in cls._tech_switch_re.findall(page.text):
            args = {}
            for attr in match.strip().split(" "):
                key, value = attr.split("=")
                _, key = key.split("-")
                args[key] = value.strip('"')
            yield args

    def _create_hls_stream(self, server, args):
        streams = HLSStream.parse_variant_playlist(self.session,
                                                   self.HLS_URL.format(server=server, **args),
                                                   verify=False)
        if len(streams) > 1:
            self.logger.debug("Multiple HLS streams found")
            return streams
        elif len(streams) == 0:
            self.logger.warning("No HLS streams found when expected")
            return {}
        else:
            # one HLS streams, rename it to live
            return {"live": list(streams.values())[0]}

    def _create_flash_stream(self, server, args):
        params = {
            "rtmp": self.RTMP_URL.format(server=server),
            "playpath": self.RTMP_PLAYPATH.format(**args)
        }
        return RTMPStream(self.session, params=params)

    def _get_streams(self):
        page = http.get(self.url)

        page_channel = self._url_re.match(self.url).group(1)

        if "does not exist" in page.text:
            self.logger.error("The channel {0} does not exist".format(page_channel))
            return

        if not self._stream_online(page):
            self.logger.error("The channel {0} is currently offline".format(page_channel))
            return

        server = None
        streams = list(self._get_steam_list(page))
        multi = False

        for args in streams:
            channel, tech, token = args["channel"], args["tech"], args["token"]
            if channel.lower() != page_channel.lower():
                if not multi:
                    self.logger.info("Skipping multi-channel stream for: {0}".format(channel))
                    multi = True
                continue

            self.logger.debug("Found stream for {channel}; tech=\"{tech}\", token=\"{token}\"", **args)

            # cache the load balancing info
            if not server:
                channel_server_res = http.post(self.API_CHANNEL_INFO, data={"loadbalancinginfo": channel})
                server = channel_server_res.text
                self.logger.debug("Using load balancing server {0} for channel {1}",
                                  server,
                                  channel)

            # generate all the streams, for multi-channel streams also append the channel name
            if tech == "hls":
                for s in self._create_hls_stream(server, args).items():
                    yield s

            elif tech == "flash":
                stream = self._create_flash_stream(server, args)
                yield "live", stream


__plugin__ = Picarto
