import re
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class DingitTV(Plugin):
    """
    Plugin that supports playing streams from DingIt.tv
    """

    # regex to match the site urls
    url_re = re.compile(r"""
        http://www.dingit.tv/(
            highlight/(?P<highlight_id>\d+)|
            channel/(?P<broadcaster>\w+)/(?P<channel_id>\d+)
    )""", re.VERBOSE)

    # flashvars API url and schema
    flashvars_url = "http://www.dingit.tv/api/get_player_flashvars"
    flashvars_schema = validate.Schema({
        u"status": 0,
        u"data": [{
            validate.optional("stream"): validate.text,
            validate.optional("akaurl"): validate.text,
            validate.optional("pereakaurl"): validate.text,
        }]
    },
        validate.get("data"),
        validate.length(1),
        validate.get(0)
    )

    pereakaurl = "http://dingitmedia-vh.akamaihd.net/i/{}/master.m3u8"
    akaurl = "https://dingmedia1-a.akamaihd.net/processed/delivery/{}70f8b7bc-5ed4-336d-609a-2d2cd86288c6.m3u8"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    @Plugin.broken()
    def _get_streams(self):
        match = self.url_re.match(self.url)

        res = http.post(self.flashvars_url,
                        data=dict(
                            broadcaster=match.group("broadcaster") or "Verm",
                            stream_id=match.group("channel_id") or match.group("highlight_id")))

        flashvars = http.json(res, schema=self.flashvars_schema)

        if flashvars.get("pereakaurl"):
            url = self.pereakaurl.format(flashvars.get("pereakaurl").strip("/"))
            return HLSStream.parse_variant_playlist(self.session, url)

        elif flashvars.get("akaurl"):
            url = self.akaurl.format(flashvars.get("akaurl").strip("/"))
            return HLSStream.parse_variant_playlist(self.session, url)

        elif flashvars.get("stream"):
            self.logger.error("OctoStreams are not currently supported")


__plugin__ = DingitTV
