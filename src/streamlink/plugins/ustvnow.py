"""
$description US live TV channels. OTT service from USTVnow.
$url ustvnow.com
$type live
$account Required, additional subscription required by some streams
"""

import base64
import json
import logging
import re
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad, unpad

from streamlink.plugin import Plugin, PluginError, pluginargument, pluginmatcher
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?ustvnow\.com/live/(?P<scode>\w+)/-(?P<id>\d+)"
))
@pluginargument(
    "username",
    required=True,
    requires=["password"],
    metavar="USERNAME",
    help="Your USTV Now account username",
)
@pluginargument(
    "password",
    required=True,
    sensitive=True,
    metavar="PASSWORD",
    help="Your USTV Now account password",
)
class USTVNow(Plugin):
    _main_js_re = re.compile(r"""src=['"](main\..*\.js)['"]""")
    _enc_key_re = re.compile(r'(?P<key>AES_(?:Key|IV))\s*:\s*"(?P<value>[^"]+)"')

    TENANT_CODE = "ustvnow"
    _api_url = "https://teleupapi.revlet.net/service/api/v1/"
    _token_url = _api_url + "get/token"
    _signin_url = "https://www.ustvnow.com/signin"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._encryption_config = {}
        self._token = None

    @classmethod
    def encrypt_data(cls, data, key, iv):
        rkey = "".join(reversed(key)).encode('utf8')
        riv = "".join(reversed(iv)).encode('utf8')

        fkey = SHA256.new(rkey).hexdigest()[:32].encode("utf8")

        cipher = AES.new(fkey, AES.MODE_CBC, riv)
        encrypted = cipher.encrypt(pad(data, 16, 'pkcs7'))
        return base64.b64encode(encrypted)

    @classmethod
    def decrypt_data(cls, data, key, iv):
        rkey = "".join(reversed(key)).encode('utf8')
        riv = "".join(reversed(iv)).encode('utf8')

        fkey = SHA256.new(rkey).hexdigest()[:32].encode("utf8")

        cipher = AES.new(fkey, AES.MODE_CBC, riv)
        decrypted = cipher.decrypt(base64.b64decode(data))
        if decrypted:
            return unpad(decrypted, 16, 'pkcs7')
        else:
            return decrypted

    def _get_encryption_config(self, url):
        # find the path to the main.js
        # load the main.js and extract the config
        if not self._encryption_config:
            res = self.session.http.get(url)
            m = self._main_js_re.search(res.text)
            main_js_path = m and m.group(1)
            if main_js_path:
                res = self.session.http.get(urljoin(url, main_js_path))
                self._encryption_config = dict(self._enc_key_re.findall(res.text))

        return self._encryption_config.get("AES_Key"), self._encryption_config.get("AES_IV")

    @property
    def box_id(self):
        if not self.cache.get("box_id"):
            self.cache.set("box_id", str(uuid4()))
        return self.cache.get("box_id")

    def get_token(self):
        """
        Get the token for USTVNow
        :return: a valid token
        """

        if not self._token:
            log.debug("Getting new session token")
            res = self.session.http.get(self._token_url, params={
                "tenant_code": self.TENANT_CODE,
                "box_id": self.box_id,
                "product": self.TENANT_CODE,
                "device_id": 5,
                "display_lang_code": "ENG",
                "device_sub_type": "",
                "timezone": "UTC"
            })

            data = res.json()
            if data['status']:
                self._token = data['response']['sessionId']
                log.debug("New token: {}".format(self._token))
            else:
                log.error("Token acquisition failed: {details} ({detail})".format(**data['error']))
                raise PluginError("could not obtain token")

        return self._token

    def api_request(self, path, data, metadata=None):
        key, iv = self._get_encryption_config(self._signin_url)
        post_data = {
            "data": self.encrypt_data(json.dumps(data).encode('utf8'), key, iv).decode("utf8"),
            "metadata": self.encrypt_data(json.dumps(metadata).encode('utf8'), key, iv).decode("utf8")
        }
        headers = {"box-id": self.box_id,
                   "session-id": self.get_token(),
                   "tenant-code": self.TENANT_CODE,
                   "content-type": "application/json"}
        res = self.session.http.post(self._api_url + path, data=json.dumps(post_data), headers=headers).json()
        data = {k: v and json.loads(self.decrypt_data(v, key, iv)) for k, v in res.items()}
        return data

    def login(self, username, password):
        log.debug("Trying to login...")
        resp = self.api_request(
            "send",
            {
                "login_id": username,
                "login_key": password,
                "login_mode": "1",
                "manufacturer": "123"
            },
            {"request": "signin"}
        )

        return resp['data']['status']

    def _get_streams(self):
        """
        Finds the streams from ustvnow.com.
        """
        if self.login(self.get_option("username"), self.get_option("password")):
            path = urlparse(self.url).path.strip("/")
            resp = self.api_request("send", {"path": path}, {"request": "page/stream"})
            if resp['data']['status']:
                for stream in resp['data']['response']['streams']:
                    if stream['keys']['licenseKey']:
                        log.warning("Stream possibly protected by DRM")
                    yield from HLSStream.parse_variant_playlist(self.session, stream['url']).items()
            else:
                log.error("Could not find any streams: {code}: {message}".format(**resp['data']['error']))
        else:
            log.error("Failed to login, check username and password")


__plugin__ = USTVNow
