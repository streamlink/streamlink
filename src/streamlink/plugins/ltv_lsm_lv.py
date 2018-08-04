import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream


class LtvLsmLv(Plugin):
    '''
    Support for Latvian live channels streams on ltv.lsm.lv
    '''
    url_re = re.compile(r"https?://ltv.lsm.lv/lv/tieshraide")
    iframe_re = re.compile(r'iframe .*?src="((?:http(s)?:)?//[^"]*?)"')
    stream_re = re.compile(r'source .*?src="((?:http(s)?:)?//[^"]*?)"') 

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        HEADERS = {
           "Referer": self.url,
           "User-Agent": useragents.FIREFOX
        }
        # get URL content
        res = self.session.http.get(self.url, headers=HEADERS)
        # find iframe url
        iframe = self.iframe_re.search(res.text)
        iframe_url = iframe and iframe.group(1)
        if iframe_url:
            self.logger.debug("Found iframe: {}", iframe_url)
            ires = self.session.http.get(iframe_url, headers=HEADERS)
            streams_m = self.stream_re.search(ires.text)
            streams_url = streams_m and streams_m.group(1)
            if streams_url:
                self.logger.debug("Found streams URL: {}", streams_url)
                streams = HLSStream.parse_variant_playlist(self.session, streams_url)
                if not streams:
                    self.logger.debug("Play whole m3u8 file")
                    yield 'live', HLSStream(self.session, video_url)
                else:
                    self.logger.debug("Play single stream (but broadcaster currently set all the listed resolutions point to the same 480p stream)")
                    for s in streams.items():
                        yield s
            else:
                self.logger.error("Could not find the stream URL")
        else:
            self.logger.error("Could not find player iframe")


__plugin__ = LtvLsmLv
