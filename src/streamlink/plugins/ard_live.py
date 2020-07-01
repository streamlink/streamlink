import re
import json
import logging

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


class ard_live(Plugin):
    _url_re = re.compile(r"https?://(www\.)?ardmediathek\.de/", re.I)
    _context_data_re = re.compile(r"window\.__FETCHED_CONTEXT__\s*=\s*(\{.+\});")
    _stream_infos_schema = validate.Schema(
        validate.transform(_context_data_re.search),
        validate.transform(lambda v: json.loads(v.group(1))),
        validate.transform(lambda vl: [d for d in vl.values() if "widgets" in d]),
        validate.transform(lambda v: v[0]), {
            "widgets": [{
                "mediaCollection": {
                    "embedded": {
                        "_isLive": bool,
                        "_mediaArray": [{
                            "_mediaStreamArray": [{
                                "_stream": validate.all(validate.endswith(".m3u8"), validate.url(),
                                                        validate.transform(lambda v: update_scheme("https://", v)))
                            }]
                        }],
                    },
                },
            }],
        }
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        stream_infos = self.session.http.get(self.url, schema=self._stream_infos_schema)
        log.trace("{0!r}".format(stream_infos))
        for stream in stream_infos["widgets"][0]["mediaCollection"]["embedded"]["_mediaArray"][0]["_mediaStreamArray"]:
            url = stream["_stream"]
            for s in HLSStream.parse_variant_playlist(self.session, url).items():
                yield s


__plugin__ = ard_live
