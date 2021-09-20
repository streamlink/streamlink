import json
import re
from urllib.parse import unquote

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        showtv\.com\.tr/canli-yayin(/showtv)?|
        haberturk\.com/canliyayin|
        haberturk\.com/tv/canliyayin|
        showmax\.com\.tr/canliyayin|
        showturk\.com\.tr/canli-yayin/showturk|
        bloomberght\.com/tv|
        haberturk\.tv/canliyayin
    )/?
""", re.VERBOSE))
class CinerGroup(Plugin):
    stream_re = re.compile(r"""div .*? data-ht=(?P<quote>["'])(?P<data>.*?)(?P=quote)""", re.DOTALL)
    stream_data_schema = validate.Schema(
        validate.transform(stream_re.search),
        validate.any(
            None,
            validate.all(
                validate.get("data"),
                validate.transform(unquote),
                validate.transform(lambda x: x.replace("&quot;", '"')),
                validate.transform(json.loads),
                {
                    "ht_stream_m3u8": validate.url()
                },
                validate.get("ht_stream_m3u8")
            )
        )
    )

    def _get_streams(self):
        res = self.session.http.get(self.url)
        stream_url = self.stream_data_schema.validate(res.text)
        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = CinerGroup
