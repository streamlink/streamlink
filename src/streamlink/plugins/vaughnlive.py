import random
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream

PLAYER_VERSION = "0.1.1.782"
INFO_URL = "http://mvn.vaughnsoft.net/video/edge/soon_depricated_Q2_2017-{domain}_{channel}?{version}_{ms}-{ms}-{random}"

DOMAIN_MAP = {
    "breakers": "btv",
    "vapers": "vtv",
    "vaughnlive": "live",
}

_url_re = re.compile(r"""
    http(s)?://(\w+\.)?
    (?P<domain>vaughnlive|breakers|instagib|vapers).tv
    (/embed/video)?
    /(?P<channel>[^/&?]+)
""", re.VERBOSE)

_swf_player_re = re.compile(r'swfobject.embedSWF\("(/\d+/swf/[0-9A-Za-z]+\.swf)"')

_schema = validate.Schema(
    validate.any(
        validate.all(u"<error></error>", validate.transform(lambda x: None)),
        validate.all(
            validate.transform(lambda s: s.split(";")),
            validate.length(3),
            validate.union({
                "server": validate.all(
                    validate.get(0),
                    validate.text
                ),
                "token": validate.all(
                    validate.get(1),
                    validate.text,
                    validate.startswith(":mvnkey-"),
                    validate.transform(lambda s: s[len(":mvnkey-"):])
                ),
                "ingest": validate.all(
                    validate.get(2),
                    validate.text
                )
            })
        )
    )
)


class VaughnLive(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = _swf_player_re.search(res.text)
        if match is None:
            return
        swfUrl = "http://vaughnlive.tv" + match.group(1)
        self.logger.debug("Using swf url: {0}", swfUrl)

        match = _url_re.match(self.url)
        params = {}
        params["channel"] = match.group("channel").lower()
        params["domain"] = DOMAIN_MAP.get(match.group("domain"), match.group("domain"))
        params["version"] = PLAYER_VERSION
        params["ms"] = random.randint(0, 999)
        params["random"] = random.random()
        info_url = INFO_URL.format(**params)
        self.logger.debug("Loading info url: {0}", INFO_URL.format(**params))
        info = http.get(info_url, schema=_schema)
        if not info:
            self.logger.info("This stream is currently available")
            return

        app = "live"
        if info["server"] in ["198.255.17.18:1337", "198.255.17.66:1337", "50.7.188.2:1337"]:
            if info["ingest"] == "SJC":
                app = "live-sjc"
            elif info["ingest"] == "NYC":
                app = "live-nyc"
            elif info["ingest"] == "ORD":
                app = "live-ord"
            elif info["ingest"] == "AMS":
                app = "live-ams"
            elif info["ingest"] == "DEN":
                app = "live-den"

        stream = RTMPStream(self.session, {
            "rtmp": "rtmp://{0}/live".format(info["server"]),
            "app": "{0}?{1}".format(app, info["token"]),
            "swfVfy": swfUrl,
            "pageUrl": self.url,
            "live": True,
            "playpath": "{domain}_{channel}".format(**params),
        })

        return dict(live=stream)


__plugin__ = VaughnLive
