import json
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils.url import update_scheme


class InvintusMedia(Plugin):
    WSC_API_KEY = "7WhiEBzijpritypp8bqcU7pfU9uicDR"  # hard coded in the middle of https://player.invintus.com/app.js
    API_URL = "https://api.v3.invintusmedia.com/v2/Event/getDetailed"

    url_re = re.compile(r"https?://player\.invintus\.com/\?clientID=(\d+)&eventID=(\d+)")
    api_response_schema = validate.Schema({"data": {"streamingURIs": {"main": validate.url()}}})

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        m = self.url_re.match(self.url)
        postdata = {
            "clientID": m.group(1),
            "showEncoder": True,
            "showMediaAssets": True,
            "showStreams": True,
            "includePrivate": False,
            "advancedDetails": True,
            "VAST": True,
            "eventID": m.group(2)
        }
        headers = {
            "Content-Type": "application/json",
            "wsc-api-key": self.WSC_API_KEY,
            "Authorization": "embedder"
        }
        res = self.session.http.post(self.API_URL, data=json.dumps(postdata), headers=headers)
        api_response = self.session.http.json(res, schema=self.api_response_schema)
        if api_response is None:
            return

        hls_url = api_response["data"]["streamingURIs"]["main"]
        return HLSStream.parse_variant_playlist(self.session, update_scheme(self.url, hls_url))


__plugin__ = InvintusMedia
