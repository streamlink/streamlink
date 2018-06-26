from __future__ import print_function

import logging
import re
from functools import partial

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, StreamMapper
from streamlink.stream import HLSStream, DASHStream
from streamlink.utils import parse_json, update_scheme, search_dict

log = logging.getLogger(__name__)


class AtresPlayer(Plugin):
    url_re = re.compile(r"https?://(?:www.)?atresplayer.com/")
    state_re = re.compile(r"""window.__PRELOADED_STATE__\s*=\s*({.*?});""", re.DOTALL)
    channel_id_schema = validate.Schema(
        validate.transform(state_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(parse_json),
                validate.transform(partial(search_dict, key="urlVideo"))
            )
        )
    )
    stream_schema = validate.Schema(
        validate.transform(parse_json),
        {"sources": [
            validate.all({
                "src": validate.url(),
                validate.optional("type"): validate.text
            })
        ]}, validate.get("sources"))


    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def __init__(self, url):
        # must be HTTPS
        super(AtresPlayer, self).__init__(update_scheme("https://", url))

    def _get_streams(self):
        api_urls = http.get(self.url, schema=self.channel_id_schema)
        for api_url in api_urls:
            log.debug("API URL: {0}".format(api_url))
            for source in http.get(api_url, schema=self.stream_schema):
                log.debug("Stream source: {0} ({1})".format(source['src'], source.get("type", "n/a")))

                if "type" not in source or source["type"] == "application/vnd.apple.mpegurl":
                    for s in HLSStream.parse_variant_playlist(self.session, source["src"]).items():
                        yield s
                elif source["type"] == "application/dash+xml":
                    for s in DASHStream.parse_manifest(self.session, source["src"]).items():
                        yield s


__plugin__ = AtresPlayer
