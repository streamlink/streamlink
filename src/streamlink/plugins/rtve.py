import base64
import re

from Crypto.Cipher import Blowfish
from streamlink.compat import bytes, is_py3
from streamlink.plugin import Plugin, PluginOptions
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.utils import parse_xml


class ZTNRClient(object):
    base_url = "http://ztnr.rtve.es/ztnr/res/"
    block_size = 16

    def __init__(self, key):
        self.cipher = Blowfish.new(key, Blowfish.MODE_ECB)

    @classmethod
    def pad(cls, data):
        n = cls.block_size - len(data) % cls.block_size
        return data + bytes(chr(cls.block_size - len(data) % cls.block_size), "utf8") * n

    @staticmethod
    def unpad(data):
        if is_py3:
            return data[0:-data[-1]]
        else:
            return data[0:-ord(data[-1])]

    def encrypt(self, data):
        return base64.b64encode(self.cipher.encrypt(self.pad(bytes(data, "utf-8"))), altchars=b"-_").decode("ascii")

    def decrypt(self, data):
        return self.unpad(self.cipher.decrypt(base64.b64decode(data, altchars=b"-_")))

    def request(self, data, *args, **kwargs):
        res = http.get(self.base_url + self.encrypt(data), *args, **kwargs)
        return self.decrypt(res.content)

    def get_cdn_list(self, vid, manager="apedemak", vtype="video", lang="es", schema=None):
        data = self.request("{id}_{manager}_{type}_{lang}".format(id=vid, manager=manager, type=vtype, lang=lang))
        if schema:
            return schema.validate(data)
        else:
            return data


class Rtve(Plugin):
    secret_key = base64.b64decode("eWVMJmRhRDM=")
    content_id_re = re.compile(r'data-id\s*=\s*"(\d+)"')
    url_re = re.compile(r"""
        https?://(?:www\.)?rtve\.es/(?:directo|noticias|television|deportes|alacarta|drmn)/.*?/?
    """, re.VERBOSE)
    cdn_schema = validate.Schema(
        validate.transform(parse_xml),
        validate.xml_findtext(".//url")
    )
    subtitles_api = "http://www.rtve.es/api/videos/{id}/subtitulos.json"
    subtitles_schema = validate.Schema({
        "page": {
            "items": [{
                    "src": validate.url(),
                    "lang": validate.text
                }]
            }
        },
        validate.get("page"),
        validate.get("items"))
    options = PluginOptions({
        "mux_subtitles": False
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def __init__(self, url):
        Plugin.__init__(self, url)
        self.zclient = ZTNRClient(self.secret_key)
        http.headers = {"User-Agent": useragents.SAFARI_8}

    def _get_content_id(self):
        res = http.get(self.url)
        m = self.content_id_re.search(res.text)
        return m and int(m.group(1))

    def _get_subtitles(self, content_id):
        res = http.get(self.subtitles_api.format(id=content_id))
        return http.json(res, schema=self.subtitles_schema)

    def _get_streams(self):
        content_id = self._get_content_id()
        if content_id:
            self.logger.debug("Found content with id: {0}", content_id)
            hls_url = self.zclient.get_cdn_list(content_id, schema=self.cdn_schema)
            self.logger.debug("Got stream URL: {0}", hls_url)
            streams = HLSStream.parse_variant_playlist(self.session, hls_url)

            subtitles = None
            if self.get_option("mux_subtitles"):
                subtitles = self._get_subtitles(content_id)
            if subtitles:
                substreams = {}
                for i, subtitle in enumerate(subtitles):
                    substreams[subtitle["lang"]] = HTTPStream(self.session, subtitle["src"])

                for q, s in streams.items():
                    yield q, MuxedStream(self.session, s, subtitles=substreams)
            else:
                for s in streams.items():
                    yield s


__plugin__ = Rtve
