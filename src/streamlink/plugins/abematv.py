import hashlib
import hmac
import logging
import re
import struct
import time
import uuid
from base64 import urlsafe_b64encode
from binascii import unhexlify

from Crypto.Cipher import AES
from requests import Response
from requests.adapters import BaseAdapter

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.utils.url import update_qsd

log = logging.getLogger(__name__)


class AbemaTVLicenseAdapter(BaseAdapter):
    '''
    Handling abematv-license:// protocol to get real video key_data.
    '''

    STRTABLE = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    HKEY = b"3AF0298C219469522A313570E8583005A642E73EDD58E3EA2FB7339D3DF1597E"

    _MEDIATOKEN_API = "https://api.abema.io/v1/media/token"

    _LICENSE_API = "https://license.abema.io/abematv-hls"

    _MEDIATOKEN_SCHEMA = validate.Schema({"token": validate.text})

    _LICENSE_SCHEMA = validate.Schema({"k": validate.text,
                                       "cid": validate.text})

    def __init__(self, session, deviceid, usertoken):
        self._session = session
        self.deviceid = deviceid
        self.usertoken = usertoken
        super().__init__()

    def _get_videokey_from_ticket(self, ticket):
        params = {
            "osName": "android",
            "osVersion": "6.0.1",
            "osLang": "ja_JP",
            "osTimezone": "Asia/Tokyo",
            "appId": "tv.abema",
            "appVersion": "3.27.1"
        }
        auth_header = {"Authorization": "Bearer " + self.usertoken}
        res = self._session.http.get(self._MEDIATOKEN_API, params=params,
                                     headers=auth_header)
        jsonres = self._session.http.json(res,
                                          schema=self._MEDIATOKEN_SCHEMA)
        mediatoken = jsonres['token']

        res = self._session.http.post(self._LICENSE_API,
                                      params={"t": mediatoken},
                                      json={"kv": "a", "lt": ticket})
        jsonres = self._session.http.json(res,
                                          schema=self._LICENSE_SCHEMA)
        cid = jsonres['cid']
        k = jsonres['k']

        res = sum([self.STRTABLE.find(k[i]) * (58 ** (len(k) - 1 - i))
                  for i in range(len(k))])
        encvideokey = struct.pack('>QQ', res >> 64, res & 0xffffffffffffffff)

        # HKEY:
        # RC4KEY = unhexlify('DB98A8E7CECA3424D975280F90BD03EE')
        # RC4DATA = unhexlify(b'D4B718BBBA9CFB7D0192A58F9E2D146A'
        #                     b'FC5DB29E4352DE05FC4CF2C1005804BB')
        # rc4 = ARC4.new(RC4KEY)
        # HKEY = rc4.decrypt(RC4DATA)
        h = hmac.new(unhexlify(self.HKEY),
                     (cid + self.deviceid).encode("utf-8"),
                     digestmod=hashlib.sha256)
        enckey = h.digest()

        aes = AES.new(enckey, AES.MODE_ECB)
        rawvideokey = aes.decrypt(encvideokey)

        return rawvideokey

    def send(self, request, stream=False, timeout=None, verify=True, cert=None,
             proxies=None):
        resp = Response()
        resp.status_code = 200
        ticket = re.findall(r"abematv-license://(.*)", request.url)[0]
        resp._content = self._get_videokey_from_ticket(ticket)
        return resp

    def close(self):
        return


