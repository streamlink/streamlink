import re

from streamlink import StreamError
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HTTPStream, StreamIOIterWrapper, StreamIOThreadWrapper

_url_re = re.compile(r'http(s)?:\/\/(\w+\.)?(?P<domain>vaughn).live(\/embed\/video)?\/(?P<channel>[^\/&?]+)', re.VERBOSE)


class VaughnStream(HTTPStream):
    def open(self):
        method = self.args.get("method", "GET")
        timeout = self.session.options.get("http-timeout")
        res = self.session.http.request(method=method,
                                        stream=True,
                                        exception=StreamError,
                                        timeout=timeout,
                                        **self.args)

        def fix_stream():
            """
            Replace the first 3 bytes of the stream with b'FLV'
            :return: stream iterator
            """
            content_iter = res.iter_content(8192)
            data = next(content_iter)
            yield b'FLV' + data[3:]
            for chunk in content_iter:
                yield chunk

        fd = StreamIOIterWrapper(fix_stream())
        if self.buffered:
            fd = StreamIOThreadWrapper(self.session, fd, timeout=timeout)

        return fd


class VaughnLive(Plugin):

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        self.session.http.headers = {
            "Origin": "https://vaughnlive.tv",
            "Referer": self.url,
            "User-Agent": useragents.FIREFOX
        }
        m = _url_re.match(self.url)
        if m:
                        
            res = self.session.http.get(self.url)
            res = re.findall(r'mp4Servers\s*=\s*\[\s*"([^"]+).*?mp4StreamName\s*=\s*"([^"]+).*?mp4StreamUrl\s*=\s*"([^"]+)', res.text, re.DOTALL)[0]
            self.stream_url = res[2].replace('{mp4Server}', res[0]).replace('{streamName}', res[1])
            self.logger.info("Stream powered by VaughnSoft - remember to support them.")
            
            stream = VaughnStream(self.session,
                                  self.stream_url)
            
            stream_url = stream.to_url()
            res = self.session.http.head(stream_url, raise_for_status=False)
            yield "live", stream


__plugin__ = VaughnLive
