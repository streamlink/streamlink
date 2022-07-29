"""
$description Global live streaming platform used by various US media outlets, including many local news stations.
$url w3.mp.lura.live
$type live
"""

import logging
import re
import base64
import urllib
import json

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.plugin import parse_params
from streamlink.stream.hls import HLSStream
from streamlink.plugin.api import validate

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?P<url>w3\.mp\.lura\.live/player/prod/v3/anvload\.html\?)(?:(?P<params>.+))?"
))
class Lura(Plugin):

    def _get_streams(self):
        data = self.match.groupdict()
        params = parse_params(data.get("params"))
        log.debug(f"params={params}")
        if "key" not in params:
            log.error("The Lura url does not have a key")
            return

        key_b64 = urllib.parse.unquote(params["key"])
        key_bytes = base64.b64decode(key_b64)
        key_str = key_bytes.decode("utf-8")
        key_json = json.loads(key_str)

        if "anvack" not in key_json or "v" not in key_json:
            log.error("The Lura url does not have the expected data encoded")
            return

        url = f"https://tkx.mp.lura.live/rest/v2/mcp/video/{key_json['v']}?anvack={key_json['anvack']}"
        postResult = self.session.http.post(
            url
        )
        resultMatch = re.match(r"^(anvatoVideoJSONLoaded\()?({.*})(\()?", postResult.text)
        if (not resultMatch) or (not resultMatch.group(2)):
            log.error("The response does not have the expected data")
            return

        schema_data = validate.Schema(
            validate.parse_json(),
            {
                "def_title": str,
                "published_urls": [{
                    "embed_url": validate.url(),
                    "format": "m3u8-variant",
                }],
            },
        )

        data = schema_data.validate(resultMatch.group(2))
        self.title = data["def_title"]
        return HLSStream.parse_variant_playlist(self.session, data["published_urls"][0]["embed_url"])


__plugin__ = Lura
