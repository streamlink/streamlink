import re
import json
try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream


class InvintusMedia(Plugin):
    url_re = re.compile(r"https?://player\.invintus\.com/\?clientID=\d+&eventID=\d+")
    WSC_API_KEY = "7WhiEBzijpritypp8bqcU7pfU9uicDR"  # hard coded in the middle of https://player.invintus.com/app.js
    API_URL = "https://api.v3.invintusmedia.com/v2/Event/getDetailed"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        query = parse_qs(urlparse(self.url).query)
        postdata = {
            "clientID": query.get('clientID')[0],
            "showEncoder": True,
            "showMediaAssets": True,
            "showStreams": True,
            "includePrivate": False,
            "advancedDetails": True,
            "VAST": True,
            "eventID": query.get('eventID')[0]
        }
        headers = {
            "Content-Type": "application/json",
            "wsc-api-key": self.WSC_API_KEY,
            "Authorization": "embedder"
        }
        api_response = self.session.http.post(self.API_URL, data=json.dumps(postdata), headers=headers).json()
        if "data" not in api_response:
            return
        if "streamingURIs" not in api_response["data"]:
            return
        if not isinstance(api_response["data"]["streamingURIs"], dict):
            return
        if "main" not in api_response["data"]["streamingURIs"]:
            return
        return HLSStream.parse_variant_playlist(self.session, "https:{}".format(api_response["data"]["streamingURIs"]["main"]))


__plugin__ = InvintusMedia
