import requests

from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.options import Options
from livestreamer.utils import res_json, urlget

# Import base class from a support plugin that must exist in the
# same directory as this plugin.
from livestreamer.plugin.api.support_plugin import justintv_common


SWF_URL = "http://www-cdn.jtvnw.net/swflibs/TwitchPlayer.swf"
TWITCH_API_HOST = "https://api.twitch.tv"


class TwitchAPI(object):
    def __init__(self):
        self.session = requests.session()
        self.oauth_token = None

    def add_cookies(self, cookies):
        for cookie in cookies.split(";"):
            try:
                name, value = cookie.split("=")
            except ValueError:
                continue

            self.session.cookies[name.strip()] = value.strip()

    def call(self, path, **extra_params):
        params = dict(as3="t", **extra_params)

        if self.oauth_token:
            params["oauth_token"] = self.oauth_token

        url = "{0}{1}.json".format(TWITCH_API_HOST, path)
        res = urlget(url, params=params, session=self.session)

        return res_json(res)

    def token(self):
        res = self.call("/api/viewer/token")

        return res.get("token")

    def channel_access_token(self, channel):
        res = self.call("/api/channels/{0}/access_token".format(channel))

        return res.get("sig"), res.get("token")

    def channel_info(self, channel):
        return self.call("/api/channels/{0}".format(channel))

    def channel_subscription(self, channel):
        return self.call("/api/channels/{0}/subscription".format(channel))

    def channel_viewer_info(self, channel):
        return self.call("/api/channels/{0}/viewer".format(channel))

    def viewer_info(self):
        return self.call("/api/viewer/info")


class Twitch(justintv_common.JustinTVBase):
    options = Options({
        "cookie": None,
    })

    @classmethod
    def can_handle_url(self, url):
        return "twitch.tv" in url

    def __init__(self, url):
        justintv_common.JustinTVBase.__init__(self, url)

        self.api = TwitchAPI()

    def _authorize(self):
        cookies = self.options.get("cookie")

        if cookies:
            self.logger.info("Attempting to authenticate using cookies")

            self.api.add_cookies(cookies)
            self.api.oauth_token = self.api.token()

            viewer = self.api.viewer_info()
            login = viewer.get("login")

            if login:
                self.logger.info("Successfully logged in as {0}", login)
            else:
                self.logger.error("Failed to authenticate, your cookies may "
                                  "have expired")

        try:
            sig, token = self.api.channel_access_token(self.channel)
        except PluginError as err:
            if "404 Client Error" in str(err):
                raise NoStreamsError(self.url)
            else:
                raise

        return sig, token

    def _get_desktop_streams(self):
        sig, token = self._authorize()

        self.logger.debug("Fetching desktop streams")
        res = self.usher.find(self.channel,
                              nauthsig=sig,
                              nauth=token)

        return self._parse_find_result(res, SWF_URL)


__plugin__ = Twitch
