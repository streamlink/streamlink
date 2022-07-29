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
        if not "key" in params:
            log.error("The Lura url does not have a key")
            return

        b64 = urllib.parse.unquote(params["key"])
        bytes = base64.b64decode(b64)
        str = bytes.decode("utf-8")
        j = json.loads(str)

        if not "anvack" in j or not "v" in j:
            log.error("The Lura url does not have the expected data encoded")
            return
        
        url = f"https://tkx.mp.lura.live/rest/v2/mcp/video/{j['v']}?anvack={j['anvack']}"
        print(url)
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
                    "published_urls": [{
                        "embed_url": validate.url(),
                        "format":"m3u8-variant",
                    }],
                },
                validate.get(("published_urls", 0, "embed_url")),
            )
        publishedUrl = schema_data.validate(resultMatch.group(2))
        return HLSStream.parse_variant_playlist(self.session, publishedUrl)

__plugin__ = Lura
