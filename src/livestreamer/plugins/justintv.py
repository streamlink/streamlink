from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.utils import res_xml, urlget

# Import base class from a support plugin that must exist in the
# same directory as this plugin.
from livestreamer.plugin.api.support_plugin import justintv_common


METADATA_URL = "http://www.justin.tv/meta/{0}.xml?on_site=true"
SWF_URL = "http://www.justin.tv/widgets/live_embed_player.swf"


class JustinTV(justintv_common.JustinTVBase):
    @classmethod
    def can_handle_url(self, url):
        return "justin.tv" in url

    def _get_metadata(self):
        url = METADATA_URL.format(self.channel)
        cookies = {}

        for cookie in self.options.get("cookie").split(";"):
            try:
                name, value = cookie.split("=")
            except ValueError:
                continue

            cookies[name.strip()] = value.strip()

        res = urlget(url, cookies=cookies)
        meta = res_xml(res, "metadata XML")

        metadata = {}
        metadata["access_guid"] = meta.findtext("access_guid")
        metadata["login"] = meta.findtext("login")
        metadata["title"] = meta.findtext("title")

        return metadata

    def _authenticate(self):
        if self.options.get("cookie") is not None:
            self.logger.info("Attempting to authenticate using cookies")

            try:
                metadata = self._get_metadata()
            except PluginError as err:
                if "404 Client Error" in str(err):
                    raise NoStreamsError(self.url)
                else:
                    raise

            chansub = metadata.get("access_guid")
            login = metadata.get("login")

            if login:
                self.logger.info("Successfully logged in as {0}", login)
            else:
                self.logger.error("Failed to authenticate, your cookies may "
                                  "have expired")

            return chansub

    def _get_desktop_streams(self):
        chansub = self._authenticate()

        self.logger.debug("Fetching desktop streams")
        res = self.usher.find(self.channel,
                              channel_subscription=chansub)

        return self._parse_find_result(res, SWF_URL)

__plugin__ = JustinTV
