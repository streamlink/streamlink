import re

from itertools import chain

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import StreamMapper, http, validate
from streamlink.stream import HLSStream, HTTPStream, RTMPStream
from streamlink.utils import absolute_url

HLS_PLAYLIST_BASE = "http://www.hitbox.tv{0}"
LIVE_API = "http://www.hitbox.tv/api/media/live/{0}?showHidden=true"
PLAYER_API = "http://www.hitbox.tv/api/player/config/{0}/{1}?embed=false&showHidden=true"
SWF_BASE = "http://edge.vie.hitbox.tv/static/player/flowplayer/"
SWF_URL = SWF_BASE + "flowplayer.commercial-3.2.16.swf"
VOD_BASE_URL = "http://www.hitbox.tv/"

_quality_re = re.compile("(\d+p)$")
_url_re = re.compile("""
    http(s)?://(www\.)?hitbox.tv
    /(?P<channel>[^/]+)
    (?:
        /(?P<media_id>[^/]+)
    )?
""", re.VERBOSE)

_live_schema = validate.Schema(
    {
        "livestream": [{
            "media_is_live": validate.all(
                validate.text,
                validate.transform(int),
                validate.transform(bool)
            ),
            "media_id": validate.text
        }],
    },
    validate.get("livestream"),
    validate.length(1),
    validate.get(0)
)
_player_schema = validate.Schema(
    {
        "clip": {
            "baseUrl": validate.any(None, validate.text),
            "bitrates": validate.all(
                validate.filter(lambda b: b.get("url") and b.get("label")),
                [{
                    "label": validate.text,
                    "url": validate.text,
                }],
            )
        },
        validate.optional("playlist"): [{
            validate.optional("connectionProvider"): validate.text,
            validate.optional("netConnectionUrl"): validate.text,
            validate.optional("bitrates"): [{
                "label": validate.text,
                "url": validate.text,
                "provider": validate.text
            }]
        }],
        "plugins": validate.all(
            dict,
            validate.filter(lambda k, v: k in ["rtmp", "rtmpHitbox", "hls"]),
            {
                validate.text: {
                    validate.optional("netConnectionUrl"): validate.text,
                    "url": validate.text
                }
            }
        )
    }
)


class Hitbox(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_quality(self, label):
        match = _quality_re.search(label)
        if match:
            return match.group(1)

        return "live"

    def _create_hls_streams(self, bitrate):
        url = bitrate["url"]
        quality = self._get_quality(bitrate["label"])

        if not url.startswith("http"):
            url = HLS_PLAYLIST_BASE.format(url)

        if bitrate["label"] == "Auto":
            try:
                streams = HLSStream.parse_variant_playlist(self.session, url)
                return streams.items()
            except IOError as err:
                self.logger.warning("Failed to extract HLS streams: {0}", err)
        else:
            return quality, HLSStream(self.session, url)

    def _create_rtmp_stream(self, rtmp, swf_url, bitrate):
        quality = self._get_quality(bitrate["label"])
        url = bitrate["url"]
        stream = RTMPStream(self.session, {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "playpath": url,
            "swfVfy": swf_url,
            "live": True
        })

        return quality, stream

    def _get_live_streams(self, player):
        mappers = []
        swf_url = SWF_URL
        for playlist in player.get("playlist", []):
            bitrates = playlist.get("bitrates")
            provider = playlist.get("connectionProvider")
            rtmp = None

            if bitrates:
                rtmp = playlist.get("netConnectionUrl")
            elif provider and provider in player["plugins"]:
                provider = player["plugins"][provider]
                swf_name = provider["url"]
                swf_url = SWF_BASE + swf_name
                rtmp = provider["netConnectionUrl"]
                bitrates = player["clip"]["bitrates"]
            else:
                continue

            mapper = StreamMapper(
                cmp=lambda provider, bitrate: bitrate["provider"].startswith(provider)
            )
            mapper.map("hls", self._create_hls_streams)
            mapper.map("rtmp", self._create_rtmp_stream, rtmp, swf_url)
            mappers.append(mapper(bitrates))

        return chain.from_iterable(mappers)

    def _create_video_stream(self, cls, base_url, bitrate):
        url = absolute_url(base_url, bitrate["url"])
        if bitrate["label"].lower() == "auto":
            try:
                return cls.parse_variant_playlist(self.session, url).items()
            except IOError as err:
                self.logger.warning("Failed to extract HLS streams: {0}", err)
                return

        quality = self._get_quality(bitrate["label"])
        return quality, cls(self.session, url)

    def _get_video_streams(self, player):
        base_url = player["clip"]["baseUrl"] or VOD_BASE_URL
        mapper = StreamMapper(
            cmp=lambda ext, bitrate: urlparse(bitrate["url"]).path.endswith(ext)
        )
        mapper.map(".m3u8", self._create_video_stream, HLSStream, base_url)
        mapper.map(".mp4", self._create_video_stream, HTTPStream, base_url)
        mapper.map(".flv", self._create_video_stream, HTTPStream, base_url)

        return mapper(player["clip"]["bitrates"])

    def _get_streams(self):
        match = _url_re.match(self.url)
        if not match:
            return

        channel, media_id = match.group("channel", "media_id")
        if channel != "video":
            res = http.get(LIVE_API.format(channel))
            livestream = http.json(res, schema=_live_schema)
            if not livestream["media_is_live"]:
                return

            media_id = livestream["media_id"]
            media_type = "live"
        else:
            media_type = "video"

        res = http.get(PLAYER_API.format(media_type, media_id))
        player = http.json(res, schema=_player_schema)

        if media_type == "live":
            return self._get_live_streams(player)
        else:
            return self._get_video_streams(player)

__plugin__ = Hitbox
