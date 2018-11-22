import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate


_url_re = re.compile(r'http(s)?://www\.skai(?:tv)?.gr/.*')
_api_url = "http://www.skaitv.gr/json/live.php"
_api_res_schema = validate.Schema(validate.all(
    validate.get("now"),
    {
        "livestream": validate.url()
    },
    validate.get("livestream"))
)


class Skai(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        api_res = self.session.http.get(_api_url)
        yt_url = self.session.http.json(api_res, schema=_api_res_schema)
        if yt_url:
            return self.session.streams(yt_url)


__plugin__ = Skai
