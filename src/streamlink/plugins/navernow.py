import re, json

from streamlink.plugin import Plugin, PluginError
from streamlink.stream import HLSStream

class NaverNow(Plugin):
    _url_re = re.compile(r"https?://now\.naver\.com/(\d+)")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @property
    def channel_id(self):
        return self._url_re.match(self.url).group(1)

    def _get_streams(self):
        self._stream_status_url = "https://now.naver.com/api/nnow/v1/stream/%s/livestatus/" % self.channel_id

        stream_info = self.session.http.get(self._stream_status_url)

        if stream_info.status_code != 200:
            raise PluginError("Could not get stream info. HTTP Status Code %s" % stream_info.status_code)
        
        stream_json = json.loads(stream_info.text)

        if stream_json["status"]["status"] != "ONAIR":
            raise PluginError("Stream is offline.")
        
        streams = dict()
        stream_audio = stream_json["status"]["liveStreamUrl"]
        stream_video = stream_json["status"]["videoStreamUrl"]

        if not stream_audio:
            raise PluginError("Could not find stream url!")
        
        streams["audio"] = HLSStream.parse_variant_playlist(self.session, stream_audio).popitem()[1]

        if stream_video:            
            resolutions = HLSStream.parse_variant_playlist(self.session, stream_video)
            for k, v in resolutions.items():
                streams[k] = v

        return streams

__plugin__ = NaverNow
