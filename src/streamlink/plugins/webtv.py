import json
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


class WebTV(Plugin):
    _url_re = re.compile(r"http(?:s)?://(\w+)\.web.tv/?")
    _sources_re = re.compile(r'"sources": (\[.*?\]),', re.DOTALL)
    _sources_schema = validate.Schema([
        {
            u"src": validate.text,
            u"type": validate.text,
            u"label": validate.text
        }
    ])

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        """
        Find the streams for web.tv
        :return:
        """
        headers = {}
        res = http.get(self.url, headers=headers)
        headers["Referer"] = self.url

        sources = self._sources_re.findall(res.text)
        if len(sources):
            sdata = parse_json(sources[0], schema=self._sources_schema)
            for source in sdata:
                self.logger.debug("Found stream of type: {}", source[u'type'])
                if source[u'type'] == u"application/vnd.apple.mpegurl":
                    # if the url has no protocol, assume it is http
                    url = source[u"src"]
                    if url.startswith("//"):
                        url = "http:" + url

                    try:
                        # try to parse the stream as a variant playlist
                        variant = HLSStream.parse_variant_playlist(self.session, url, headers=headers)
                        if variant:
                            for q, s in variant.items():
                                yield q, s
                        else:
                            # and if that fails, try it as a plain HLS stream
                            yield 'live', HLSStream(self.session, url, headers=headers)
                    except IOError:
                        self.logger.warning("Could not open the stream, perhaps the channel is offline")


__plugin__ = WebTV
