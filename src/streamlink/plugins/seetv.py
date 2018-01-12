import re

import time

from streamlink import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.compat import urlparse, parse_qsl


class SeeTV(Plugin):
    _url_re = re.compile(r"""(http://seetv.tv/vse-tv-online/.*?)(#|$)""")
    _api_url = "http://seetv.tv/get/player/{0}"
    _main_source_re = re.compile(r'stream-active-main" rel="(\d+)"')
    api_schema = validate.Schema(validate.any(
        {
            "status": False,
            "text": validate.text
        },
        {
            "status": True,
            "file": validate.any(
                validate.all(validate.url(), validate.transform(lambda x: x.replace("%3F", "?"))),
                validate.all(validate.text, validate.startswith("<"))
            ),
            "height": validate.text,
        }
    ))

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @property
    def referer(self):
        return self._url_re.match(self.url).group(1)

    def _get_tv_link(self):
        res = http.get(self.url)
        link_m = self._main_source_re.search(res.text)
        return link_m and link_m.group(1)

    def _get_streams(self):
        http.headers.update({"User-Agent": useragents.CHROME,
                             "Referer": self.referer})
        fragment = dict(parse_qsl(urlparse(self.url).fragment))
        link = fragment.get("link")
        if not link:
            link = self._get_tv_link()

        if not link:
            self.logger.error("Missing link fragment: stream unavailable")
            return

        player_url = self._api_url.format(link)
        self.logger.debug("Requesting player API: {0} (referer={1})", player_url, self.referer)
        res = http.get(player_url,
                       params={"_": int(time.time() * 1000)},
                       headers={"X-Requested-With": "XMLHttpRequest"})

        try:
            data = http.json(res, schema=self.api_schema)
        except PluginError as e:
            print(e)
            self.logger.error("Cannot play this stream type")
        else:
            if data["status"]:
                if data["file"].startswith("<"):
                    self.logger.error("Cannot play embedded streams")
                else:
                    return HLSStream.parse_variant_playlist(self.session, data["file"])
            else:
                self.logger.error(data["text"])


__plugin__ = SeeTV
