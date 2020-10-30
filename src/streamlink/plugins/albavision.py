"""
Support for the live streams on Albavision sites
    - http://www.tvc.com.ec/envivo
    - http://www.rts.com.ec/envivo
    - http://www.elnueve.com.ar/en-vivo
    - http://www.atv.pe/envivo/ATV
    - http://www.atv.pe/envivo/ATVMas
"""
import logging
import re
import time
from urllib.parse import quote, urlencode, urlparse

from streamlink import PluginError
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


class Albavision(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?(tvc.com.ec|rts.com.ec|elnueve.com.ar|atv.pe)/en-?vivo(?:/ATV(?:Mas)?)?")
    _token_input_re = re.compile(r"Math.floor\(Date.now\(\) / 3600000\),'([a-f0-9OK]+)'")
    _live_url_re = re.compile(r"LIVE_URL = '(.*?)';")
    _playlist_re = re.compile(r"file:\s*'(http.*m3u8)'")
    _token_url_re = re.compile(r"https://.*/token/.*?\?rsk=")

    _channel_urls = {
        'ATV': 'http://dgrzfw9otv9ra.cloudfront.net/player_atv.html?iut=',
        'ATVMas': 'http://dgrzfw9otv9ra.cloudfront.net/player_atv_mas.html?iut=',
        'Canal5': 'http://dxejh4fchgs18.cloudfront.net/player_televicentro.html?iut=',
        'Guayaquil': 'http://d2a6tcnofawcbm.cloudfront.net/player_rts.html?iut=',
        'Quito': 'http://d3aacg6baj4jn0.cloudfront.net/reproductor_rts_o_quito.html?iut=',
    }

    def __init__(self, url):
        super().__init__(url)
        self._page = None

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @property
    def page(self):
        if not self._page:
            self._page = self.session.http.get(self.url)
        return self._page

    def _get_token_url(self, channelnumber):
        token = self._get_live_url_token(channelnumber)
        if token:
            m = self._token_url_re.findall(self.page.text)
            token_url = m and m[channelnumber]
            if token_url:
                return token_url + token
        else:
            log.error("Could not find site token")

    @staticmethod
    def transform_token(token_in, date):
        token_out = list(token_in)
        offset = len(token_in)
        for i in range(offset - 1, -1, -1):
            p = (i * date) % offset
            # swap chars at p and i
            token_out[i], token_out[p] = token_out[p], token_out[i]
        token_out = ''.join(token_out)
        if token_out.endswith("OK"):
            return token_out[:-2]
        else:
            log.error("Invalid site token: {0} => {1}".format(token_in, token_out))

    def _get_live_url_token(self, channelnumber):
        m = self._token_input_re.findall(self.page.text)
        log.debug("Token input: {0}".format(m[channelnumber]))
        if m:
            date = int(time.time() // 3600)
            return self.transform_token(m[channelnumber], date) or self.transform_token(m[channelnumber], date - 1)

    def _get_token(self, channelnumber):
        token_url = self._get_token_url(channelnumber)
        if token_url:
            res = self.session.http.get(token_url)
            data = self.session.http.json(res)
            if data['success']:
                return data['token']

    def _get_streams(self):
        m = self._live_url_re.search(self.page.text)
        playlist_url = m and update_scheme(self.url, m.group(1))
        player_url = self.url
        live_channel = None
        p = urlparse(player_url)
        channelnumber = 0
        if p.netloc.endswith("tvc.com.ec"):
            live_channel = "Canal5"
        elif p.netloc.endswith("rts.com.ec"):
            live_channel = "Guayaquil"
        elif p.netloc.endswith("atv.pe"):
            if p.path.endswith(("ATVMas", "ATVMas/")):
                live_channel = "ATVMas"
                channelnumber = 1
            else:
                live_channel = "ATV"
        token = self._get_token(channelnumber)
        log.debug("token {0}".format(token))
        if playlist_url:
            log.debug("Found playlist URL in the page")
        else:
            if live_channel:
                log.debug("Live channel: {0}".format(live_channel))
                player_url = self._channel_urls[live_channel] + quote(token)
                page = self.session.http.get(player_url, raise_for_status=False)
                if "block access from your country." in page.text:
                    raise PluginError("Content is geo-locked")
                m = self._playlist_re.search(page.text)
                playlist_url = m and update_scheme(self.url, m.group(1))
            else:
                log.error("Could not find the live channel")

        if playlist_url:
            stream_url = "{0}?{1}".format(playlist_url, urlencode({"iut": token}))
            return HLSStream.parse_variant_playlist(self.session, stream_url, headers={"referer": player_url})


__plugin__ = Albavision
