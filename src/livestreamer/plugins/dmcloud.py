from livestreamer.exceptions import NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import HLSStream
from livestreamer.utils import urlget, parse_json

import re

class DMCloud(Plugin):

    @classmethod
    def can_handle_url(self, url):
        return "api.dmcloud.net" in url

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = urlget(self.url)

        match = re.search("var info = (.*);", res.text)
        if not match:
            raise NoStreamsError(self.url)

        json = parse_json(match.group(1))
        if not "ios_url" in json:
            raise NoStreamsError(self.url)

        streams = HLSStream.parse_variant_playlist(self.session, json["ios_url"])

        return streams


__plugin__ = DMCloud
