import logging
import base64
import re

from streamlink.compat import unquote
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import parse_json, search_dict

log = logging.getLogger(__name__)


class BeatTV(Plugin):
    _url_re = re.compile(r"https?://(\w+\.)?be-at.tv/videos?/.+")
    _data_re = re.compile(r"""JSON\.parse\(unescape\(atob\(["'](.*)["']""")
    _data_schema = validate.Schema(
        validate.transform(_data_re.search),
        validate.any(
            validate.all(
                validate.get(1),
                validate.transform(lambda d: base64.b64decode(d).decode('utf8')),
                validate.transform(unquote),
                validate.transform(parse_json)
            ), None)
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        data = self.session.http.get(self.url, schema=self._data_schema)
        if data:
            for streaming_info in search_dict(data, "streamingInfo"):
                video_assets = streaming_info.get("videoAssets")
                if video_assets.get("hls"):
                    log.debug("Found HLS stream: {}".format(video_assets.get("hls")))
                    for s in HLSStream.parse_variant_playlist(self.session, video_assets.get("hls")).items():
                        yield s

                if video_assets.get("mpeg"):
                    for mpeg_stream in video_assets.get("mpeg"):
                        q = mpeg_stream.get("renditionValue").strip("_") or "{}k".format(mpeg_stream.get("bitrate") // 1000) or "vod"
                        yield q, HTTPStream(self.session, mpeg_stream["url"])


__plugin__ = BeatTV
