from livestreamer.plugin import Plugin

import re

URL_REGEX = r"http://(?:www\.)?speedrunslive.com/#!/(?P<user>\w+)"
TWITCH_URL = "http://www.twitch.tv/"

class SpeedRunsLive(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return re.search(URL_REGEX, url)

    def _get_streams(self):
        match = re.search(URL_REGEX, self.url)
        if match:
            url = TWITCH_URL + match.group("user")
            plugin = self.session.resolve_url(url)
            return plugin.get_streams()


__plugin__ = SpeedRunsLive
