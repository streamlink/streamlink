from livestreamer.exceptions import PluginError, NoStreamsError

# Import base classes from a support plugin that must exist in the
# same directory as this plugin.
from livestreamer.plugin.api.support_plugin import justintv_common

JustinTVPluginBase = justintv_common.PluginBase
JustinTVAPIBase = justintv_common.APIBase


class TwitchAPI(JustinTVAPIBase):
    def __init__(self):
        JustinTVAPIBase.__init__(self, host="twitch.tv")

    def channel_info(self, channel):
        return self.call("/api/channels/{0}".format(channel))

    def channel_subscription(self, channel):
        return self.call("/api/channels/{0}/subscription".format(channel))

    def channel_viewer_info(self, channel):
        return self.call("/api/channels/{0}/viewer".format(channel))

    def videos(self, video_id):
        return self.call("/api/videos/{0}".format(video_id))


class Twitch(JustinTVPluginBase):
    @classmethod
    def can_handle_url(self, url):
        return "twitch.tv" in url

    def __init__(self, url):
        JustinTVPluginBase.__init__(self, url)

        self.api = TwitchAPI()

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

        return self._create_playlist_streams(videos)


__plugin__ = Twitch
