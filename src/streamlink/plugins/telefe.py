"""
$description Video content from Telefe, an Argentine TV station.
$url mitelefe.com
$type live
$region Argentina
"""

import logging
import re

from streamlink.compat import urljoin
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https://mitelefe\.com/vivo"))
class Telefe(Plugin):
    _re_content = re.compile(r"=\s*(\{.+\});", re.DOTALL | re.MULTILINE)

    def _get_streams(self):
        self.title, hls_url = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(), 'HLS')]/text()"),
                validate.any(None, validate.all(
                    validate.transform(self._re_content.search),
                    validate.any(None, validate.all(
                        validate.get(1),
                        validate.parse_json(),
                        {validate.text: {"children": {"top": {"model": {"videos": [{
                            "title": validate.text,
                            "sources": validate.all(
                                [{"url": validate.text, "type": validate.text}],
                                validate.filter(lambda p: p["type"].lower() == "hls"),
                                validate.get((0, "url")))
                        }]}}}}},
                        validate.transform(lambda k: next(iter(k.values()))),
                        validate.get(("children", "top", "model", "videos", 0)),
                        validate.union_get("title", "sources")
                    ))
                ))
            )
        )
        return HLSStream.parse_variant_playlist(self.session, urljoin(self.url, hls_url))


__plugin__ = Telefe
