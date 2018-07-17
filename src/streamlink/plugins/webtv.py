import json
import re
import base64

import binascii

from Crypto.Cipher import AES

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json, update_scheme
from streamlink.utils.crypto import unpad_pkcs5


class WebTV(Plugin):
    _url_re = re.compile(r"http(?:s)?://(\w+)\.web.tv/?")
    _sources_re = re.compile(r'"sources": (\[.*?\]),', re.DOTALL)
    _sources_schema = validate.Schema([
        {
            u"src": validate.any(
                validate.contains("m3u8"),
                validate.all(
                    validate.text,
                    validate.transform(lambda x: WebTV.decrypt_stream_url(x)),
                    validate.contains("m3u8")
                )
            ),
            u"type": validate.text,
            u"label": validate.text
        }
    ])

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @staticmethod
    def decrypt_stream_url(encoded_url):
        data = base64.b64decode(encoded_url)
        cipher_text = binascii.unhexlify(data[96:])

        decryptor = AES.new(binascii.unhexlify(data[32:96]),
                            AES.MODE_CBC,
                            binascii.unhexlify(data[:32]))

        return unpad_pkcs5(decryptor.decrypt(cipher_text)).decode("utf8")

    def _get_streams(self):
        """
        Find the streams for web.tv
        :return:
        """
        headers = {}
        res = self.session.http.get(self.url, headers=headers)
        headers["Referer"] = self.url

        sources = self._sources_re.findall(res.text)
        if len(sources):
            sdata = parse_json(sources[0], schema=self._sources_schema)
            for source in sdata:
                self.logger.debug("Found stream of type: {}", source[u'type'])
                if source[u'type'] == u"application/vnd.apple.mpegurl":
                    url = update_scheme(self.url, source[u"src"])

                    try:
                        # try to parse the stream as a variant playlist
                        variant = HLSStream.parse_variant_playlist(self.session, url, headers=headers)
                        if variant:
                            for q, s in variant.items():
                                yield q, s
                        else:
                            # and if that fails, try it as a plain HLS stream
                            yield 'live', HLSStream(self.session, url, headers=headers)
                    except IOError:
                        self.logger.warning("Could not open the stream, perhaps the channel is offline")


__plugin__ = WebTV
