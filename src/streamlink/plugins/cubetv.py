import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink import NoStreamsError
from streamlink.utils import parse_json

class CubeTV(Plugin):

    _url_re = re.compile(r"https?://(www\.)?cube\.tv/(?P<channel>[^/]{2,})")

    _channel_info_api_url_base = "https://www.cube.tv/studio/info?cube_id={channel}"
    _stream_data_api_url_base = "https://www.cube.tv/studioApi/getStudioSrcBySid?sid={gid}&videoType=1&https=1"

    _channel_info_schema = validate.Schema({
        u"code" : 1,
        u"msg": u"success",
        u"data": {
            u"gid": validate.text,
            u"cube_id": validate.text
        }
    })

    _stream_data_schema = validate.Schema({
        u"code" : 1,
        u"msg": u"success",
        u"data": {
            u"video": u"hls",
            u"video_src": validate.url()
        }
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_api_res(self, user_id):
        try:
            res = self.session.http.get(self._channel_info_api_url_base.format(channel=user_id))
            return res
        except Exception as e:
            raise NoStreamsError(self.url)

    def _get_streams(self):
        user_id = self._url_re.match(self.url).group(2)
        res = self._get_api_res(user_id)
        user_gid = self.session.http.json(res, schema=self._channel_info_schema)['data']['gid']

        try:
            stream_data = self.session.http.get(self._stream_data_api_url_base.format(gid=user_gid))
            hls = self.session.http.json(stream_data, schema=self._stream_data_schema)['data']['video_src']
        except Exception as e:
            raise NoStreamsError(self.url)

        return HLSStream.parse_variant_playlist(self.session, hls)


__plugin__ = CubeTV
