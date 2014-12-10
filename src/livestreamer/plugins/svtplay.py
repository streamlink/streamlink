import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import StreamMapper, http, validate
from livestreamer.stream import HLSStream, HDSStream


_url_re = re.compile("""
    http(s)?://
    (www\.)?
    (?:
        svtplay |
        svtflow |
        oppetarkiv
    )
    .se
""", re.VERBOSE)

_video_schema = validate.Schema(
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
        res = http.get(self.url, params=dict(output="json"))
        videos = http.json(res, schema=_video_schema)

        mapper = StreamMapper(cmp=lambda type, video: video["playerType"] == type)
        mapper.map("ios", self._create_streams, "HLS", HLSStream.parse_variant_playlist)
        mapper.map("flash", self._create_streams, "HDS", HDSStream.parse_manifest)

        return mapper(videos)

__plugin__ = SVTPlay
