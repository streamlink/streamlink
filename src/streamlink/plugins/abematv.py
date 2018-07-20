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
from streamlink.plugin.api import useragents
from streamlink.plugin.plugin import parse_url_params
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class AbemaTVLicenseAdapter(BaseAdapter):
    '''
    Handling abematv-license:// protocol to get real video key_data.
    '''
    SECRETKEY = (b"v+Gjs=25Aw5erR!J8ZuvRrCx*rGswhB&qdHd_SYerEWdU&a?3DzN9B"
                 b"Rbp5KwY4hEmcj5#fykMjJ=AuWz5GSMY-d@H7DMEh3M@9n2G552Us$$"
                 b"k9cD=3TxwWe86!x#Zyhe")

    STRTABLE = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    HKEY = b"3AF0298C219469522A313570E8583005A642E73EDD58E3EA2FB7339D3DF1597E"

    _USER_API = "https://api.abema.io/v1/users"

    _TOKEN_API = "https://api.abema.io/v1/media/token"

    _LICENSE_API = "https://license.abema.io/abematv-hls"

    def __init__(self, session):
        self._plugin_session = session
        self._plugin_session.http.headers.update(
            {'User-Agent': useragents.CHROME})
        super(AbemaTVLicenseAdapter, self).__init__()

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

    def _get_videokey_from_ticket(self, ticket):
        deviceid = str(uuid.uuid4())
        appkeysecret = self._generate_applicationkeysecret(deviceid)
        json_data = {"deviceId": deviceid,
                     "applicationKeySecret": appkeysecret}
        res = self._plugin_session.http.post(self._USER_API, json=json_data)
        usertoken = res.json()['token']

        params = {
            "osName": "android",
            "osVersion": "6.0.1",
            "osLang": "ja_JP",
            "osTimezone": "Asia/Tokyo",
            "appId": "tv.abema",
            "appVersion": "3.27.1"
        }
        auth_header = {"Authorization": "Bearer " + usertoken}
        res = self._plugin_session.http.get(self._TOKEN_API, params=params,
                                            headers=auth_header)
        mediatoken = res.json()['token']

        res = self._plugin_session.http.post(self._LICENSE_API,
                                             params={"t": mediatoken},
                                             json={"kv": "a", "lt": ticket})
        cid = res.json()['cid']
        k = res.json()['k']

        res = sum([self.STRTABLE.find(k[i]) * (58 ** (len(k) - 1 - i))
                  for i in range(len(k))])
        encvideokey = struct.pack('>QQ', res >> 64, res & 0xffffffffffffffff)

        # HMACKEY:
        # rc4 = ARC4.new('DB98A8E7CECA3424D975280F90BD03EE'.decode('hex'))
        # rc4.decrypt('D4B718BBBA9CFB7D0192A58F9E2D146AFC5DB29E4352DE05FC4CF2C1005804BB'.decode('hex')).encode('hex')
        h = hmac.new(unhexlify(self.HKEY), (cid + deviceid).encode("utf-8"),
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
        now-on-air/(?P<onair>.+)
        |
        video/episode/(?P<episode>.+)
        |
        channels/.+?/slots/(?P<slot>.+)
        )""", re.VERBOSE)

    _CHANNEL = "https://api.abema.io/v1/channels"

    _PROGRAMM3U8 = "https://vod-abematv.akamaized.net/program/%s/playlist.m3u8"

    _SLOTM3U8 = "https://vod-abematv.akamaized.net/slot/%s/playlist.m3u8"

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def __init__(self, url):
        super(AbemaTV, self).__init__(url)

    def _get_streams(self):
        url, params = parse_url_params(self.url)
        matchresult = self._url_re.match(url)
        if matchresult.group("onair"):
            onair = matchresult.group("onair")
            channels = self.session.http.get(self._CHANNEL).json()["channels"]
            for channel in channels:
                if onair == channel["id"]:
                    break
            else:
                raise NoStreamsError
            playlisturl = channel["playback"]["hls"]
        elif matchresult.group("episode"):
            playlisturl = self._PROGRAMM3U8 % (matchresult.group("episode"))
        elif matchresult.group("slot"):
            playlisturl = self._SLOTM3U8 % (matchresult.group("slot"))

        log.debug("URL={0}".format(playlisturl))

        # hook abematv private protocol
        self.session.http.mount("abematv-license://",
                                AbemaTVLicenseAdapter(self.session))

        streams = HLSStream.parse_variant_playlist(self.session, playlisturl)
        if not streams:
            return {"live": HLSStream(self.session, playlisturl)}
        else:
            return streams


__plugin__ = AbemaTV
