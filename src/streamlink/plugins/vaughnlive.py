import random
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream
from streamlink.utils import swfdecompress

INFO_URL = "http://{site}{path}{domain}_{channel}?{version}_{ms}-{ms}-{random}"

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
        swf_url = "http://vaughnlive.tv" + match.group(1)
        self.logger.debug("Using swf url: {0}", swf_url)

        swfres = http.get(swf_url)
        swfdata = swfdecompress(swfres.content).decode("latin1")

        player_version_m = re.search(r"0\.\d+\.\d+\.\d+", swfdata)
        info_url_domain_m = re.search(r"\w+\.vaughnsoft\.net", swfdata)
        info_url_path_m = re.search(r"/video/edge/[a-zA-Z0-9_]+-", swfdata)

        player_version = player_version_m and player_version_m.group(0)
        info_url_domain = info_url_domain_m and info_url_domain_m.group(0)
        info_url_path = info_url_path_m and info_url_path_m.group(0)

        if player_version and info_url_domain and info_url_path:
            self.logger.debug("Found player_version={0}, info_url_domain={1}, info_url_path={2}",
                              player_version, info_url_domain, info_url_path)
            match = _url_re.match(self.url)
            params = {"channel": match.group("channel").lower(),
                      "domain": DOMAIN_MAP.get(match.group("domain"), match.group("domain")),
                      "version": player_version,
                      "ms": random.randint(0, 999),
                      "random": random.random(),
                      "site": info_url_domain,
                      "path": info_url_path}
            info_url = INFO_URL.format(**params)
            self.logger.debug("Loading info url: {0}", INFO_URL.format(**params))

            info = http.get(info_url, schema=_schema)
            if not info:
                self.logger.info("This stream is currently unavailable")
                return

            app = "live"
            self.logger.debug("Streaming server is: {0}", info["server"])
            if info["server"].endswith(":1337"):
                app = "live-{0}".format(info["ingest"].lower())

            stream = RTMPStream(self.session, {
                "rtmp": "rtmp://{0}/live".format(info["server"]),
                "app": "{0}?{1}".format(app, info["token"]),
                "swfVfy": swf_url,
                "pageUrl": self.url,
                "live": True,
                "playpath": "{domain}_{channel}".format(**params),
            })

            return dict(live=stream)
        else:
            self.logger.info("Found player_version={0}, info_url_domain={1}, info_url_path={2}",
                             player_version, info_url_domain, info_url_path)
            if not player_version:
                self.logger.error("Could not detect player_version")
            if not info_url_domain:
                self.logger.error("Could not detect info_url_domain")
            if not info_url_path:
                self.logger.error("Could not detect info_url_path")


__plugin__ = VaughnLive
