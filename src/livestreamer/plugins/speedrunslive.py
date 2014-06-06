import re

from livestreamer.plugin import Plugin

TWITCH_URL_FORMAT = "http://www.twitch.tv/{0}"

_url_re = re.compile("http://(?:www\.)?speedrunslive.com/#!/(?P<user>\w+)")


class SpeedRunsLive(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        if match:
            url = TWITCH_URL_FORMAT.format(match.group("user"))
            return self.session.streams(url)


__plugin__ = SpeedRunsLive
