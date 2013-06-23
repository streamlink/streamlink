from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, res_json

class Euronews(Plugin):
    SWFURL = "http://euronews.com/media/player_live_1_14.swf"
    APIURL = "http://euronews.hexaglobe.com/json/"
    GEOIPURL = "http://freegeoip.net/json/"

    @classmethod
    def can_handle_url(self, url):
        return "euronews.com" in url

    def _get_streams(self):
        country_code = urlparse(self.url).netloc.split(".")[0]

        self.logger.debug("Fetching stream info")
        res = urlget(self.APIURL)
        json = res_json(res)

        if not isinstance(json, dict):
            raise PluginError("Invalid JSON response")
        elif not ("primary" in json or "secondary" in json):
            raise PluginError("Invalid JSON response")

        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Euronews plugin")

        streams = {}

        self.logger.debug("Euronews Countries:{0}", " ".join(json["primary"].keys()))

        if not (country_code in json["primary"] or country_code in json["secondary"]):
            res = urlget(self.GEOIPURL)
            geo = res_json(res)
            if isinstance(json, dict) and "country_code" in geo:
                country_code = geo["country_code"].lower()
                if not (country_code in json["primary"] or country_code in json["secondary"]):
                    country_code = "en"
            else:
                country_code = "en"

        for site in ("primary", "secondary"):
            for quality in json[site][country_code]["rtmp_flash"]:
                stream = json[site][country_code]["rtmp_flash"][quality]
                name = quality + "k"
                if site == "secondary":
                    name += "_alt"
                streams[name] = RTMPStream(self.session, {
                    "rtmp": stream["server"],
                    "playpath" : stream["name"],
                    "swfUrl": self.SWFURL,
                    "live": True
                })

        if len(streams) == 0:
            raise NoStreamsError(self.url)

        return streams


__plugin__ = Euronews
