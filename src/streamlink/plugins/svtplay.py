import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import StreamMapper, http, validate
from streamlink.stream import HLSStream, HDSStream

API_URL = "http://www.svt.se/videoplayer-api/video/{0}"

_url_re = re.compile(r"""
    http(s)?://
    (www\.)?
    (?:
        svtplay |
        svtflow |
        oppetarkiv
    )
    .se
""", re.VERBOSE)

# Regex to match video ID
_id_re = re.compile(r"""data-video-id=['"](?P<id>[^'"]+)['"]""")
_old_id_re = re.compile(r"/(?:video|klipp)/(?P<id>[0-9]+)/")

# New video schema used with API call
_video_schema = validate.Schema(
    {
        "videoReferences": validate.all(
            [{
                "url": validate.text,
                "format": validate.text
            }],
        ),
    },
    validate.get("videoReferences")
)

# Old video schema
_old_video_schema = validate.Schema(
    {
        "video": {
            "videoReferences": validate.all(
                [{
                    "url": validate.text,
                    "playerType": validate.text
                }],
            ),
        }
    },
    validate.get("video"),
    validate.get("videoReferences")
)


class SVTPlay(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _create_streams(self, stream_type, parser, video):
        try:
            streams = parser(self.session, video["url"])
            return streams.items()
        except IOError as err:
            self.logger.error("Failed to extract {0} streams: {1}",
                              stream_type, err)

    def _get_streams(self):
        # Retrieve URL page and search for new type of video ID
        res = http.get(self.url)
        match = _id_re.search(res.text)

        # Use API if match, otherwise resort to old method
        if match:
            vid = match.group("id")
            res = http.get(API_URL.format(vid))

            videos = http.json(res, schema=_video_schema)
            mapper = StreamMapper(cmp=lambda format, video: video["format"] == format)
            mapper.map("hls", self._create_streams, "HLS", HLSStream.parse_variant_playlist)
            mapper.map("hds", self._create_streams, "HDS", HDSStream.parse_manifest)
        else:
            res = http.get(self.url, params=dict(output="json"))
            videos = http.json(res, schema=_old_video_schema)

            mapper = StreamMapper(cmp=lambda type, video: video["playerType"] == type)
            mapper.map("ios", self._create_streams, "HLS", HLSStream.parse_variant_playlist)
            mapper.map("flash", self._create_streams, "HDS", HDSStream.parse_manifest)

        return mapper(videos)


__plugin__ = SVTPlay
