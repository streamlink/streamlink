import re

from operator import methodcaller

from livestreamer.compat import urlparse
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream

_url_re = re.compile("http(s)?://(\w+\.)?ilive.to/")
_rtmp_re = re.compile("""
    \$.getJSON\("(?P<token_url>[^"]+)".*
    flashplayer:\s+"(?P<swf_url>[^"]+)".*
    streamer:\s+"(?P<rtmp_url>[^"]+)".*
    file:\s+"(?P<rtmp_playpath>[^"]+)\.flv"
""", re.VERBOSE | re.DOTALL)

_token_schema = validate.Schema(
    {
        "token": validate.text
    },
    validate.get("token")
)
_schema = validate.Schema(
    validate.transform(_rtmp_re.search),
    validate.any(
        None,
        validate.all(
            validate.transform(methodcaller("groupdict")),
            {
                "rtmp_playpath": validate.text,
                "rtmp_url": validate.all(
                    validate.transform(methodcaller("replace", "\\/", "/")),
                    validate.url(scheme="rtmp"),
                ),
                "swf_url": validate.url(scheme="http"),
                "token_url": validate.url(scheme="http")
            }
        )
    )
)


class ILive(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        info = http.get(self.url, schema=_schema)
        if not info:
            return

        headers = {"Referer": self.url}
        res = http.get(info["token_url"], headers=headers)
        token = http.json(res, schema=_token_schema)

        parsed = urlparse(info["rtmp_url"])
        if parsed.query:
            app = "{0}?{1}".format(parsed.path[1:], parsed.query)
        else:
            app = parsed.path[1:]

        params = {
            "rtmp": info["rtmp_url"],
            "app": app,
            "pageUrl": self.url,
            "swfVfy": info["swf_url"],
            "playpath": info["rtmp_playpath"],
            "token": token,
            "live": True
        }

        stream = RTMPStream(self.session, params)
        return dict(live=stream)

__plugin__ = ILive
