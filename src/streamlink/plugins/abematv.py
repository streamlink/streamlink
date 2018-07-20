from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin
from streamlink.plugin.plugin import parse_url_params
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

import hashlib
import hmac
import re
import struct
import time
import uuid
from base64 import urlsafe_b64encode
from binascii import unhexlify

from Crypto.Cipher import AES
from requests import Response
from requests.adapters import BaseAdapter


class AbemaTVLicenseAdapter(BaseAdapter):
    '''
    Handling abematv-license:// protocol to get real video key_data.
    '''
    SECRETKEY = b"v+Gjs=25Aw5erR!J8ZuvRrCx*rGswhB&qdHd_SYerEWdU&a?3DzN9BRbp5KwY4hEmcj5#fykMjJ=AuWz5GSMY-d@H7DMEh3M@9n2G552Us$$k9cD=3TxwWe86!x#Zyhe"
    
    STRTABLE = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    
    HMACKEY = b"3AF0298C219469522A313570E8583005A642E73EDD58E3EA2FB7339D3DF1597E"

    def __init__(self, session):
        self._plugin_session = session
        super(AbemaTVLicenseAdapter, self).__init__()

    def _generateApplicationKeySecret(self, deviceId):
        deviceId = deviceId.encode("utf-8") # for python3
        # plus 1 hour and drop minute and secs
        ts_1hour = (int(time.time()) + 60*60) // 3600 * 3600 # for python3 : floor division
        time_struct = time.gmtime(ts_1hour)

        h = hmac.new(SECRETKEY, digestmod=hashlib.sha256)
        h.update(SECRETKEY)
        tmp = h.digest()
        for i in range(time_struct.tm_mon):
            h = hmac.new(SECRETKEY, digestmod=hashlib.sha256)
            h.update(tmp)
            tmp = h.digest()
        h = hmac.new(SECRETKEY, digestmod=hashlib.sha256)
        h.update(urlsafe_b64encode(tmp).rstrip(b"=")+deviceId)
        tmp = h.digest()
        for i in range(time_struct.tm_mday % 5):
            h = hmac.new(SECRETKEY, digestmod=hashlib.sha256)
            h.update(tmp)
            tmp = h.digest()

        h = hmac.new(SECRETKEY, digestmod=hashlib.sha256)
        h.update(urlsafe_b64encode(tmp).rstrip(b"=") + str(ts_1hour).encode("utf-8"))
        tmp = h.digest()

        for i in range(time_struct.tm_hour % 5):  # utc hour
            h = hmac.new(SECRETKEY, digestmod=hashlib.sha256)
            h.update(tmp)
            tmp = h.digest()

        return urlsafe_b64encode(tmp).rstrip(b"=").decode("utf-8")

    def _getVideoKeyFromTicket(self, ticket):
        deviceId = str(uuid.uuid4())
        res = requests.post("https://api.abema.io/v1/users", json={
                                             "deviceId": deviceId, "applicationKeySecret": self._generateApplicationKeySecret(deviceId)})
        usertoken = res.json()['token']

        params = {"osName": "android", "osVersion": "6.0.1", "osLang": "ja_JP", "osTimezone": "Asia/Tokyo", "appId": "tv.abema", "appVersion": "3.27.1"}
        res = self._plugin_session.http.get("https://api.abema.io/v1/media/token", params=params, headers={"Authorization": "Bearer "+usertoken})
        mediatoken = res.json()['token']

        res = self._plugin_session.http.post("https://license.abema.io/abematv-hls", params={"t": mediatoken}, json={"kv": "a", "lt": ticket})
        cid = res.json()['cid']
        key = res.json()['k']

        res = sum([STRTABLE.find(key[i]) * (58 ** (len(key) - 1 - i))  for i in range(len(key))])
        encVideoKey = struct.pack('>QQ', res >> 64, res & 0xffffffffffffffff)

        # Crypto.Cipher.ARC4.new('DB98A8E7CECA3424D975280F90BD03EE'.decode('hex')).decrypt('D4B718BBBA9CFB7D0192A58F9E2D146AFC5DB29E4352DE05FC4CF2C1005804BB'.decode('hex')).encode('hex')
        h = hmac.new(unhexlify(HMACKEY), (cid+deviceId).encode("utf-8"), digestmod=hashlib.sha256)
        enckey = h.digest()

        aes = AES.new(enckey, AES.MODE_ECB)
        rawVideoKey = aes.decrypt(encVideoKey)

        return rawVideoKey

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        resp = Response()
        resp.status_code = 200
        ticket = re.findall(r"abematv-license://(.*)", request.url)[0]
        resp._content = self._getVideoKeyFromTicket(ticket)
        return resp

    def close(self):
        return



class AbemaTV(Plugin):
    '''
    Abema.tv https://abema.tv/
    Note: Streams are geo-restricted to Japan

    '''
    _url_re = re.compile(r"https://abema\.tv/(now-on-air/(?P<onair>.+)|video/episode/(?P<episode>.+)|channels/.+?/slots/(?P<slot>.+))")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def __init__(self, url):
        super(AbemaTV, self).__init__(url)

    def _get_streams(self):
        url, params = parse_url_params(self.url)
        matchResult = self._url_re.match(url)
        if matchResult.group("onair"):
            onair = matchResult.group("onair")
            channels = self.session.http.get("https://api.abema.io/v1/channels").json()["channels"]
            for channel in channels:
                if onair == channel["id"]:
                    break
            else:
                raise NoStreamsError 
            playlisturl = channel["playback"]["hls"]
        elif matchResult.group("episode"):
            playlisturl = "https://vod-abematv.akamaized.net/program/%s/playlist.m3u8"%(matchResult.group("episode"))
        elif matchResult.group("slot"):
            playlisturl = "https://vod-abematv.akamaized.net/slot/%s/playlist.m3u8"%(matchResult.group("slot"))

        self.logger.debug("AbemaTV playlist URL={0}; ", playlisturl)
        
        self.session.http.mount("abematv-license://",AbemaTVLicenseAdapter(self.session)) # hook abematv private protocol

        streams = HLSStream.parse_variant_playlist(self.session, playlisturl)
        if not streams:
            return {"live": HLSStream(self.session, playlisturl)}
        else:
            return streams

__plugin__ = AbemaTV
