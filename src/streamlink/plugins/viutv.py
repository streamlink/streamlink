import datetime
import json
import logging
import random
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://viu\.tv/ch/(\d+)"
))
class ViuTV(Plugin):
    api_url = "https://api.viu.now.com/p8/2/getLiveURL"

    @property
    def device_id(self):
        return "".join(random.choice("abcdef0123456789") for _ in range(18))

    @property
    def channel_id(self):
        return self.match.group(1)

    def _get_streams(self):
        api_res = self.session.http.post(self.api_url,
                                         headers={"Content-Type": 'application/json'},
                                         data=json.dumps({"callerReferenceNo": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                                                          "channelno": self.channel_id.zfill(3),
                                                          "mode": "prod",
                                                          "deviceId": self.device_id,
                                                          "deviceType": "5",
                                                          "format": "HLS"}))
        data = self.session.http.json(api_res)
        if data['responseCode'] == 'SUCCESS':
            for stream_url in data.get("asset", {}).get("hls", {}).get("adaptive", []):
                return HLSStream.parse_variant_playlist(self.session, stream_url)
        else:
            log.error("Failed to get stream URL: {0}".format(data['responseCode']))


__plugin__ = ViuTV
