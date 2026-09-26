"""
$description Ukrainian OTT TV service owned by TOV Platforma TV.
$url youtv.ua
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?youtv\.ua/(?:\w{2}/)?tv/[\w-]+"),
)
class YouTVUA(Plugin):
    AJAX_URL = "https://youtv.ua/core/ajax/controller.php"

    def _get_streams(self):
        js_data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'function play (')][1]/text()"),
            ),
        )

        if not js_data:
            return

        offset = js_data.find("function play (")
        if offset == -1:
            return

        play_js = js_data[offset:]

        channel_match = re.search(r"\bid:\s*['\"](\d+)['\"]", play_js)
        if not channel_match:  # In case an update changes 'id' from a string literal to a variable reference
            channel_match = re.search(r"var\s+channel\s*=\s*(\d+);", js_data)

        uuid_match = re.search(r"\buuid:\s*['\"]([a-f0-9]+)['\"]", play_js)
        hash_match = re.search(r"\bhash:\s*['\"]([a-f0-9]+)['\"]", play_js)

        if not (channel_match and uuid_match and hash_match):
            return

        channel_id = channel_match.group(1)
        uuid = uuid_match.group(1)
        hash_val = hash_match.group(1)

        api_data = self.session.http.post(
            self.AJAX_URL,
            headers={
                "Referer": self.url,
                "X-Requested-With": "XMLHttpRequest",
            },
            data={
                "do": "website",
                "action": "channel",
                "uuid": uuid,
                "hash": hash_val,
                "lang": "uk",
                "id": channel_id,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "status": str,
                    validate.optional("source"): validate.none_or_all(validate.url()),
                    validate.optional("client"): validate.none_or_all(str),
                    validate.optional("sign"): validate.none_or_all(str),
                },
            ),
        )

        if api_data.get("status") != "success" or not api_data.get("source"):
            return

        headers = {}
        if api_data.get("client"):
            headers["Smart-TV-User-Agent"] = api_data["client"]
        if api_data.get("sign"):
            headers["Device-Sign"] = api_data["sign"]

        return HLSStream.parse_variant_playlist(
            self.session,
            api_data["source"],
            headers=headers,
        )


__plugin__ = YouTVUA
