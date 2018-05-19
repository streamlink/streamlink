from __future__ import print_function

import re

from streamlink import NoPluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.utils import update_scheme


class GardenersWorld(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?gardenersworld\.com/")
    iframe_re = re.compile('''iframe src=(?P<quote>["'])(?P<url>.*?)(?P=quote)''')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        page = http.get(self.url)
        iframe = self.iframe_re.search(page.text)
        if iframe:
            self.logger.debug("Handing off of {0}".format(iframe.group("url")))
            try:
                return self.session.streams(update_scheme(self.url, iframe.group("url")))
            except NoPluginError:
                self.logger.error("Handing off of {0} failed".format(iframe.group("url")))
                return None


__plugin__ = GardenersWorld
