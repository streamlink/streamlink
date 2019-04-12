import re
 
from streamlink import StreamError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, useragents
from streamlink.stream import HTTPStream, StreamIOIterWrapper, StreamIOThreadWrapper
 
#_url_re = re.compile(r"""
#   http(s)?://(\w+\.)?
#   (?P<domain>breakers|instagib|vapers|pearltime).tv
#   (/embed/video)?
#   /(?P<channel>[^/&?]+)
#""", re.VERBOSE)

_url_re = re.compile(r"""
   http(s)?://(\w+\.)?
   (?P<domain>vaughn).live
   (/embed/video)?
   /(?P<channel>[^/&?]+)
""", re.VERBOSE)

_schema = validate.Schema(
    validate.text
)

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
    domain_map = {"vaughn": "live", "breakers": "btv", "instagib": "instagib", "vapers": "vtv", "pearltime": "pt"}
    stream_url = "https://mp4v.vaughnsoft.net"
 
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)
 
    def _get_streams(self):
        self.session.http.headers = {
            "Origin": "https://vaughn.live",
            "Referer": self.url,
            "User-Agent": useragents.FIREFOX,
        }
        m = _url_re.match(self.url)
        if m:
            stream_name = "{0}_{1}".format(self.domain_map[(m.group("domain").lower())],
                                           m.group("channel"))

            res = http.get(self.url, schema=_schema)
            if not res: return

            pattern = r"""var mp4StreamUrl = \"(.*?)&secure=(.*?)&expires=(.*?)&ip=(.*?)\""""
            r = re.search(pattern, res)
            if not r: return

            stream_link = '%s/play/%s.flv?&secure=%s&expires=%s&ip=%s' % (self.stream_url, stream_name, r.group(2), r.group(3), r.group(4))

            self.logger.info("Stream powered by VaughnSoft - remember to support them.")
            stream = VaughnStream(self.session,
                                  stream_link,
                                  params=dict(app="live",
                                              stream=stream_name,
                                              port=2935))
            stream_url = stream.to_url()
            res = self.session.http.head(stream_url, raise_for_status=False)
            print(res.status_code)
            yield "live", stream
 
 
__plugin__ = VaughnLive
