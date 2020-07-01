import re
import json
import logging

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.compat import urljoin
from streamlink.exceptions import PluginError

log = logging.getLogger(__name__)


class ard_live(Plugin):
    _url_re = re.compile(r"https?://(www.)?daserste.de/", re.I)
    _player_re = re.compile(r'''data-ctrl-player\s*=\s*"(?P<jsondata>.*?)"''')
    _player_url_schema = validate.Schema(
        validate.transform(_player_re.search),
        validate.any(
            None,
            validate.all(validate.get("jsondata"), validate.text)
        ),
        validate.transform(lambda v: json.loads(v.replace("'", '"'))),
        validate.all(validate.transform(lambda v: v["url"]), validate.text),
    )
    _mediainfo_schema = validate.Schema({
        "mc": {
            "_title": validate.text,
            "_isLive": bool,
            "_geoblocked": bool,
            "_mediaArray": [{
                "_mediaStreamArray": [{
                    "_quality": validate.any(validate.text, int),
                    "_stream": validate.any(validate.text, [validate.text]),
                }]
            }],
        }
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        data_url = self._player_url_schema.validate(res.text)
        data_url = urljoin(res.url, data_url)
        log.debug("Player URL: '{0}'", data_url)
        res = self.session.http.get(data_url)
        mediainfo = self._mediainfo_schema.validate(json.loads(res.content))
        log.debug("Mediainfo: {0}", json.dumps(mediainfo))

        for media in mediainfo["mc"]["_mediaArray"]:
            for stream in media["_mediaStreamArray"]:
                stream_ = stream["_stream"]
                if isinstance(stream_, list):
                    if not stream_:
                        continue
                    stream_ = stream_[0]

                if ".m3u8" in stream_:
                    for s in HLSStream.parse_variant_playlist(self.session, stream_).items():
                        yield s
                else:
                    raise PluginError("Unexpected stream type: '{0}'".format(stream_))


__plugin__ = ard_live
