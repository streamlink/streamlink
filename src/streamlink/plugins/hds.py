import re

from streamlink.plugin import Plugin
from streamlink.plugin.plugin import parse_url_params
from streamlink.stream import HDSStream
from streamlink.utils import update_scheme


class HDSPlugin(Plugin):
    _url_re = re.compile(r"hds://(.+)")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        url, params = parse_url_params(self.url)

        urlnoproto = self._url_re.match(url).group(1)
        urlnoproto = update_scheme("http://", urlnoproto)

        return HDSStream.parse_manifest(self.session, urlnoproto, **params)


__plugin__ = HDSPlugin
