import base64
import logging
import re
from urllib.parse import urlparse

from Crypto.Cipher import Blowfish

from streamlink.plugin import Plugin, PluginArgument, PluginArguments, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


class ZTNRClient:
    base_url = "https://ztnr.rtve.es/ztnr/res/"
    block_size = 16

    def __init__(self, key, session):
        self.cipher = Blowfish.new(key, Blowfish.MODE_ECB)
        self.session = session

    @classmethod
    def pad(cls, data):
        n = cls.block_size - len(data) % cls.block_size
        return data + bytes(chr(cls.block_size - len(data) % cls.block_size), "utf8") * n

    @staticmethod
    def unpad(data):
        return data[0:-data[-1]]

    def encrypt(self, data):
        return base64.b64encode(self.cipher.encrypt(self.pad(bytes(data, "utf-8"))), altchars=b"-_").decode("ascii")

    def decrypt(self, data):
        return self.unpad(self.cipher.decrypt(base64.b64decode(data, altchars=b"-_")))

    def request(self, data, *args, **kwargs):
        res = self.session.http.get(self.base_url + self.encrypt(data), *args, **kwargs)
        return self.decrypt(res.content)

    def get_cdn_list(self, vid, manager="apedemak", vtype="video", lang="es", schema=None):
        data = self.request("{id}_{manager}_{type}_{lang}".format(id=vid, manager=manager, type=vtype, lang=lang))
        if schema:
            return schema.validate(data)
        else:
            return data


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?rtve\.es/play/videos/.+"
))
class Rtve(Plugin):
    _re_idAsset = re.compile(r"\"idAsset\":\"(\d+)\"")
    secret_key = base64.b64decode("eWVMJmRhRDM=")
    cdn_schema = validate.Schema(
        validate.parse_xml(invalid_char_entities=True),
        validate.xml_findall(".//preset"),
        [
            validate.union({
                "quality": validate.all(validate.getattr("attrib"),
                                        validate.get("type")),
                "urls": validate.all(
                    validate.xml_findall(".//url"),
                    [validate.getattr("text")]
                )
            })
        ]
    )
    subtitles_api = "https://www.rtve.es/api/videos/{id}/subtitulos.json"
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
    video_api = "https://www.rtve.es/api/videos/{id}.json"
    video_schema = validate.Schema({
        "page": {
            "items": [{
                "qualities": [{
                    "preset": validate.text,
                    "height": int
                }]
            }]
        }
    },
        validate.get("page"),
        validate.get("items"),
        validate.get(0))

    arguments = PluginArguments(
        PluginArgument("mux-subtitles", is_global=True)
    )

    def __init__(self, url):
        super().__init__(url)
        self.zclient = ZTNRClient(self.secret_key, self.session)

    def _get_subtitles(self, content_id):
        res = self.session.http.get(self.subtitles_api.format(id=content_id))
        return self.session.http.json(res, schema=self.subtitles_schema)

    def _get_quality_map(self, content_id):
        res = self.session.http.get(self.video_api.format(id=content_id))
        data = self.session.http.json(res, schema=self.video_schema)
        qmap = {}
        for item in data["qualities"]:
            qname = {"MED": "Media", "HIGH": "Alta", "ORIGINAL": "Original"}.get(item["preset"], item["preset"])
            qmap[qname] = f"{item['height']}p"
        return qmap

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self._re_idAsset.search(res.text)
        if m:
            content_id = m.group(1)
            log.debug(f"Found content with id: {content_id}")
            stream_data = self.zclient.get_cdn_list(content_id, schema=self.cdn_schema)
            quality_map = None

            streams = []
            for stream in stream_data:
                # only use one stream
                _one_m3u8 = False
                _one_mp4 = False
                for url in stream["urls"]:
                    p_url = urlparse(url)
                    if p_url.path.endswith(".m3u8"):
                        if _one_m3u8:
                            continue
                        try:
                            streams.extend(HLSStream.parse_variant_playlist(self.session, url).items())
                            _one_m3u8 = True
                        except OSError as err:
                            log.error(str(err))
                    elif p_url.path.endswith(".mp4"):
                        if _one_mp4:
                            continue
                        if quality_map is None:  # only make the request when it is necessary
                            quality_map = self._get_quality_map(content_id)
                        # rename the HTTP sources to match the HLS sources
                        quality = quality_map.get(stream["quality"], stream["quality"])
                        streams.append((quality, HTTPStream(self.session, url)))
                        _one_mp4 = True

            subtitles = None
            if self.get_option("mux_subtitles"):
                subtitles = self._get_subtitles(content_id)
            if subtitles:
                substreams = {}
                for i, subtitle in enumerate(subtitles):
                    substreams[subtitle["lang"]] = HTTPStream(self.session, subtitle["src"])

                for q, s in streams:
                    yield q, MuxedStream(self.session, s, subtitles=substreams)
            else:
                for s in streams:
                    yield s


__plugin__ = Rtve
