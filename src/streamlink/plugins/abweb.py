import re
import time

from streamlink.cache import Cache
from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin import PluginArguments, PluginArgument
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme


class ABweb(Plugin):
    '''BIS Livestreams of french AB Groupe
       http://www.abweb.com/BIS-TV-Online/
    '''

    login_url = 'http://www.abweb.com/BIS-TV-Online/Default.aspx'

    _url_re = re.compile(r'https?://(?:www\.)?abweb\.com/BIS-TV-Online/bistvo-tele-universal.aspx', re.IGNORECASE)
    _hls_re = re.compile(r'''["']file["']:\s?["'](?P<url>[^"']+\.m3u8[^"']+)["']''')
    _iframe_re = re.compile(r'''<iframe[^>]+src=["'](?P<url>[^"']+)["']''')

    _input_re = re.compile(r'''(<input[^>]+>)''')
    _name_re = re.compile(r'''name=["']([^"']*)["']''')
    _value_re = re.compile(r'''value=["']([^"']*)["']''')

    expires_time = 3600 * 24

    arguments = PluginArguments(
        PluginArgument(
            "username",
            required=True,
            requires=["password"],
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
        super(ABweb, self).__init__(url)
        self._session_attributes = Cache(filename='plugin-cache.json', key_prefix='abweb:attributes')
        self._authed = self._session_attributes.get('ASP.NET_SessionId') and self._session_attributes.get('.abportail1')
        self._expires = self._session_attributes.get('expires', time.time() + self.expires_time)

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def set_expires_time_cache(self):
        expires = time.time() + self.expires_time
        self._session_attributes.set('expires', expires, expires=self.expires_time)

    def get_iframe_url(self):
        self.logger.debug('search for an iframe')
        res = self.session.http.get(self.url)
        m = self._iframe_re.search(res.text)
        if not m:
            raise PluginError('No iframe found.')

        iframe_url = m.group('url')
        iframe_url = update_scheme('http://', iframe_url)
        self.logger.debug('IFRAME URL={0}'.format(iframe_url))
        return iframe_url

    def get_hls_url(self, iframe_url):
        self.logger.debug('search for hls url')
        res = self.session.http.get(iframe_url)
        m = self._hls_re.search(res.text)
        if not m:
            raise PluginError('No playlist found.')

        return m and m.group('url')

    def _login(self, username, password):
        '''login and update cached cookies'''
        self.logger.debug('login ...')

        res = self.session.http.get(self.login_url)
        input_list = self._input_re.findall(res.text)
        if not input_list:
            raise PluginError('Missing input data on login website.')

        data = {}
        for _input_data in input_list:
            try:
                _input_name = self._name_re.search(_input_data).group(1)
            except AttributeError:
                continue

            try:
                _input_value = self._value_re.search(_input_data).group(1)
            except AttributeError:
                _input_value = ''

            data[_input_name] = _input_value

        login_data = {
            'ctl00$Login1$UserName': username,
            'ctl00$Login1$Password': password,
            'ctl00$Login1$LoginButton.x': '0',
            'ctl00$Login1$LoginButton.y': '0'
        }
        data.update(login_data)

        res = self.session.http.post(self.login_url, data=data)

        for cookie in self.session.http.cookies:
            self._session_attributes.set(cookie.name, cookie.value, expires=3600 * 24)

        if self._session_attributes.get('ASP.NET_SessionId') and self._session_attributes.get('.abportail1'):
            self.logger.debug('New session data')
            self.set_expires_time_cache()
            return True
        else:
            self.logger.error('Failed to login, check your username/password')
            return False

    def _get_streams(self):
        self.session.http.headers.update({'User-Agent': useragents.CHROME,
                             'Referer': 'http://www.abweb.com/BIS-TV-Online/bistvo-tele-universal.aspx'})

        login_username = self.get_option('username')
        login_password = self.get_option('password')

        if self.options.get('purge_credentials'):
            self._session_attributes.set('ASP.NET_SessionId', None, expires=0)
            self._session_attributes.set('.abportail1', None, expires=0)
            self._authed = False
            self.logger.info('All credentials were successfully removed.')

        if not self._authed and not (login_username and login_password):
            self.logger.error('A login for ABweb is required, use --abweb-username USERNAME --abweb-password PASSWORD')
            return

        if self._authed:
            if self._expires < time.time():
                self.logger.debug('get new cached cookies')
                # login after 24h
                self.set_expires_time_cache()
                self._authed = False
            else:
                self.logger.info('Attempting to authenticate using cached cookies')
                self.session.http.cookies.set('ASP.NET_SessionId', self._session_attributes.get('ASP.NET_SessionId'))
                self.session.http.cookies.set('.abportail1', self._session_attributes.get('.abportail1'))

        if not self._authed and not self._login(login_username, login_password):
            return

        iframe_url = self.get_iframe_url()
        self.session.http.headers.update({'Referer': iframe_url})

        hls_url = self.get_hls_url(iframe_url)
        hls_url = update_scheme(self.url, hls_url)

        self.logger.debug('URL={0}'.format(hls_url))
        variant = HLSStream.parse_variant_playlist(self.session, hls_url)
        if variant:
            for q, s in variant.items():
                yield q, s
        else:
            yield 'live', HLSStream(self.session, hls_url)


__plugin__ = ABweb
