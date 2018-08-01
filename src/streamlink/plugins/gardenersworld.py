from __future__ import print_function

import re

from streamlink import NoPluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api.utils import itertags
from streamlink.utils import update_scheme


class GardenersWorld(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?gardenersworld\.com/")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        page = self.session.http.get(self.url)
        for iframe in itertags(page.text, u"iframe"):
            url = iframe.attributes["src"]
            self.logger.debug("Handing off of {0}".format(url))
            try:
                return self.session.streams(update_scheme(self.url, url))
            except NoPluginError:
                self.logger.error("Handing off of {0} failed".format(url))
                return None


__plugin__ = GardenersWorld
