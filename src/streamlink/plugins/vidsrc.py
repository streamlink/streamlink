import re
import streamlink.plugin
import streamlink.stream
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream

#https://vidsrc.me/embed/tt0396269/

@pluginmatcher(
    name="default",
    pattern=re.compile(r"https?://(?:www\.)?vidsrc\.me/embed/(?P<video_id>[^/]+)/?"),
)
class VidSrc(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?vidsrc\.me/embed/(?P<video_id>[^/]+)/?$")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        #res = self.session.http.get(self.url)
        # print(res)
        # m = self.url_re.match(res.url)
        # video_id = m.group("video_id")
        # api_url = f"https://vidsrc.me/embed/tt0396269/"
        headers = {
            "Referer": self.url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }
        data = self.session.http.get(self.url, headers=headers)
        print(data.text)
        # streams = validate(data, validate.Schema({
        #     "success": bool,
        #     "result": [{
        #         "type": str,
        #         "label": str,
        #         "file": validate.url(scheme="http"),
        #         validate.optional("format"): str,
        #         validate.optional("height"): int,
        #         validate.optional("width"): int
        #     }]
        # }))
        # for stream in streams["result"]:
        #     if stream["type"] == "hls":
        #         yield stream["label"], HLSStream(self.session, stream["file"])
# Register the plugin
#streamlink.plugin.register_plugin(VidsrcPlugin)
__plugin__ = VidSrc
