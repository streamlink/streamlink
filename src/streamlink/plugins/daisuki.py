import base64
import json
import random
import re
import tempfile
import time
import warnings

from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util import number

from streamlink.compat import urljoin, urlparse
from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin, PluginOptions
from streamlink.plugin.api import http, validate
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HLSStream
from streamlink.stream.ffmpegmux import MuxedStream, FFMPEGMuxer
from streamlink.stream.file import FileStream

HDCORE_VERSION = "3.2.0"

_url_re = re.compile(r"https?://www.daisuki.net/[^/]+/[^/]+/anime/watch\..+")
_flashvars_re = re.compile(r"var\s+flashvars\s*=\s*\{([^}]*?)};", re.DOTALL)
_flashvar_re = re.compile(r"""(['"])(.*?)\1\s*:\s*(['"])(.*?)\3""")
_clientlibs_re = re.compile(r"""<script.*?src=(['"])(.*?/clientlibs_anime_watch.*?\.js)\1""")

_schema = validate.Schema(
    validate.union({
        "flashvars": validate.all(
            validate.transform(_flashvars_re.search),
            validate.get(1),
            validate.transform(_flashvar_re.findall),
            validate.map(lambda v: (v[1], v[3])),
            validate.transform(dict),
            {
                "s": validate.text,
                "country": validate.text,
                "init": validate.text,
                validate.optional("ss_id"): validate.text,
                validate.optional("mv_id"): validate.text,
                validate.optional("device_cd"): validate.text,
                validate.optional("ss1_prm"): validate.text,
                validate.optional("ss2_prm"): validate.text,
                validate.optional("ss3_prm"): validate.text
            }
        ),
        "clientlibs": validate.all(
            validate.transform(_clientlibs_re.search),
            validate.get(2),
            validate.text
        )
    })
)

_language_schema = validate.Schema(
    validate.xml_findtext("./country_code")
)

_xml_to_srt_schema = validate.Schema(
    validate.xml_findall(".//body/div"),
    [
        validate.union([validate.all(
                validate.getattr("attrib"),
                validate.get("{http://www.w3.org/XML/1998/namespace}lang")
            ),
            validate.all(
                validate.xml_findall("./p"),
                validate.transform(lambda x: list(enumerate(x, 1))),
                [
                    validate.all(
                        validate.union({
                            "i": validate.get(0),
                            "begin": validate.all(
                                validate.get(1),
                                validate.getattr("attrib"),
                                validate.get("begin"),
                                validate.transform(lambda s: s.replace(".", ","))
                            ),
                            "end": validate.all(
                                validate.get(1),
                                validate.getattr("attrib"),
                                validate.get("end"),
                                validate.transform(lambda s: s.replace(".", ","))
                            ),
                            "text": validate.all(
                                validate.get(1),
                                validate.transform(lambda x: '\n'.join([s.strip() for s in x.itertext()]))
                            )
                        }),
                        validate.transform(
                            lambda d: "{i}\n{begin} --> {end}\n{text}\n".format(**d)
                        )
                    )
                ],
                validate.transform(lambda s: '\n'.join(s))
            )
        ])
    ]
)

_init_schema = validate.Schema(
    {
        "rtn": validate.all(
            validate.text
        )
    },
    validate.get("rtn")
)


def aes_encrypt(key, plaintext):
    plaintext = plaintext.encode("utf-8")
    aes = AES.new(key, AES.MODE_CBC, number.long_to_bytes(0, AES.block_size))
    if len(plaintext) % AES.block_size != 0:
        plaintext += b"\0" * (AES.block_size - len(plaintext) % AES.block_size)
    return base64.b64encode(aes.encrypt(plaintext))


def aes_decrypt(key, ciphertext):
    aes = AES.new(key, AES.MODE_CBC, number.long_to_bytes(0, AES.block_size))
    plaintext = aes.decrypt(base64.b64decode(ciphertext))
    plaintext = plaintext.strip(b"\0")
    return plaintext.decode("utf-8")


def rsa_encrypt(key, plaintext):
    pubkey = RSA.importKey(key)
    cipher = PKCS1_v1_5.new(pubkey)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return base64.b64encode(cipher.encrypt(plaintext))


def get_public_key(cache, url):
    headers = {}

    cached = cache.get("clientlibs")
    if cached and cached["url"] == url:
        headers["If-Modified-Since"] = cached["modified"]

    script = http.get(url, headers=headers)
    if cached and script.status_code == 304:
        return cached["pubkey"]

    modified = script.headers.get("Last-Modified", "")

    match = re.search(r"""\"(-----BEGIN PUBLIC KEY-----[^"]*?-----END PUBLIC KEY-----)\"""", script.text, re.DOTALL)
    if match is None:
        return None

    pubkey = match.group(1).replace("\\n", "\n")

    cache.set("clientlibs", dict(url=url, modified=modified, pubkey=pubkey))

    return pubkey


class Daisuki(Plugin):
    options = PluginOptions({
        "mux_subtitles": False
    })

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        page = http.get(self.url, schema=_schema)
        if not page:
            return

        pubkey_pem = get_public_key(self.cache, urljoin(self.url, page["clientlibs"]))
        if not pubkey_pem:
            raise PluginError("Unable to get public key")

        flashvars = page["flashvars"]

        params = {
            "cashPath": int(time.time() * 1000)
        }
        res = http.get(urljoin(self.url, flashvars["country"]), params=params)
        if not res:
            return
        language = http.xml(res, schema=_language_schema)

        api_params = {}
        for key in ("ss_id", "mv_id", "device_cd", "ss1_prm", "ss2_prm", "ss3_prm"):
            if flashvars.get(key, ""):
                api_params[key] = flashvars[key]

        aeskey = number.long_to_bytes(random.getrandbits(8 * 32), 32)

        params = {
            "s": flashvars["s"],
            "c": language,
            "e": self.url,
            "d": aes_encrypt(aeskey, json.dumps(api_params)),
            "a": rsa_encrypt(pubkey_pem, aeskey)
        }
        res = http.get(urljoin(self.url, flashvars["init"]), params=params)
        if not res:
            return
        rtn = http.json(res, schema=_init_schema)
        if not rtn:
            return

        init_data = parse_json(aes_decrypt(aeskey, rtn))

        parsed = urlparse(init_data["play_url"])
        if parsed.scheme != "https" or not parsed.path.startswith("/i/") or not parsed.path.endswith("/master.m3u8"):
            return
        hlsstream_url = init_data["play_url"]

        streams = HLSStream.parse_variant_playlist(self.session, hlsstream_url)

        if "caption_url" in init_data:
            if self.get_option("mux_subtitles") and FFMPEGMuxer.is_usable(self.session):
                res = http.get(init_data["caption_url"])
                srt = http.xml(res, ignore_ns=True, schema=_xml_to_srt_schema)
                subfiles = []
                metadata = {}
                for i, lang, srt in ((i, s[0], s[1]) for i, s in enumerate(srt)):
                    subfile = tempfile.TemporaryFile()
                    subfile.write(srt.encode("utf8"))
                    subfile.seek(0)
                    subfiles.append(FileStream(self.session, fileobj=subfile))
                    metadata["s:s:{0}".format(i)] = ["language={0}".format(lang)]

                for n, s in streams.items():
                    yield n, MuxedStream(self.session, s, *subfiles,
                                         maps=list(range(0, len(metadata)+1)),
                                         metadata=metadata)
                return
            else:
                self.logger.info("Subtitles: {0}".format(init_data["caption_url"]))

        for s in streams.items():
            yield s


__plugin__ = Daisuki
