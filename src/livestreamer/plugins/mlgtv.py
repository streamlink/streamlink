import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HDSStream, HLSStream

CONFIG_API_URL = "http://www.majorleaguegaming.com/player/config.json"
STREAM_API_URL = "http://streamapi.majorleaguegaming.com/service/streams/playback/{0}"
STREAM_TYPES = {
    "hls": HLSStream.parse_variant_playlist,
    "hds": HDSStream.parse_manifest
}

_stream_id_re = re.compile(r"<meta content='.+/([\w_-]+).+' property='og:video'>")
_url_re = re.compile("http(s)?://(\w+\.)?(majorleaguegaming\.com|mlg\.tv)")

_config_schema = validate.Schema(
    {
        "media": [{
            "channel": validate.text
        }]
    }
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

    def _get_stream_id(self, channel_id):
        res = http.get(CONFIG_API_URL, params=dict(id=channel_id))
        config = http.json(res, schema=_config_schema)

        if config["media"]:
            return config["media"][0]["channel"]

    def _get_streams(self):
        res = http.get(self.url)
        channel_id = self._find_channel_id(res.text)
        if not channel_id:
            return

        stream_id = self._get_stream_id(channel_id)
        if not stream_id:
            return

        res = http.get(STREAM_API_URL.format(stream_id),
                       params=dict(format="all"))
        items = http.json(res, schema=_stream_schema)
        streams = {}
        for stream in items:
            parser = STREAM_TYPES[stream["format"]]

            try:
                streams.update(parser(self.session, stream["url"]))
            except IOError as err:
                if not re.search(r"(404|400) Client Error", str(err)):
                    self.logger.error("Failed to extract {0} streams: {1}",
                                      stream["format"].upper(), err)

        return streams

__plugin__ = MLGTV
