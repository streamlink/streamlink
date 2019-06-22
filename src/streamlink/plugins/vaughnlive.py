import re
import logging
from streamlink import StreamError
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HTTPStream, StreamIOIterWrapper, StreamIOThreadWrapper
import esprima
import sys
from random import shuffle
if sys.version_info[0] > 2:
    from html.parser import HTMLParser
else:
    from HTMLParser import HTMLParser

log = logging.getLogger(__name__)

_url_re = re.compile("""
    https://(
        (vaughn.live)|
        ((breakers|instagib|vapers).tv)
        )/.*
    """
    , re.VERBOSE)

class HTML_Parser(HTMLParser):
    js = False
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            attrs = dict(attrs)
            if 'type' in attrs and attrs['type'] == 'text/javascript':
                self.js = True

    def handle_data(self, data):
        if self.js and data.find('function serverShuffle'):
            self.data = data


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

class HTML_Parser(HTMLParser):
    js = False
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            attrs = dict(attrs)
            if 'type' in attrs and attrs['type'] == 'text/javascript':
                self.js = True

    def handle_data(self, data):
        if self.js and data.find('serverShuffle') > 0:
            self.data = data

def get_js(html):
    parser = HTML_Parser()
    parser.feed(html)
    try:
        js = parser.data
    except:
        return False
    parsed = esprima.parseScript(js, { "tolerant": True })
    return parsed.body

class VaughnLive(Plugin):

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        self.session.http.headers = {
            "Referer": self.url,
            "User-Agent": useragents.FIREFOX
        }
        html = self.session.http.get(self.url).text
        body = get_js(html)
        if body:
            mp4ServerNode = None
            mp4StreamName = None
            mp4StreamUrl = None
            for node in body:
                if node.declarations:
                    if not mp4ServerNode and \
                        node.declarations[0].id.name ==  "mp4Servers":
                        mp4Servers = node.declarations[0].init.elements
                        shuffle(mp4Servers)
                        mp4ServerNode = mp4Servers[0].value
                
                    if not mp4StreamName and \
                        node.declarations[0].id.name ==  "mp4StreamName":
                        mp4StreamName = node.declarations[0].init.value

                    if not mp4StreamUrl and \
                        node.declarations[0].id.name ==  "mp4StreamUrl":
                        mp4StreamUrl = node.declarations[0].init.value

                if mp4ServerNode and mp4StreamName and mp4StreamUrl:
                    break

            stream_url = mp4StreamUrl.format(
                mp4Server=mp4ServerNode, streamName=mp4StreamName)
            log.debug("Stream URL: {0}".format(stream_url))
            stream = VaughnStream(self.session, stream_url)
            yield "live", stream

__plugin__ = VaughnLive
