import re

from streamlink.plugin import Plugin
from streamlink.plugin.plugin import parse_url_params
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme


class HLSPlugin(Plugin):
    _url_re = re.compile(r"hls(?:variant)?://(.+)")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        url, params = parse_url_params(self.url)
        urlnoproto = self._url_re.match(url).group(1)
        urlnoproto = update_scheme("http://", urlnoproto)

        self.logger.debug("URL={0}; params={1}", urlnoproto, params)
        streams = HLSStream.parse_variant_playlist(self.session, urlnoproto, **params)
        if not streams:
            return {"live": HLSStream(self.session, urlnoproto, **params)}
        else:
            return streams


__plugin__ = HLSPlugin
