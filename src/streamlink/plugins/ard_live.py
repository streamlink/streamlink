import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import parse_json, verifyjson

log = logging.getLogger(__name__)


class ard_live(Plugin):
    _url_re = re.compile(r"https?://((www|live)\.)?daserste\.de/")
    _player_re = re.compile(r'''data-ctrl-player\s*=\s*"(?P<jsondata>.*?)"''')
    _player_url_schema = validate.Schema(
        validate.transform(_player_re.search),
        validate.any(None, validate.all(
            validate.get("jsondata"),
            validate.text,
            validate.transform(lambda v: parse_json(v.replace("'", '"'))),
            validate.transform(lambda v: verifyjson(v, "url")),
        ))
    )
    _mediainfo_schema = validate.Schema({
        "mc": {
            validate.optional("_title"): validate.text,
            validate.optional("_isLive"): bool,
            validate.optional("_geoblocked"): bool,
            "_mediaArray": [{
                "_mediaStreamArray": [{
                    "_quality": validate.any(validate.text, int),
                    "_stream": validate.any(validate.text, [validate.text]),
                }]
            }],
        },
    }, validate.get("mc"))
    _QUALITY_MAP = {
        "auto": "auto",
        4: "1080p",
        3: "720p",
        2: "544p",
        1: "288p",
        0: "144p"
    }

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        data_url = self._player_url_schema.validate(res.text)
        if not data_url:
            log.error("Could not find video at this url.")
            return

        data_url = urljoin(res.url, data_url)
        log.debug(f"Player URL: '{data_url}'")
        res = self.session.http.get(data_url)
        mediainfo = parse_json(res.text, name="MEDIAINFO", schema=self._mediainfo_schema)
        log.trace("Mediainfo: {0!r}".format(mediainfo))

        for media in mediainfo["_mediaArray"]:
            for stream in media["_mediaStreamArray"]:
                stream_ = stream["_stream"]
                if isinstance(stream_, list):
                    if not stream_:
                        continue
                    stream_ = stream_[0]

                if ".m3u8" in stream_:
                    yield from HLSStream.parse_variant_playlist(self.session, stream_).items()
                elif ".mp4" in stream_ and ".f4m" not in stream_:
                    yield "{0}".format(self._QUALITY_MAP[stream["_quality"]]), HTTPStream(self.session, stream_)
                else:
                    if ".f4m" not in stream_:
                        log.error("Unexpected stream type: '{0}'".format(stream_))


__plugin__ = ard_live
