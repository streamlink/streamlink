import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


_url_re = re.compile(r"http(s)?://meerkatapp.co/(?P<user>[\w\-\=]+)/(?P<token>[\w\-]+)")


class Meerkat(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        if not match:
            return

        streams = {}
        streams["live"] = HLSStream(self.session, "http://cdn.meerkatapp.co/broadcast/{0}/live.m3u8".format(match.group("token")))

        return streams


__plugin__ = Meerkat
