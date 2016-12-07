import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import StreamMapper, http, validate
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HDSStream, HLSStream

PLAYER_EMBED_URL = "http://www.majorleaguegaming.com/player/embed/{0}"
STREAM_API_URL = "http://streamapi.majorleaguegaming.com/service/streams/playback/{0}"
STREAM_TYPES = {
    "hls": HLSStream.parse_variant_playlist,
    "hds": HDSStream.parse_manifest
}

_stream_id_re = re.compile(r"<meta content='.+/([\w_-]+).+' property='og:video'>")
_player_config_re = re.compile(r"var playerConfig = (.+);")
_url_re = re.compile("http(s)?://(\w+\.)?(majorleaguegaming\.com|mlg\.tv)")

_player_config_schema = validate.Schema(
    {
        "media": {
            "stream_name": validate.text
        }
    },
    validate.get("media", {}),
    validate.get("stream_name")
)
_stream_schema = validate.Schema(
    {
        "data": {
            "items": validate.all(
                [{
                    "format": validate.text,
                    "url": validate.text
                }],
                validate.filter(lambda s: s["format"] in STREAM_TYPES)
            )
        }
    },
    validate.get("data", {}),
    validate.get("items", [])
)


class MLGTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _find_channel_id(self, text):
        match = _stream_id_re.search(text)
        if match:
            return match.group(1)

    def _find_stream_id(self, text):
        match = _player_config_re.search(text)
        if match:
            stream_id = parse_json(match.group(1),
                                   schema=_player_config_schema)
            return stream_id

    def _create_streams(self, parser, stream):

        try:
            streams = parser(self.session, stream["url"])
            return streams.items()
        except IOError as err:
            if not re.search(r"(404|400) Client Error", str(err)):
                self.logger.error("Failed to extract {0} streams: {1}",
                                  stream["format"].upper(), err)

    def _get_streams(self):
        res = http.get(self.url)
        channel_id = self._find_channel_id(res.text)
        if not channel_id:
            return

        res = http.get(PLAYER_EMBED_URL.format(channel_id))
        stream_id = self._find_stream_id(res.text)
        if not stream_id:
            return

        res = http.get(STREAM_API_URL.format(stream_id),
                       params=dict(format="all"))
        items = http.json(res, schema=_stream_schema)

        mapper = StreamMapper(
            cmp=lambda type, stream: stream["format"] == type
        )
        mapper.map("hls", self._create_streams, HLSStream.parse_variant_playlist)
        mapper.map("hds", self._create_streams, HDSStream.parse_manifest)

        return mapper(items)

__plugin__ = MLGTV
