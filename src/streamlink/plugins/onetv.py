import logging
import random
import re
from urllib.parse import unquote

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.plugin import stream_weight
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_qsd

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?1tv\.ru/live"
))
class OneTV(Plugin):
    @classmethod
    def stream_weight(cls, stream):
        return dict(ld=(140, "pixels"), sd=(360, "pixels"), hd=(720, "pixels")).get(stream, stream_weight(stream))

    def _get_streams(self):
        url = self.session.http.get(
            "https://stream.1tv.ru/api/playlist/1tvch_as_array.json",
            data={"r": random.randint(1, 100000)},
            schema=validate.Schema(
                validate.parse_json(),
                {"hls": [validate.url()]},
                validate.get("hls"),
                validate.get(0),
            ))

        if not url:
            return

        if "georestrictions" in url:
            log.error("Stream is geo-restricted")
            return

        hls_session = self.session.http.get(
            "https://stream.1tv.ru/get_hls_session",
            schema=validate.Schema(
                validate.parse_json(),
                {"s": validate.transform(unquote)},
            ))
        url = update_qsd(url, qsd=hls_session, safe="/:")

        yield from HLSStream.parse_variant_playlist(self.session, url, name_fmt="{pixels}_{bitrate}").items()


__plugin__ = OneTV
