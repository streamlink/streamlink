from __future__ import print_function

import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json, update_scheme

log = logging.getLogger(__name__)


class AtresPlayer(Plugin):
    url_re = re.compile(r"https?://(?:www.)?atresplayer.com/directos/([\w-]+)/?")
    state_re = re.compile(r"""window.__PRELOADED_STATE__\s*=\s*({.*?});""", re.DOTALL)
    channel_id_schema = validate.Schema(
        validate.transform(state_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(parse_json),
                {
                    "programming": {
                        validate.text: validate.all({"urlVideo": validate.text},
                                                    validate.get("urlVideo"))
                    }
                },
                validate.get("programming")
            )))
    stream_schema = validate.Schema(
        validate.transform(parse_json),
        {"sources": [
            validate.all({"src": validate.url()},
                         validate.get("src"))
        ]}, validate.get("sources"))


    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def __init__(self, url):
        # must be HTTPS
        super(AtresPlayer, self).__init__(update_scheme("https://", url))

    def _get_streams(self):
        programming = http.get(self.url, schema=self.channel_id_schema)
        for api_url in programming.values():
            for src in http.get(api_url, schema=self.stream_schema):
                for s in HLSStream.parse_variant_playlist(self.session, src).items():
                    yield s


__plugin__ = AtresPlayer
