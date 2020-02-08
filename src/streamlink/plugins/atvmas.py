"""
Support for the live streams of ATV más on Albavision site
    - http://www.atv.pe/envivo
Call stream by using http://www.atvmas.pe/envivo ! 
"""
import logging
import re
import time

from streamlink import PluginError
from streamlink.compat import quote, urlencode
from streamlink.plugin import Plugin
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)

class Atvmas(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?(atvmas.pe)/en-?vivo")
    _token_input_re = re.compile(r"Math.floor\(Date.now\(\) / 3600000\),'([a-f0-9OK]+)'")
    _live_url_re = re.compile(r"LIVE_URL = '(.*?)';")
    _playlist_re = re.compile(r"file:\s*'(http.*m3u8)'")
    _token_url_re = re.compile(r"https://.*/token/.*?\?rsk=")

    _channel_urls = {
		'ATVmas': 'http://dgrzfw9otv9ra.cloudfront.net/player_atv_mas.html?iut='
    }

    def __init__(self, url):
        super(Atvmas, self).__init__("http://www.atv.pe/envivo")
        self._page = None

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @property
    def page(self):
        if not self._page:
            self._page = self.session.http.get(self.url)
        return self._page

    def _get_token_url(self):
        token = self._get_live_url_token()
        if token:
            m = self._token_url_re.findall(self.page.text)
            log.debug("get_token_url m {0}".format(m))
            log.debug("get_token_url m0 {0}".format(m[1]))
            token_url = m and m[1]
            if token_url:
                log.debug("token_url={0}{1}".format(token_url, token))
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
            return token_out[:-2]  # return token without OK suffix
        else:
            log.error("Invalid site token: {0} => {1}".format(token_in, token_out))

    def _get_live_url_token(self):
        m = self._token_input_re.findall(self.page.text)
        log.debug("Token input: {0}".format(m[1]))
        if m:
            date = int(time.time()//3600)
            return self.transform_token(m[1], date) or self.transform_token(m[1], date - 1)

    def _get_token(self):
        token_url = self._get_token_url()
        if token_url:
            res = self.session.http.get(token_url)
            data = self.session.http.json(res)
            if data['success']:
                return data['token']

    def _get_streams(self):
        token = self._get_token()
        log.debug("token {0}".format(token))
        live_channel = 'ATVmas'

        log.debug("Live channel: {0}".format(live_channel))
        player_url = self._channel_urls[live_channel]+quote(token)
        log.debug("player url bei live channel {0}".format(player_url))
        page = self.session.http.get(player_url, raise_for_status=False)
        if "block access from your country." in page.text:
            raise PluginError("Content is geo-locked")
        m = self._playlist_re.search(page.text)
        log.debug("m {0}".format(m))
        playlist_url = m and update_scheme(self.url, m.group(1))
        log.debug("playlist_url {0}".format(playlist_url))

        if playlist_url:
            stream_url = "{0}?{1}".format(playlist_url, urlencode({"iut": token}))
            return HLSStream.parse_variant_playlist(self.session, stream_url, headers={"referer": player_url})


__plugin__ = Atvmas
