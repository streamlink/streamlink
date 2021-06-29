import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json, update_scheme


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?streamable\.com/(.+)"
))
class Streamable(Plugin):
    meta_re = re.compile(r'''var\s*videoObject\s*=\s*({.*});''')
    config_schema = validate.Schema(
        validate.transform(meta_re.search),
        validate.any(None,
                     validate.all(
                         validate.get(1),
                         validate.transform(parse_json),
                         {
                             "files": {validate.text: {"url": validate.url(),
                                                       "width": int,
                                                       "height": int,
                                                       "bitrate": int}}
                         })
                     )
    )

    def _get_streams(self):
        data = self.session.http.get(self.url, schema=self.config_schema)

        for info in data["files"].values():
            stream_url = update_scheme(self.url, info["url"])
            # pick the smaller of the two dimensions, for landscape v. portrait videos
            res = min(info["width"], info["height"])
            yield "{0}p".format(res), HTTPStream(self.session, stream_url)


__plugin__ = Streamable
