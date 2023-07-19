import re
import streamlink.plugin
import streamlink.stream
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
import requests

@pluginmatcher(
    name="default",
    pattern=re.compile(r"https?://(?:www\.)?tiktok\.com/@(?P<account_id>[^/]+)/live?"),
)
class TikTok(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?tiktok\.com/@(?P<account_id>[^/]+)/live?$")
    API_URL = "https://www.tiktok.com/api/live/detail/"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        response = requests.get(self.url)
        html_content = response.text

        roomId = re.search(r'room_id=([0-9]*)', html_content).group(0).split("=")[1]
        res =  requests.get(self.API_URL + '/?aid=1988&roomID=' + roomId)
        print(res.text)
        jsonres = res.json()
        hls_url = jsonres['LiveRoomInfo']['liveUrl']
        print(hls_url)
        return {"live": HLSStream(self.session, hls_url)}


__plugin__ = TikTok
