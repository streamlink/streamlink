"""
$description Pakistani live TV channels and video on-demand service. OTT service from mjunoon.
$url mjunoon.tv
$type live, vod
$metadata author
$metadata category
$metadata title
$region Pakistan
"""

import binascii
import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.crypto import AES, unpad
from streamlink.utils.parse import parse_json


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?mjunoon\.tv/(?:watch/)?([\w-]+)"),
)
class Mjunoon(Plugin):
    login_url = "https://cdn2.mjunoon.tv:9191/v2/auth/login"
    stream_url = "https://cdn2.mjunoon.tv:9191/v2/streaming-url"

    is_live_channel_re = re.compile(r'"isLiveBroadcast":\s*"(true|undefined)"')

    main_chunk_js_url_re = re.compile(
        r'<script src="(/static/js/main\.\w+\.chunk\.js)"></script>',
    )

    js_credentials_re = re.compile(
        r'data:{email:"(?P<email>.*?)",password:"(?P<password>.*?)"}',
    )

    js_cipher_data_re = re.compile(
        r'createDecipheriv\("(?P<algorithm>.*?)","(?P<key>.*?)","(?P<iv>.*?)"\)',
    )

    token_schema = validate.Schema({
        "token": str,
        "token_type": str,
        "expires_in": int,
    })

    encrypted_data_schema = validate.Schema(
        {
            "eData": str,
        },
        validate.get("eData"),
    )

    stream_schema = validate.Schema(
        {
            "data": {
                "live_stream_url": validate.url(),
                "channel_name": str,
                "meta_title": validate.any(None, str),
                "genres": validate.all(
                    validate.transform(lambda x: x.split(",")[0]),
                    str,
                ),
            },
        },
        validate.get("data"),
    )

    encryption_algorithm = {
        "aes-256-cbc": AES.MODE_CBC,
    }

    def get_data(self):
        js_data = {}
        res = self.session.http.get(self.url)

        m = self.is_live_channel_re.search(res.text)
        if not m:
            return

        if m.group(1) == "true":
            js_data["type"] = "channel"
        else:
            js_data["type"] = "episode"

        m = self.main_chunk_js_url_re.search(res.text)
        if not m:
            log.error("Failed to get main chunk JS URL")
            return

        res = self.session.http.get(urljoin(self.url, m.group(1)))

        m = self.js_credentials_re.search(res.text)
        if not m:
            log.error("Failed to get credentials")
            return

        js_data["credentials"] = m.groupdict()

        m = self.js_cipher_data_re.search(res.text)
        if not m:
            log.error("Failed to get cipher data")
            return

        js_data["cipher_data"] = m.groupdict()

        return js_data

    def decrypt_data(self, cipher_data, encrypted_data):
        cipher = AES.new(
            bytes(cipher_data["key"], "utf-8"),
            self.encryption_algorithm[cipher_data["algorithm"]],
            bytes(cipher_data["iv"], "utf-8"),
        )

        return unpad(cipher.decrypt(binascii.unhexlify(encrypted_data)), 16, "pkcs7")

    def get_stream(self, slug, js_data):
        token_data = {
            "token": self.cache.get("token"),
            "token_type": self.cache.get("token_type"),
        }

        if token_data["token"] and token_data["token_type"]:
            log.debug("Using cached token")
        else:
            log.debug("Getting new token")

            res = self.session.http.post(
                self.login_url,
                json=js_data["credentials"],
            )
            token_data = self.session.http.json(res, schema=self.token_schema)
            log.debug(f"Token={token_data['token']}")

            self.cache.set("token", token_data["token"], expires=token_data["expires_in"])
            self.cache.set("token_type", token_data["token_type"], expires=token_data["expires_in"])

        headers = {"Authorization": f"{token_data['token_type']} {token_data['token']}"}
        data = {
            "slug": slug,
            "type": js_data["type"],
        }
        res = self.session.http.post(
            self.stream_url,
            headers=headers,
            json=data,
        )
        encrypted_data = self.session.http.json(
            res,
            schema=self.encrypted_data_schema,
        )

        stream_data = parse_json(
            self.decrypt_data(js_data["cipher_data"], encrypted_data),
            schema=self.stream_schema,
        )

        self.author = stream_data["channel_name"]
        self.category = stream_data["genres"]
        self.title = stream_data["meta_title"]

        return stream_data["live_stream_url"]

    def _get_streams(self):
        slug = self.match.group(1)
        log.debug(f"Slug={slug}")

        js_data = self.get_data()
        if not js_data:
            return

        log.debug(f"JS data={js_data}")

        hls_url = self.get_stream(slug, js_data)
        log.debug(f"HLS URL={hls_url}")

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = Mjunoon
