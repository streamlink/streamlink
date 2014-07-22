import re

from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin.api import validate
from livestreamer.options import Options

# Import base classes from a support plugin that must exist in the
# same directory as this plugin.
from livestreamer.plugin.api.support_plugin import justintv_common

JustinTVPluginBase = justintv_common.PluginBase
JustinTVAPIBase = justintv_common.APIBase

_url_re = re.compile(r"http(s)?://([\w\.]+)?twitch.tv/[^/]+(/[ab]/\d+)?")
_time_re = re.compile("""
    (?:
        (?P<hours>\d+)h
    )?
    (?:
        (?P<minutes>\d+)m
    )?
    (?:
        (?P<seconds>\d+)s
    )?
""", re.VERBOSE)

_user_schema = validate.Schema(
    {
        validate.optional("display_name"): validate.text
    },
    validate.get("display_name")
)
_video_schema = validate.Schema(
    {
        "chunks": {
            validate.text: [{
                "length": int,
                "url": validate.text
            }]
        },
        "restrictions": { validate.text: validate.text },
        "start_offset": int,
        "end_offset": int,
    }
)


def time_to_offset(t):
    match = _time_re.match(t)
    if match:
        offset = int(match.group("hours") or "0") * 60 * 60
        offset += int(match.group("minutes") or "0") * 60
        offset += int(match.group("seconds") or "0")
    else:
        offset = 0

    return offset


class TwitchAPI(JustinTVAPIBase):
    def channel_info(self, channel, **params):
        return self.call("/api/channels/{0}".format(channel), **params)

    def channel_subscription(self, channel, **params):
        return self.call("/api/channels/{0}/subscription".format(channel), **params)

    def channel_viewer_info(self, channel, **params):
        return self.call("/api/channels/{0}/viewer".format(channel), **params)

    def user(self, **params):
        return self.call("/kraken/user", **params)

    def videos(self, video_id, **params):
        return self.call("/api/videos/{0}".format(video_id), **params)


class Twitch(JustinTVPluginBase):
    options = Options({
        "cookie": None,
        "oauth_token": None,
        "password": None
    })

    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def __init__(self, url):
        JustinTVPluginBase.__init__(self, url)

        self.api = TwitchAPI(host="twitch.tv",
                             beta=self.subdomain == "beta")

    def _authenticate(self):
        oauth_token = self.options.get("oauth_token")

        if oauth_token and not self.api.oauth_token:
            self.logger.info("Attempting to authenticate using OAuth token")
            self.api.oauth_token = oauth_token
            user = self.api.user(schema=_user_schema)

            if user:
                self.logger.info("Successfully logged in as {0}", user)
            else:
                self.logger.error("Failed to authenticate, the access token "
                                  "is not valid")
        else:
            return JustinTVPluginBase._authenticate(self)

    def _get_video_streams(self):
        self._authenticate()

        if self.video_type == "b":
            self.video_type = "a"

        try:
            videos = self.api.videos(self.video_type + self.video_id,
                                     schema=_video_schema)
        except PluginError as err:
            if "HTTP/1.1 0 ERROR" in str(err):
                raise NoStreamsError(self.url)
            else:
                raise

        # Parse the "t" query parameter on broadcasts and adjust
        # start offset if needed.
        time_offset = self.params.get("t")
        if time_offset:
            videos["start_offset"] += time_to_offset(self.params.get("t"))

        return self._create_playlist_streams(videos)


__plugin__ = Twitch
