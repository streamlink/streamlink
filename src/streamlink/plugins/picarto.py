"""
$description Global live streaming and video hosting platform for the creative community.
$url picarto.tv
$type live, vod
"""

import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?picarto\.tv/
    (?:
        streampopout/(?P<po_user>[^/]+)/public
    |
        videopopout/(?P<po_vod_id>\d+)
    |
        [^/]+/videos/(?P<vod_id>\d+)
    |
        (?P<user>[^/?&]+)
    )$
""", re.VERBOSE))
class Picarto(Plugin):
    API_URL_LIVE = "https://ptvintern.picarto.tv/api/channel/detail/{username}"
    API_URL_VOD = "https://ptvintern.picarto.tv/ptvapi"
    HLS_URL = "https://{netloc}/stream/hls/{file_name}/index.m3u8"

    def get_live(self, username):
        channel, multistreams, loadbalancer = self.session.http.get(
            self.API_URL_LIVE.format(username=username),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "channel": validate.any(None, {
                        "stream_name": str,
                        "title": str,
                        "online": bool,
                        "private": bool,
                        "categories": [{"label": str}],
                    }),
                    "getMultiStreams": validate.any(None, {
                        "multistream": bool,
                        "streams": [{
                            "name": str,
                            "online": bool,
                        }],
                    }),
                    "getLoadBalancerUrl": validate.any(None, {
                        "url": validate.any(None, validate.transform(lambda url: urlparse(url).netloc))
                    })
                },
                validate.union_get("channel", "getMultiStreams", "getLoadBalancerUrl"),
            )
        )
        if not channel or not multistreams or not loadbalancer:
            log.debug("Missing channel or streaming data")
            return

        log.trace(f"loadbalancer={loadbalancer!r}")
        log.trace(f"channel={channel!r}")
        log.trace(f"multistreams={multistreams!r}")

        if not channel["online"]:
            log.error("User is not online")
            return

        if channel["private"]:
            log.info("This is a private stream")
            return

        self.author = username
        self.category = channel["categories"][0]["label"]
        self.title = channel["title"]

        hls_url = self.HLS_URL.format(
            netloc=loadbalancer["url"],
            file_name=channel["stream_name"]
        )

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def get_vod(self, vod_id):
        data = {
            'query': (
                'query ($videoId: ID!) {\n'
                '  video(id: $videoId) {\n'
                '    id\n'
                '    title\n'
                '    file_name\n'
                '    video_recording_image_url\n'
                '    channel {\n'
                '      name\n'
                '      }'
                '  }\n'
                '}\n'
            ),
            'variables': {'videoId': vod_id},
        }
        vod_data = self.session.http.post(self.API_URL_VOD, json=data, schema=validate.Schema(
            validate.parse_json(),
            {"data": {
                "video": validate.any(None, {
                    "id": int,
                    "title": str,
                    "file_name": str,
                    "video_recording_image_url": str,
                    "channel": {"name": str},
                }),
            }},
            validate.get(("data", "video"))
        ))

        if not vod_data:
            log.debug("Missing video data")
            return

        log.trace(f"vod_data={vod_data!r}")

        self.author = vod_data["channel"]["name"]
        self.category = "VOD"
        self.title = vod_data["title"]

        netloc = urlparse(vod_data["video_recording_image_url"]).netloc
        hls_url = self.HLS_URL.format(
            netloc=netloc,
            file_name=vod_data["file_name"]
        )

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams(self):
        m = self.match.groupdict()

        if m['po_vod_id'] or m['vod_id']:
            log.debug('Type=VOD')
            return self.get_vod(m['po_vod_id'] or m['vod_id'])
        elif m['po_user'] or m['user']:
            log.debug('Type=Live')
            return self.get_live(m['po_user'] or m['user'])


__plugin__ = Picarto
