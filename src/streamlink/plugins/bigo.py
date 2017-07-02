import re
import socket
import struct

from streamlink import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.stream import Stream, HLSStream


class BigoStream(Stream):
    """
    Custom streaming protocol for Bigo

    The stream is started by sending the uid and sid as little-endian unsigned longs
    after connecting to the server. The video stream is FLV.
    """

    def __init__(self, session, sid, uid, ip, port):
        super(BigoStream, self).__init__(session)
        try:
            self.sid = int(sid)
            self.uid = int(uid)
        except ValueError:
            raise PluginError("invalid sid or uid parameter for Bigo Stream: {0}/{1}".format(self.sid, self.uid))
        self.ip = ip
        try:
            self.port = int(port)
        except ValueError:
            raise PluginError("invalid port number for Bigo Stream: {0}:{1}".format(self.ip, self.port))
        self.con = None

    def open(self):
        try:
            self.con = socket.create_connection((self.ip, self.port))
            self.con.send(struct.pack("<LL", self.uid, self.sid))
        except IOError:
            raise PluginError("could not connect to Bigo Stream")
        return self

    def read(self, size):
        return self.con.recv(size)

    def close(self):
        if self.con:
            self.con.close()


class Bigo(Plugin):
    _url_re = re.compile(r"^https?://(www\.)?(bigo\.tv|bigoweb\.co/show)/[\w\d]+$")
    _flashvars_re = flashvars = re.compile(
        r'''^\s*(?<!<!--)<param.*value="tmp=(\d+)&channel=(\d+)&srv=(\d+\.\d+\.\d+\.\d+)&port=(\d+)"''',
        re.M)
    _video_re = re.compile(
        r'^\s*(?<!<!--)<source id="videoSrc" src="(http://.*\.m3u8)"',
        re.M)

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        page = http.get(self.url,
                        allow_redirects=True,
                        headers={"User-Agent": useragents.IPHONE_6})
        videomatch = self._video_re.search(page.text)
        if not videomatch:
            return

        videourl = videomatch.group(1)
        yield "live", HLSStream(self.session, videourl)


__plugin__ = Bigo
