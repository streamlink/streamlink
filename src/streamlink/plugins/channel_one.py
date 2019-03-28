import re
from streamlink.plugin import Plugin
from streamlink.stream import DASHStream


class Channel_One(Plugin):
    url_re = re.compile(r'https?://www.1tv.ru/live/.*')

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        mrl = 'https://edge1.1internet.tv/dash-live11/streams/1tv/1tvdash.mpd'
        return DASHStream.parse_manifest(self.session, mrl)

__plugin__ = Channel_One
