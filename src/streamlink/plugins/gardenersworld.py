from __future__ import print_function

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugins.brightcove import BrightcovePlayer


class GardenersWorld(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?gardenersworld\.com/")
    object_re = re.compile('''<object.*?id="brightcove-pod-object".*?>(.*?)</object>''', re.DOTALL)
    param_re = re.compile('''<param.*?name="(.*?)".*?value="(.*?)".*?/>''')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        page = http.get(self.url)
        object_m = self.object_re.search(page.text)
        if object_m:
            object_t = object_m.group(1)
            params = {}
            for param_m in self.param_re.finditer(object_t):
                params[param_m.group(1)] = param_m.group(2)

            return BrightcovePlayer.from_player_key(self.session,
                                                    params.get("playerID"),
                                                    params.get("playerKey"),
                                                    params.get("videoID"),
                                                    url=self.url)


__plugin__ = GardenersWorld
