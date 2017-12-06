from __future__ import print_function

import re
import json

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
        https?://(?:\w+\.)?picarto\.tv/(?:videopopout/)?([^&?/]+)
    """, re.VERBOSE)

    # divs with tech_switch class
    _tech_switch_re = re.compile(r"""
    <div\s+class=".*?tech_switch.*?"(.*?)>
    """, re.VERBOSE)
    # Stream status regex - extracted from playersettings
    # group(1) = token, group(2) = online status (string true/false), group(3) = "Channel"
    _stream_status_re = re.compile(r"""
        <script>\s[\s\S]*?token:\s?(.*?),[\s\S]*?online:\s(.*?),[\s\S]*?channel:\s(.*?),[\s\S]*?
        </script>
    """, re.VERBOSE)
    # <source ...>
    _source_re = re.compile(r'''source src="(http[^"]+)"''')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @classmethod
    def _stream_online(cls, page):
        match = cls._stream_status_re.search(page.text)
        if match:
            return match.group(2).strip() == "true"
        return False

    def _create_hls_stream(self, server, channel, token):
        streams = HLSStream.parse_variant_playlist(self.session,
                                                   self.HLS_URL.format(
                                                       server=server,
                                                       channel=channel,
                                                       token=token),
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

    def _create_flash_stream(self, server, channel, token):
        params = {
            "rtmp": self.RTMP_URL.format(server=server),
            "playpath": self.RTMP_PLAYPATH.format(token=token, channel=channel)
        }
        return RTMPStream(self.session, params=params)

    def _get_vod_stream(self, page):
        m = self._source_re.search(page.text)
        if m:
            return HLSStream.parse_variant_playlist(self.session, m.group(1))

    def _get_streams(self):
        page = http.get(self.url)

        page_channel = self._url_re.match(self.url).group(1)
        if page_channel.endswith(".flv"):
            self.logger.debug("Possible VOD stream...")
            vod_streams = self._get_vod_stream(page)
            if vod_streams:
                for s in vod_streams.items():
                    yield s
                return

        if "This channel does not exist" in page.text:
            self.logger.error("The channel {0} does not exist".format(page_channel))
            return

        if not self._stream_online(page):
            self.logger.error("The channel {0} is currently offline".format(page_channel))
            return

        server = None
        token = "public"

        match = self._stream_status_re.search(page.text)
        if match:
            channel = match.group(3).strip(" \"")
            print(channel)
        else:
            self.logger.error("Channel name cannot be extracted from page.")
            return

        # Extract preferred edge server and available techs from channel API
        channel_server_res = http.post(self.API_CHANNEL_INFO, data={"loadbalancinginfo": channel})
        info_json = json.loads(channel_server_res.text)
        pref = info_json["preferedEdge"]
        for i in info_json["edges"]:
            if i["id"] == pref:
                server = i["ep"]
                break
        self.logger.debug("Using load balancing server {0} : {1} for channel {2}",
                          pref,
                          server,
                          channel)

        for i in info_json["techs"]:
            if i["label"] == "HLS":
                for s in self._create_hls_stream(server, channel, token).items():
                    yield s
            elif i["label"] == "RTMP Flash":
                stream = self._create_flash_stream(server, channel, token)
                yield "live", stream


__plugin__ = Picarto
