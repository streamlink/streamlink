import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Livestream(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?livestream\.com/")
    _config_re = re.compile(r"window.config = ({.+})")
    _stream_config_schema = validate.Schema(validate.any({
        "event": {
            "stream_info": validate.any({
                "is_live": bool,
                "secure_m3u8_url": validate.url(scheme="https"),
            }, None),
        }
    }, {}), validate.get("event", {}), validate.get("stream_info", {}))

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self._config_re.search(res.text)
        if not m:
            log.debug("Unable to find _config_re")
            return

        stream_info = parse_json(m.group(1), "config JSON",
                                 schema=self._stream_config_schema)

        log.trace("stream_info: {0!r}".format(stream_info))
        if not (stream_info and stream_info["is_live"]):
            log.debug("Stream might be Off Air")
            return

        m3u8_url = stream_info.get("secure_m3u8_url")
        if m3u8_url:
            yield from HLSStream.parse_variant_playlist(self.session, m3u8_url).items()


__plugin__ = Livestream