class AbemaTV(Plugin):
    '''
    Abema.tv https://abema.tv/
    Note: Streams are geo-restricted to Japan

    '''
    _url_re = re.compile(r"""https://abema\.tv/(
        now-on-air/(?P<onair>[^\?]+)
        |
        video/episode/(?P<episode>[^\?]+)
        |
        channels/.+?/slots/(?P<slots>[^\?]+)
        )""", re.VERBOSE)

    _CHANNEL = "https://api.abema.io/v1/channels"

    _USER_API = "https://api.abema.io/v1/users"

    _PRGM_API = "https://api.abema.io/v1/video/programs/{0}"

    _SLOTS_API = "https://api.abema.io/v1/media/slots/{0}"

    _PRGM3U8 = "https://vod-abematv.akamaized.net/program/{0}/playlist.m3u8"

    _SLOTM3U8 = "https://vod-abematv.akamaized.net/slot/{0}/playlist.m3u8"

    SECRETKEY = (b"v+Gjs=25Aw5erR!J8ZuvRrCx*rGswhB&qdHd_SYerEWdU&a?3DzN9B"
                 b"Rbp5KwY4hEmcj5#fykMjJ=AuWz5GSMY-d@H7DMEh3M@9n2G552Us$$"
                 b"k9cD=3TxwWe86!x#Zyhe")

    _USER_SCHEMA = validate.Schema({"profile": {"userId": validate.text},
                                    "token": validate.text})

    _CHANNEL_SCHEMA = validate.Schema({"channels": [{"id": validate.text,
                                      "name": validate.text,
                                       "playback": {validate.optional("dash"):
                                                    validate.text,
                                                    "hls": validate.text}}]})

    _PRGM_SCHEMA = validate.Schema({"label": {validate.optional("free"): bool}})

    _SLOT_SCHEMA = validate.Schema({"slot": {"flags": {validate.optional("timeshiftFree"): bool}}})

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def __init__(self, url):
        super().__init__(url)
        self.session.http.headers.update({'User-Agent': useragents.CHROME})

    def _generate_applicationkeysecret(self, deviceid):
        deviceid = deviceid.encode("utf-8")  # for python3
        # plus 1 hour and drop minute and secs
        # for python3 : floor division
        ts_1hour = (int(time.time()) + 60 * 60) // 3600 * 3600
        time_struct = time.gmtime(ts_1hour)
        ts_1hour_str = str(ts_1hour).encode("utf-8")

        h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
        h.update(self.SECRETKEY)
        tmp = h.digest()
        for i in range(time_struct.tm_mon):
            h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
            h.update(tmp)
            tmp = h.digest()
        h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
        h.update(urlsafe_b64encode(tmp).rstrip(b"=") + deviceid)
        tmp = h.digest()
        for i in range(time_struct.tm_mday % 5):
            h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
            h.update(tmp)
            tmp = h.digest()

        h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
        h.update(urlsafe_b64encode(tmp).rstrip(b"=") + ts_1hour_str)
        tmp = h.digest()

        for i in range(time_struct.tm_hour % 5):  # utc hour
            h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
            h.update(tmp)
            tmp = h.digest()

        return urlsafe_b64encode(tmp).rstrip(b"=").decode("utf-8")

    def _is_playable(self, vtype, vid):
        auth_header = {"Authorization": "Bearer " + self.usertoken}
        if vtype == "episode":
            res = self.session.http.get(self._PRGM_API.format(vid),
                                        headers=auth_header)
            jsonres = self.session.http.json(res, schema=self._PRGM_SCHEMA)
            return jsonres["label"].get("free", False) is True
        elif vtype == "slots":
            res = self.session.http.get(self._SLOTS_API.format(vid),
                                        headers=auth_header)
            jsonres = self.session.http.json(res, schema=self._SLOT_SCHEMA)
            return jsonres["slot"]["flags"].get("timeshiftFree", False) is True

    def _get_streams(self):
        deviceid = str(uuid.uuid4())
        appkeysecret = self._generate_applicationkeysecret(deviceid)
        json_data = {"deviceId": deviceid,
                     "applicationKeySecret": appkeysecret}
        res = self.session.http.post(self._USER_API, json=json_data)
        jsonres = self.session.http.json(res, schema=self._USER_SCHEMA)
        self.usertoken = jsonres['token']  # for authorzation

        matchresult = self._url_re.match(self.url)
        if matchresult.group("onair"):
            onair = matchresult.group("onair")
            if onair == "news-global":
                self._CHANNEL = update_qsd(self._CHANNEL, {"division": "1"})
            res = self.session.http.get(self._CHANNEL)
            jsonres = self.session.http.json(res, schema=self._CHANNEL_SCHEMA)
            channels = jsonres["channels"]
            for channel in channels:
                if onair == channel["id"]:
                    break
            else:
                raise NoStreamsError(self.url)
            playlisturl = channel["playback"]["hls"]
        elif matchresult.group("episode"):
            episode = matchresult.group("episode")
            if not self._is_playable("episode", episode):
                log.error("Premium stream is not playable")
                return {}
            playlisturl = self._PRGM3U8.format(episode)
        elif matchresult.group("slots"):
            slots = matchresult.group("slots")
            if not self._is_playable("slots", slots):
                log.error("Premium stream is not playable")
                return {}
            playlisturl = self._SLOTM3U8.format(slots)

        log.debug("URL={0}".format(playlisturl))

        # hook abematv private protocol
        self.session.http.mount("abematv-license://",
                                AbemaTVLicenseAdapter(self.session, deviceid,
                                                      self.usertoken))

        streams = HLSStream.parse_variant_playlist(self.session, playlisturl)
        if not streams:
            return {"live": HLSStream(self.session, playlisturl)}
        else:
            return streams


__plugin__ = AbemaTV
