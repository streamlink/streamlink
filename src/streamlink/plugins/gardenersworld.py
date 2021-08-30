import logging
import re

from streamlink import NoPluginError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api.utils import itertags
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?gardenersworld\.com/"
))
class GardenersWorld(Plugin):
    def _get_streams(self):
        page = self.session.http.get(self.url)
        for iframe in itertags(page.text, "iframe"):
            url = iframe.attributes["src"]
            log.debug(f"Handing off of {url}")
            try:
                return self.session.streams(update_scheme(self.url, url))
            except NoPluginError:
                log.error(f"Handing off of {url} failed")
                return None


__plugin__ = GardenersWorld
