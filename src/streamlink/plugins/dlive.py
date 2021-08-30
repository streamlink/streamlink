import json
import logging
import re
from urllib.parse import unquote_plus

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


QUALITY_WEIGHTS = {
    "src": 1080,
}


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?dlive\.tv/
    (?:
        p/(?P<video>[^/]+)
        |
        (?P<channel>[^/]+)
    )
""", re.VERBOSE))
class DLive(Plugin):
    _re_videoPlaybackUrl = re.compile(r'"playbackUrl"\s*:\s*"([^"]+\.m3u8)"')

    _schema_userByDisplayName = validate.Schema({
        "data": {
            "userByDisplayName": {
                "livestream": validate.any(None, {
                    "title": validate.text
                }),
                "username": validate.text
            }
        }},
        validate.get("data"),
        validate.get("userByDisplayName")
    )
    _schema_videoPlaybackUrl = validate.Schema(
        validate.transform(_re_videoPlaybackUrl.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(unquote_plus),
            validate.transform(lambda url: bytes(url, "utf-8").decode("unicode_escape")),
            validate.url()
        ))
    )

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "dlive"

        return Plugin.stream_weight(key)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.video = self.match.group("video")
        self.channel = self.match.group("channel")

    def _get_streams_video(self):
        log.debug("Getting video HLS streams for {0}".format(self.video))
        try:
            hls_url = self.session.http.get(self.url, schema=self._schema_videoPlaybackUrl)
            if hls_url is None:
                return
        except PluginError:
            return

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams_live(self):
        log.debug("Getting live HLS streams for {0}".format(self.channel))
        try:
            data = json.dumps({"query": """query {{
                userByDisplayName(displayname:"{displayname}") {{
                    livestream {{
                        title
                    }}
                    username
                }}
            }}""".format(displayname=self.channel)})
            res = self.session.http.post("https://graphigo.prd.dlive.tv/", data=data)
            res = self.session.http.json(res, schema=self._schema_userByDisplayName)
            if res["livestream"] is None:
                return
        except PluginError:
            return

        self.author = self.channel
        self.title = res["livestream"]["title"]

        hls_url = "https://live.prd.dlive.tv/hls/live/{0}.m3u8".format(res["username"])

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams(self):
        if self.video:
            return self._get_streams_video()
        elif self.channel:
            return self._get_streams_live()


__plugin__ = DLive
