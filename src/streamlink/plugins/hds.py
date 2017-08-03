import re

from streamlink.plugin import Plugin
from streamlink.plugin.plugin import parse_url_params, LOW_PRIORITY, NORMAL_PRIORITY, NO_PRIORITY
from streamlink.stream import HDSStream
from streamlink.utils import update_scheme
from streamlink.compat import urlparse


class HDSPlugin(Plugin):
    _url_re = re.compile(r"(hds://)?(.+(?:\.f4m)?.*)")

    @classmethod
    def priority(cls, url):
        """
        Returns LOW priority if the URL is not prefixed with hds:// but ends with
        .f4m and return NORMAL priority if the URL is prefixed.
        :param url: the URL to find the plugin priority for
        :return: plugin priority for the given URL
        """
        m = cls._url_re.match(url)
        if m:
            prefix, url = cls._url_re.match(url).groups()
            url_path = urlparse(url).path
            if prefix is None and url_path.endswith(".f4m"):
                return LOW_PRIORITY
            elif prefix is not None:
                return NORMAL_PRIORITY
        return NO_PRIORITY

    @classmethod
    def can_handle_url(cls, url):
        m = cls._url_re.match(url)
        if m:
            url_path = urlparse(m.group(2)).path
            return m.group(1) is not None or url_path.endswith(".f4m")

    def _get_streams(self):
        url, params = parse_url_params(self.url)

        urlnoproto = self._url_re.match(url).group(2)
        urlnoproto = update_scheme("http://", urlnoproto)

        return HDSStream.parse_manifest(self.session, urlnoproto, **params)


__plugin__ = HDSPlugin
