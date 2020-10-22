import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class BTV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?btvplus\.bg/live/?")
    api_url = "https://btvplus.bg/lbin/v3/btvplus/player_config.php"

    media_id_re = re.compile(r"media_id=(\d+)")
    src_re = re.compile(r"src: \"(http.*?)\"")
    api_schema = validate.Schema(
        validate.all(
            {"status": "ok", "config": validate.text},
            validate.get("config"),
            validate.all(
                validate.transform(src_re.search),
                validate.any(
                    None,
                    validate.get(1),
                    validate.url()
                )
            )
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_hls_url(self, media_id):
        res = self.session.http.get(self.api_url, params=dict(media_id=media_id))
        return parse_json(res.text, schema=self.api_schema)

    def _get_streams(self):
        res = self.session.http.get(self.url)
        media_match = self.media_id_re.search(res.text)
        media_id = media_match and media_match.group(1)
        if media_id:
            log.debug(f"Found media id: {media_id}")
            stream_url = self.get_hls_url(media_id)
            if stream_url:
                return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = BTV
