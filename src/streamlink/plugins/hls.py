import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin
from streamlink.plugin.plugin import LOW_PRIORITY, NORMAL_PRIORITY, NO_PRIORITY, parse_url_params
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


class HLSPlugin(Plugin):
    _url_re = re.compile(r"(hls(?:variant)?://)?(.+(?:\.m3u8)?.*)")

    @classmethod
    def priority(cls, url):
        """
        Returns LOW priority if the URL is not prefixed with hls:// but ends with
        .m3u8 and return NORMAL priority if the URL is prefixed.
        :param url: the URL to find the plugin priority for
        :return: plugin priority for the given URL
        """
        m = cls._url_re.match(url)
        if m:
            prefix, url = cls._url_re.match(url).groups()
            url_path = urlparse(url).path
            if prefix is None and url_path.endswith(".m3u8"):
                return LOW_PRIORITY
            elif prefix is not None:
                return NORMAL_PRIORITY
        return NO_PRIORITY

    @classmethod
    def can_handle_url(cls, url):
        m = cls._url_re.match(url)
        if m:
            url_path = urlparse(m.group(2)).path
            return m.group(1) is not None or url_path.endswith(".m3u8")

    def _get_streams(self):
        url, params = parse_url_params(self.url)
        urlnoproto = self._url_re.match(url).group(2)
        urlnoproto = update_scheme("http://", urlnoproto)

        log.debug("URL={0}; params={1}".format(urlnoproto, params))
        streams = HLSStream.parse_variant_playlist(self.session, urlnoproto, **params)
        if not streams:
            return {"live": HLSStream(self.session, urlnoproto, **params)}
        else:
            return streams


__plugin__ = HLSPlugin
