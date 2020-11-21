import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme
from streamlink.utils.url import url_concat

log = logging.getLogger(__name__)


class ABweb(Plugin):
    url_l = 'https://www.abweb.com/BIS-TV-Online/identification.aspx?ReturnUrl=%2fBIS-TV-Online%2fbistvo-tele-universal.aspx'

    _url_re = re.compile(r'https?://(?:www\.)?abweb\.com/BIS-TV-Online/bistvo-tele-universal.aspx', re.IGNORECASE)
    _hls_re = re.compile(r'''["']file["']:\s?["'](?P<url>[^"']+\.m3u8[^"']+)["']''')

    arguments = PluginArguments(
        PluginArgument(
            "username",
            requires=["password"],
            sensitive=True,
            metavar="USERNAME",
            help="""
            The username associated with your ABweb account, required to access any
            ABweb stream.
            """,
            prompt="Enter ABweb username"
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="A ABweb account password to use with --abweb-username.",
            prompt="Enter ABweb password"
        ),
        PluginArgument(
            "purge-credentials",
            action="store_true",
            help="""
            Purge cached ABweb credentials to initiate a new session and
            reauthenticate.
            """)
    )

    def __init__(self, url):
        super().__init__(url)
        self._authed = (self.session.http.cookies.get('ASP.NET_SessionId', domain='.abweb.com')
                        and self.session.http.cookies.get('.abportail1', domain='.abweb.com'))

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _login(self, username, password):
        log.debug('Attempting to login.')

        data = {}
        for i in itertags(self.session.http.get(self.url_l).text, 'input'):
            data[i.attributes.get('name')] = i.attributes.get('value', '')

        if not data:
            raise PluginError('Missing input data on login website.')

        data.update({
            'ctl00$ContentPlaceHolder1$Login1$UserName': username,
            'ctl00$ContentPlaceHolder1$Login1$Password': password,
            'ctl00$ContentPlaceHolder1$Login1$LoginButton.x': '0',
            'ctl00$ContentPlaceHolder1$Login1$LoginButton.y': '0',
            'ctl00$ContentPlaceHolder1$Login1$RememberMe': 'on',
        })

        self.session.http.post(self.url_l, data=data)
        if (self.session.http.cookies.get('ASP.NET_SessionId') and self.session.http.cookies.get('.abportail1')):
            for cookie in self.session.http.cookies:
                # remove www from cookie domain
                cookie.domain = '.abweb.com'

            self.save_cookies(default_expires=3600 * 24)
            return True
        else:
            log.error('Failed to login, check your username/password')
            return False

    def _get_streams(self):
        self.session.http.headers.update({
            'Referer': 'http://www.abweb.com/BIS-TV-Online/bistvo-tele-universal.aspx'
        })

        login_username = self.get_option('username')
        login_password = self.get_option('password')

        if self.options.get('purge_credentials'):
            self.clear_cookies()
            self._authed = False
            log.info('All credentials were successfully removed.')

        if self._authed:
            log.info('Attempting to authenticate using cached cookies')
        elif not self._authed and not (login_username and login_password):
            log.error('A login for ABweb is required, use --abweb-username USERNAME --abweb-password PASSWORD')
            return
        elif not self._authed and not self._login(login_username, login_password):
            return

        log.debug('get iframe_url')
        res = self.session.http.get(self.url)
        for iframe in itertags(res.text, 'iframe'):
            iframe_url = iframe.attributes.get('src')
            if iframe_url.startswith('/'):
                iframe_url = url_concat('https://www.abweb.com', iframe_url)
            else:
                iframe_url = update_scheme('https://', iframe_url)
            log.debug(f'iframe_url={iframe_url}')
            break
        else:
            raise PluginError('No iframe_url found.')

        self.session.http.headers.update({'Referer': iframe_url})
        res = self.session.http.get(iframe_url)
        m = self._hls_re.search(res.text)
        if not m:
            raise PluginError('No hls_url found.')

        hls_url = update_scheme('https://', m.group('url'))
        streams = HLSStream.parse_variant_playlist(self.session, hls_url)
        if streams:
            yield from streams.items()
        else:
            yield 'live', HLSStream(self.session, hls_url)


__plugin__ = ABweb
