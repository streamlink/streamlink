from __future__ import unicode_literals

import logging
import re
from collections import OrderedDict

from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import http, useragents
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class USTVNow(Plugin):
    _url_re = re.compile(r"https?://(?:watch\.)?ustvnow\.com(?:/(?:watch|guide)/(?P<scode>\w+))?")
    _token_re = re.compile(r'''var\s+token\s*=\s*"(.*?)";''')
    _login_url = "https://watch.ustvnow.com/account/login"
    _signin_url = "https://watch.ustvnow.com/account/signin"
    _guide_url = "http://m.ustvnow.com/gtv/1/live/channelguidehtml"
    _stream_url = "http://m.ustvnow.com/stream/1/live/view"

    arguments = PluginArguments(
        PluginArgument(
            "username",
            metavar="USERNAME",
            required=True,
            help="Your USTV Now account username"
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            required=True,
            help="Your USTV Now account password",
            prompt="Enter USTV Now account password"
        ),
        PluginArgument(
            "station-code",
            metavar="CODE",
            help="USTV Now station code"
        ),
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def login(self, username, password):
        r = http.get(self._signin_url)
        csrf = None

        for input in itertags(r.text, "input"):
            if input.attributes['name'] == "csrf_ustvnow":
                csrf = input.attributes['value']

        log.debug("CSRF: {0}", csrf)

        r = http.post(self._login_url, data={'csrf_ustvnow': csrf,
                                             'signin_email': username,
                                             'signin_password': password,
                                             'signin_remember': '1'})
        m = self._token_re.search(r.text)
        return m and m.group(1)

    def _get_streams(self):
        """
        Finds the streams from tvcatchup.com.
        """
        token = self.login(self.get_option("username"), self.get_option("password"))
        m = self._url_re.match(self.url)
        scode = m and m.group("scode") or self.get_option("station_code")

        res = http.get(self._guide_url, params=dict(token=token))

        channels = OrderedDict()
        for t in itertags(res.text, "a"):
            if t.attributes.get('cs'):
                channels[t.attributes.get('cs').lower()] = t.attributes.get('title').replace("Watch ", "").strip()

        if not scode:
            log.error("Station code not provided, use --ustvnow-station-code.")
            log.info("Available stations are: \n{0} ".format('\n'.join('    {0} ({1})'.format(c, n) for c, n in channels.items())))
            return

        if scode in channels:
            log.debug("Finding streams for: {0}", channels.get(scode))

            r = http.get(self._stream_url, params={"scode": scode,
                                                   "token": token,
                                                   "br_n": "Firefox",
                                                   "br_v": "52",
                                                   "br_d": "desktop"},
                         headers={"User-Agent": useragents.FIREFOX})

            data = http.json(r)
            return HLSStream.parse_variant_playlist(self.session, data["stream"])
        else:
            log.error("Invalid station-code: {0}", scode)


__plugin__ = USTVNow
