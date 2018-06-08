from __future__ import print_function
import re
import string
from base64 import b64decode
from pprint import pprint

from streamlink import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.compat import urlparse
from streamlink.utils import parse_json


class ovvaTV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?ovva.tv/(?:ua/)?tvguide/.*?/online")
    iframe_re = re.compile(r"iframe .*?src=\"((?:https?:)?//(?:\w+\.)?ovva.tv/[^\"]+)\"", re.DOTALL)
    data_re = re.compile(r"ovva\(\'(.*?)\'\);")
    ovva_data_schema = validate.Schema({
        "url": validate.url()
    }, validate.get("url"))
    ovva_redirect_schema = validate.Schema(validate.all(
        validate.transform(lambda x: x.split("=")),
        ['302', validate.url()],
        validate.get(1)
    ))

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def find_iframe(self, res):
        for url in self.iframe_re.findall(res.text):
            if url.startswith("//"):
                p = urlparse(self.url)
                return "{0}:{1}".format(p.scheme, url)
            else:
                return url

    @Plugin.broken()
    def _get_streams(self):
        http.headers = {"User-Agent": useragents.ANDROID}
        res = http.get(self.url)
        iframe_url = self.find_iframe(res)

        if iframe_url:
            self.logger.debug("Found iframe: {0}", iframe_url)
            res = http.get(iframe_url, headers={"Referer": self.url})
            data = self.data_re.search(res.text)
            if data:
                try:
                    ovva_url = parse_json(b64decode(data.group(1)).decode("utf8"), schema=self.ovva_data_schema)
                    stream_url = http.get(ovva_url, schema=self.ovva_redirect_schema)
                except PluginError as e:
                    self.logger.error("Could not find stream URL: {0}", e)
                else:
                    return HLSStream.parse_variant_playlist(self.session, stream_url)
            else:
                self.logger.error("Could not find player data.")


__plugin__ = ovvaTV
