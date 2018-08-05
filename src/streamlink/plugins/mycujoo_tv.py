import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream


class MycujooTv(Plugin):
    '''
    Support for live and archived transmission of the matches and channels on mycujoo.tv
    '''
    url_re = re.compile(r'https?://mycujoo\.tv/video/')
    streams_re = re.compile(r'meta .*?"twitter:player:stream" .*?content="((?:http(s)?:)?//[^"]*?)"') 

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        # get URL content
        res = self.session.http.get(self.url)
        # find stream url
        streams = self.streams_re.search(res.text)
        streams_url = streams and streams.group(1)
        if streams_url:
            self.logger.debug("Found streams URL: {}", streams_url)
            streams = HLSStream.parse_variant_playlist(self.session, streams_url)
            if not streams:
                self.logger.debug("Play whole m3u8 file")
                yield 'live', HLSStream(self.session, video_url)
            else:
                self.logger.debug("Play single resolution stream")
                for s in streams.items():
                    yield s
        else:
            self.logger.error("Could not find the stream URL")


__plugin__ = MycujooTv
