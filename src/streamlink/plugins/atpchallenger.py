"""
$description Professional tennis tournaments.
$url www.atptour.com/en/atp-challenger-tour/challenger-tv
$type live, vod
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?atptour.com/en/atp-challenger-tour/challenger-tv"
))
class AtpChallengerTour(Plugin):
    _re_window_config = re.compile(r""".*window.config\s*=\s*(?P<json>{.*?});""", re.DOTALL)

    def _get_streams(self):
        iframe_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string("normalize-space(.//iframe[contains(@src,'livestream.com')]/@src)")
        ))
        if not iframe_url:
            return None

        stream_data = self.session.http.get(iframe_url, schema=validate.Schema(
            validate.transform(self._re_window_config.search),
            validate.any(None, validate.all(
                validate.get("json"),
                validate.parse_json(),
                {
                    "event": {
                        "full_name": str,
                        "feed": {
                            "data": list
                        }
                    }
                },
                validate.get("event")
            ))
        ))
        if not stream_data:
            return None
        if len(stream_data['feed']['data']) < 1:
            return None
        if 'data' not in stream_data['feed']['data'][0]:
            return None
        if 'secure_m3u8_url' not in stream_data['feed']['data'][0]['data']:
            return None
        self.title = stream_data['full_name'].replace(" ", "")
        self.category = "atp-challenger"
        self.author = "ATP"
        stream_url = stream_data['feed']['data'][0]['data']['secure_m3u8_url']

        yield from HLSStream.parse_variant_playlist(self.session, stream_url).items()


__plugin__ = AtpChallengerTour
