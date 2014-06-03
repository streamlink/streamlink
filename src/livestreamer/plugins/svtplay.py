import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HLSStream, HDSStream

STREAM_TYPES = {
    "flash": HDSStream.parse_manifest,
    "ios": HLSStream.parse_variant_playlist
}

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
                validate.filter(lambda r: r["playerType"] in STREAM_TYPES)
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

    def _get_streams(self):
        res = http.get(self.url, params=dict(output="json"))
        videos = http.json(res, schema=_video_schema)
        streams = {}
        for video in videos:
            url = video["url"]
            stream_type = video["playerType"]
            parser = STREAM_TYPES[stream_type]

            try:
                streams.update(parser(self.session, url))
            except IOError as err:
                self.logger.error("Failed to extract {0} streams: {1}",
                                  stream_type, err)

        return streams

__plugin__ = SVTPlay
