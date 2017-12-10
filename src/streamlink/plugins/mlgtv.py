import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream


class MLGTV(Plugin):
    """Streamlink Plugin for Livestreams on mlg.tv / majorleaguegaming.com"""

    PLAYER_EMBED_URL = "http://player2.majorleaguegaming.com/api/v2/player/embed/live/?ch={0}"
    CHANNEL_API = "https://www.majorleaguegaming.com/api/channel/{0}"

    _player_config_re = re.compile(r"var playerConfig = (.+);")
    _player_embed_re = re.compile(r"""https?://player2\.majorleaguegaming\.com/api/v2/player/embed/live/\?ch=(?P<channel_id>[^"']+)""")
    _site_data_re = re.compile(r"window\.siteData = (?P<data>.+);")
    _stream_id_re = re.compile(r"<meta content='.+/([\w_-]+).+' property='og:video'>")

    _url_re = re.compile(r"http(s)?://(\w+\.)?(majorleaguegaming\.com|mlg\.tv)")

    _player_config_schema = validate.Schema(
        {
            "media": {
                "streams": [{
                    "streamUrl": validate.text,
                    "abr": validate.text
                }]
            }
        },
        validate.get("media", {}),
        validate.get("streams")
    )

    _site_data_schema = validate.Schema(
        {
            "status_code": 200,
            "status_text": "OK",
            "data": {
                "slug": validate.text,
            }
        },
        validate.get("data", {}),
        validate.get("slug")
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _find_channel_id(self, text):
        match = self._stream_id_re.search(text)
        if match:
            return match.group(1)

        match = self._site_data_re.search(text)
        if match:
            r_json = parse_json(match.group("data"))
            if r_json:
                mlg_channel_id = r_json.get("mlg_channel_id")
                if mlg_channel_id:
                    res = http.get(self.CHANNEL_API.format(mlg_channel_id))
                    channel_id = http.json(res, schema=self._site_data_schema)
                    return channel_id

        match = self._player_embed_re.search(text)
        if match:
            return match.group("channel_id")

    def _find_stream_id(self, text):
        match = self._player_config_re.search(text)
        if match:
            stream_id = parse_json(match.group(1),
                                   schema=self._player_config_schema)
            return stream_id

    def _get_streams(self):
        match = self._player_embed_re.match(self.url)
        if match:
            channel_id = match.group("channel_id")
        else:
            try:
                res = http.get(self.url)
            except Exception as e:
                raise NoStreamsError(self.url)
            channel_id = self._find_channel_id(res.text)

        if not channel_id:
            return
        self.logger.info("Channel ID: {0}".format(channel_id))

        res = http.get(self.PLAYER_EMBED_URL.format(channel_id))
        items = self._find_stream_id(res.text)
        if not items:
            return

        a = b = False
        for stream in items:
            if stream["abr"] == "hls":
                try:
                    for s in HLSStream.parse_variant_playlist(self.session, stream["streamUrl"]).items():
                        yield s
                except IOError:
                    a = True
            elif stream["abr"] == "hds":
                try:
                    for s in HDSStream.parse_manifest(self.session, stream["streamUrl"]).items():
                        yield s
                except IOError:
                    b = True

        if a and b:
            self.logger.warning("Could not open the stream, perhaps the channel is offline")


__plugin__ = MLGTV
