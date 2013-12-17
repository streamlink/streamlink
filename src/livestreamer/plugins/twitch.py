import re

from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.options import Options

# Import base classes from a support plugin that must exist in the
# same directory as this plugin.
from livestreamer.plugin.api.support_plugin import justintv_common

JustinTVPluginBase = justintv_common.PluginBase
JustinTVAPIBase = justintv_common.APIBase


def time_to_offset(t):
    match = re.match(r"((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?", t)
    if match:
        offset = int(match.group("minutes") or "0") * 60
        offset += int(match.group("seconds") or "0")
    else:
        offset = 0

    return offset


class TwitchAPI(JustinTVAPIBase):
    def __init__(self):
        JustinTVAPIBase.__init__(self, host="twitch.tv")

    def channel_info(self, channel):
        return self.call("/api/channels/{0}".format(channel))

    def channel_subscription(self, channel):
        return self.call("/api/channels/{0}/subscription".format(channel))

    def channel_viewer_info(self, channel):
        return self.call("/api/channels/{0}/viewer".format(channel))

    def user(self):
        return self.call("/kraken/user")

    def videos(self, video_id):
        return self.call("/api/videos/{0}".format(video_id))


class Twitch(JustinTVPluginBase):
    options = Options({
        "cookie": None,
        "oauth_token": None,
        "password": None
    })

    @classmethod
    def can_handle_url(self, url):
        return "twitch.tv" in url

    def __init__(self, url):
        JustinTVPluginBase.__init__(self, url)

        self.api = TwitchAPI()

    def _authenticate(self):
        oauth_token = self.options.get("oauth_token")

        if oauth_token and not self.api.oauth_token:
            self.logger.info("Attempting to authenticate using OAuth token")
            self.api.oauth_token = oauth_token
            user = self.api.user().get("display_name")

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
            videos = self.api.videos(self.video_type + self.video_id)
        except PluginError as err:
            if "HTTP/1.1 0 ERROR" in str(err):
                raise NoStreamsError(self.url)
            else:
                raise

        # Parse the "t" query parameter on broadcasts and adjust
        # start offset if needed.
        time_offset = self.params.get("t")
        if time_offset and self.video_type == "a":
            videos["start_offset"] = time_to_offset(self.params.get("t"))

        return self._create_playlist_streams(videos)


__plugin__ = Twitch
