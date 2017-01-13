import base64
import re

from Crypto.Cipher import Blowfish
from streamlink.compat import bytes, is_py3
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_xml


class ZTNRClient(object):
    base_url = "http://ztnr.rtve.es/ztnr/res/"
    block_size = 16

    def __init__(self, key):
        self.cipher = Blowfish.new(key, Blowfish.MODE_ECB)

    def pad(self, data):
        n = self.block_size - len(data) % self.block_size
        return data + bytes(chr(self.block_size - len(data) % self.block_size), "utf8") * n

    def unpad(self, data):
        if is_py3:
            return data[0:-data[-1]]
        else:
            return data[0:-ord(data[-1])]

    def encrypt(self, data):
        return base64.b64encode(self.cipher.encrypt(self.pad(bytes(data, "utf-8"))), altchars=b"-_").decode("ascii")

    def decrypt(self, data):
        return self.unpad(self.cipher.decrypt(base64.b64decode(data, altchars=b"-_")))

    def request(self, data, *args, **kwargs):
        res = http.get(self.base_url+self.encrypt(data), *args, **kwargs)
        return self.decrypt(res.content)

    def get_cdn_list(self, vid, manager="apedemak", vtype="video", lang="es", schema=None):
        data = self.request("{id}_{manager}_{type}_{lang}".format(id=vid, manager=manager, type=vtype, lang=lang))
        if schema:
            return schema.validate(data)
        else:
            return data


class Rtve(Plugin):
    secret_key = base64.b64decode("eWVMJmRhRDM=")
    channel_id_re = re.compile(r'<span.*?id="iniIDA">(\d+)</span>')
    url_re = re.compile(r"""
        https?://(?:www\.)?rtve\.es/(?:noticias|television|deportes)/.*?/?
    """, re.VERBOSE)
    cdn_schema = validate.Schema(
        validate.transform(parse_xml),
        validate.xml_findtext(".//url")
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def __init__(self, url):
        Plugin.__init__(self, url)
        self.zclient = ZTNRClient(self.secret_key)
        http.headers = {"User-Agent": useragents.SAFARI_8}

    def _get_channel_id(self):
        res = http.get(self.url)
        m = self.channel_id_re.search(res.text)
        return m and int(m.group(1))

    def _get_streams(self):
        channel_id = self._get_channel_id()

        if channel_id:
            self.logger.debug("Found channel with id: {0}", channel_id)
            hls_url = self.zclient.get_cdn_list(channel_id, schema=self.cdn_schema)
            self.logger.debug("Got stream URL: {0}", hls_url)
            return HLSStream.parse_variant_playlist(self.session, hls_url)

        return


__plugin__ = Rtve
