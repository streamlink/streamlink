from livestreamer.compat import urlparse, urljoin
from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, parse_json

import re

class Filmon(Plugin):
    SWFURL = "http://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf"

    @classmethod
    def can_handle_url(self, url):
        return "filmon.com" in url

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = urlget(self.url)

        match = re.search("var current_channel = (.*);", res.text)
        if match:
            json = parse_json(match.group(1))
        else:
            raise NoStreamsError(self.url)

        if not isinstance(json, dict):
            raise PluginError("Invalid JSON response")
        elif not "streams" in json:
            raise NoStreamsError(self.url)

        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Filmon plugin")

        match = re.search("var flash_config = (.*);", res.text)
        if match:
            config = parse_json(match.group(1))
            if "streamer" in config:
                self.SWFURL = urljoin(self.SWFURL, config["streamer"])

        streams = {}

        for stream in json["streams"]:
            if not ("url" in stream and "name" in stream):
                continue

            parsed = urlparse(stream["url"])

            if not parsed.scheme.startswith("rtmp"):
                continue

            name = stream["quality"]
            streams[name] = RTMPStream(self.session, {
                "rtmp": stream["url"],
                "pageUrl": self.url,
                "swfUrl": self.SWFURL,
                "playpath": stream["name"],
                "app": "{0}?{1}".format(parsed.path[1:], parsed.query),
                "live": True
            })

        return streams


__plugin__ = Filmon
