import json
import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, RTMPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Picarto(Plugin):
    CHANNEL_API_URL = "https://api.picarto.tv/v1/channel/name/{channel}"
    VIDEO_API_URL = "https://picarto.tv/process/channel"
    RTMP_URL = "rtmp://{server}:1935/play/"
    RTMP_PLAYPATH = "golive+{channel}?token={token}"
    HLS_URL = "https://{server}/hls/{channel}/index.m3u8?token={token}"

    # Regex for all usable URLs
    _url_re = re.compile(r"""
        https?://(?:\w+\.)?picarto\.tv/(?:videopopout/)?([^&?/]+)
    """, re.VERBOSE)

    # Regex for VOD extraction
    _vod_re = re.compile(r'''(?<=#vod-player", )(\{.*?\})''')

    data_schema = validate.Schema(
        validate.transform(_vod_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(0),
                validate.transform(parse_json),
                {
                    "vod": validate.url(),
                }
            )
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _create_hls_stream(self, server, channel, token):
        streams = HLSStream.parse_variant_playlist(self.session,
                                                   self.HLS_URL.format(
                                                       server=server,
                                                       channel=channel,
                                                       token=token),
                                                   verify=False)
        if len(streams) > 1:
            log.debug("Multiple HLS streams found")
            return streams
        elif len(streams) == 0:
            log.warning("No HLS streams found when expected")
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
        data = self.data_schema.validate(page.text)

        if data:
            return HLSStream.parse_variant_playlist(self.session, data["vod"])

    def _get_streams(self):
        url_channel_name = self._url_re.match(self.url).group(1)

        # Handle VODs first, since their "channel name" is different
        if url_channel_name.endswith((".flv", ".mkv")):
            log.debug("Possible VOD stream...")
            page = self.session.http.get(self.url)
            vod_streams = self._get_vod_stream(page)
            if vod_streams:
                yield from vod_streams.items()
                return
            else:
                log.warning("Probably a VOD stream but no VOD found?")

        ci = self.session.http.get(self.CHANNEL_API_URL.format(channel=url_channel_name), raise_for_status=False)

        if ci.status_code == 404:
            log.error("The channel {0} does not exist".format(url_channel_name))
            return

        channel_api_json = json.loads(ci.text)

        if not channel_api_json["online"]:
            log.error("The channel {0} is currently offline".format(url_channel_name))
            return

        if channel_api_json["private"]:
            log.error("The channel {0} is private, such streams are not yet supported".format(url_channel_name))
            return

        server = None
        token = "public"
        channel = channel_api_json["name"]

        # Extract preferred edge server and available techs from the undocumented channel API
        channel_server_res = self.session.http.post(self.VIDEO_API_URL, data={"loadbalancinginfo": channel})
        info_json = json.loads(channel_server_res.text)
        pref = info_json["preferedEdge"]
        for i in info_json["edges"]:
            if i["id"] == pref:
                server = i["ep"]
                break
        log.debug("Using load balancing server {0} : {1} for channel {2}".format(pref, server, channel))

        for i in info_json["techs"]:
            if i["label"] == "HLS":
                yield from self._create_hls_stream(server, channel, token).items()
            elif i["label"] == "RTMP Flash":
                stream = self._create_flash_stream(server, channel, token)
                yield "live", stream


__plugin__ = Picarto
