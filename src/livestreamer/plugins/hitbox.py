import re

from livestreamer.compat import urlparse
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HLSStream, HTTPStream, RTMPStream

LIVE_API = "http://www.hitbox.tv/api/media/live/{0}?showHidden=true"
PLAYER_API = "http://www.hitbox.tv/api/player/config/{0}/{1}?embed=false&showHidden=true"
SWF_BASE = "http://edge.vie.hitbox.tv/static/player/flowplayer/"
SWF_URL = SWF_BASE + "flowplayer.commercial-3.2.16.swf"
VOD_BASE_URL = "http://edge.bf.hitbox.tv/static/videos/vods"

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
                    "url": validate.text
                }],
            )
        },
        validate.optional("playlist"): [{
            validate.optional("connectionProvider"): validate.text,
            validate.optional("netConnectionUrl"): validate.text,
            validate.optional("bitrates"): [{
                "label": validate.text,
                "url": validate.text
            }]
        }],
        "plugins": {
            validate.optional("clustering"): {
                "netConnectionUrl": validate.text,
                "url": validate.text
            }
        }
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
        streams = {}
        if media_type == "live":
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

                for bitrate in bitrates:
                    quality = self._get_quality(bitrate["label"])
                    url = bitrate["url"]
                    stream = RTMPStream(self.session, {
                        "rtmp": rtmp,
                        "pageUrl": self.url,
                        "playpath": url,
                        "swfVfy": swf_url,
                        "live": True
                    })
                    if quality in streams:
                        quality += "_alt"

                    streams[quality] = stream
        else:
            base_url = player["clip"]["baseUrl"] or VOD_BASE_URL
            for bitrate in player["clip"]["bitrates"]:
                url = base_url + "/" + bitrate["url"]
                quality = self._get_quality(bitrate["label"])

                if urlparse(url).path.endswith("m3u8"):
                    stream = HLSStream(self.session, url)
                else:
                    stream = HTTPStream(self.session, url)

                streams[quality] = stream

        return streams

__plugin__ = Hitbox
