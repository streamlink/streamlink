import re
import time
import uuid

from streamlink.cache import Cache
from streamlink.plugin import Plugin
from streamlink.plugin import PluginArguments, PluginArgument
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class Zattoo(Plugin):
    API_HELLO = '{0}/zapi/session/hello'
    API_LOGIN = '{0}/zapi/v2/account/login'
    API_CHANNELS = '{0}/zapi/v2/cached/channels/{1}?details=False'
    API_WATCH = '{0}/zapi/watch'
    API_WATCH_REC = '{0}/zapi/watch/recording/{1}'
    API_WATCH_VOD = '{0}/zapi/avod/videos/{1}/watch'

    _url_re = re.compile(r'''
        https?://
        (?P<base_url>
        zattoo\.com
        |
        tvonline\.ewe\.de
        |
        nettv\.netcologne\.de
        )/
        (?:
            (?:ondemand/)?(?:watch/(?:[^/\s]+)(?:/[^/]+/(?P<recording_id>\d+)))
            |
            watch/(?P<channel>[^/\s]+)
            |
            ondemand/watch/(?P<vod_id>[^-]+)-
        )
        ''', re.VERBOSE)

    _app_token_re = re.compile(r"""window\.appToken\s+=\s+'([^']+)'""")

    _channels_schema = validate.Schema({
        'success': int,
        'channel_groups': [{
            'channels': [
                {
                    'display_alias': validate.text,
                    'cid': validate.text
                },
            ]
        }]},
        validate.get('channel_groups'),
    )

    arguments = PluginArguments(
        PluginArgument(
            "email",
            requires=["password"],
            metavar="EMAIL",
            help="""
            The email associated with your zattoo account, required to access
            any zattoo stream.
            """),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="""
            A zattoo account password to use with --zattoo-email.
            """),
        PluginArgument(
            "purge-credentials",
            action="store_true",
            help="""
            Purge cached zattoo credentials to initiate a new session
            and reauthenticate.
            """)
    )

    def __init__(self, url):
        super(Zattoo, self).__init__(url)
        self._session_attributes = Cache(filename='plugin-cache.json', key_prefix='zattoo:attributes')
        self._authed = self._session_attributes.get('beaker.session.id') and self._session_attributes.get(
            'pzuid') and self._session_attributes.get('power_guide_hash')
        self._uuid = self._session_attributes.get('uuid')
        self._expires = self._session_attributes.get('expires', 946684800)

        self.base_url = 'https://{0}'.format(Zattoo._url_re.match(url).group('base_url'))
        self.headers = {
            'User-Agent': useragents.CHROME,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self.base_url
        }

    @classmethod
    def can_handle_url(cls, url):
        return Zattoo._url_re.match(url)

    def _hello(self):
        self.logger.debug('_hello ...')
        res = http.get(self.base_url)
        match = self._app_token_re.search(res.text)

        app_token = match.group(1)
        hello_url = self.API_HELLO.format(self.base_url)

        if self._uuid:
            __uuid = self._uuid
        else:
            __uuid = str(uuid.uuid4())
            self._session_attributes.set('uuid', __uuid, expires=3600 * 24)

        params = {
            'client_app_token': app_token,
            'uuid': __uuid,
            'lang': 'en',
            'format': 'json'
        }
        res = http.post(hello_url, headers=self.headers, data=params)
        return res

    def _login(self, email, password, _hello):
        self.logger.debug('_login ... Attempting login as {0}'.format(email))

        login_url = self.API_LOGIN.format(self.base_url)

        params = {
            'login': email,
            'password': password,
            'remember': 'true'
        }

        res = http.post(login_url, headers=self.headers, data=params, cookies=_hello.cookies)
        data = http.json(res)

        self._authed = data['success']
        if self._authed:
            self.logger.debug('New Session Data')
            self._session_attributes.set('beaker.session.id', res.cookies.get('beaker.session.id'), expires=3600 * 24)
            self._session_attributes.set('pzuid', res.cookies.get('pzuid'), expires=3600 * 24)
            self._session_attributes.set('power_guide_hash', data['session']['power_guide_hash'], expires=3600 * 24)
            return self._authed
        else:
            return None

    def _watch(self):
        self.logger.debug('_watch ...')
        match = self._url_re.match(self.url)
        if not match:
            self.logger.debug('_watch ... no match')
            return
        channel = match.group('channel')
        vod_id = match.group('vod_id')
        recording_id = match.group('recording_id')

        cookies = {
            'beaker.session.id': self._session_attributes.get('beaker.session.id'),
            'pzuid': self._session_attributes.get('pzuid')
        }

        watch_url = []
        if channel:
            params, watch_url = self._watch_live(channel, cookies)
        elif vod_id:
            params, watch_url = self._watch_vod(vod_id)
        elif recording_id:
            params, watch_url = self._watch_recording(recording_id)

        if not watch_url:
            self.logger.debug('Missing watch_url')
            return

        res = []
        try:
            res = http.post(watch_url, headers=self.headers, data=params, cookies=cookies)
        except Exception as e:
            if '404 Client Error' in str(e):
                self.logger.error(
                    'Unfortunately streaming is not permitted in this country or this channel does not exist.')
            elif '402 Client Error: Payment Required' in str(e):
                self.logger.error('Paid subscription required for this channel.')
                self.logger.info('If paid subscription exist, use --zattoo-purge-credentials to start a new session.')
            else:
                self.logger.error(str(e))
            return

        self.logger.debug('Found post data')
        data = http.json(res)

        if data['success']:
            for hls_url in data['stream']['watch_urls']:
                for s in HLSStream.parse_variant_playlist(self.session, hls_url['url']).items():
                    yield s

    def _watch_live(self, channel, cookies):
        self.logger.debug('_watch_live ... Channel: {0}'.format(channel))
        watch_url = self.API_WATCH.format(self.base_url)

        channels_url = self.API_CHANNELS.format(self.base_url, self._session_attributes.get('power_guide_hash'))
        res = http.get(channels_url, headers=self.headers, cookies=cookies)
        data = http.json(res, schema=self._channels_schema)

        c_list = []
        for d in data:
            for c in d['channels']:
                c_list.append(c)

        cid = []
        zattoo_list = []
        for c in c_list:
            zattoo_list.append(c['display_alias'])
            if c['display_alias'] == channel:
                cid = c['cid']

        self.logger.debug('Available zattoo channels in this country: {0}'.format(', '.join(sorted(zattoo_list))))

        if not cid:
            cid = channel

        self.logger.debug('CHANNEL ID: {0}'.format(cid))

        params = {
            'cid': cid,
            'https_watch_urls': True,
            'stream_type': 'hls'
        }
        return params, watch_url

    def _watch_recording(self, recording_id):
        self.logger.debug('_watch_recording ...')
        watch_url = self.API_WATCH_REC.format(self.base_url, recording_id)
        params = {
            'https_watch_urls': True,
            'stream_type': 'hls'
        }
        return params, watch_url

    def _watch_vod(self, vod_id):
        self.logger.debug('_watch_vod ...')
        watch_url = self.API_WATCH_VOD.format(self.base_url, vod_id)
        params = {
            'https_watch_urls': True,
            'stream_type': 'hls'
        }
        return params, watch_url

    def _get_streams(self):
        email = self.get_option('email')
        password = self.get_option('password')

        if self.options.get('purge_credentials'):
            self._session_attributes.set('beaker.session.id', None, expires=0)
            self._session_attributes.set('expires', None, expires=0)
            self._session_attributes.set('power_guide_hash', None, expires=0)
            self._session_attributes.set('pzuid', None, expires=0)
            self._session_attributes.set('uuid', None, expires=0)
            self._authed = False
            self.logger.info('All credentials were successfully removed.')

        if not self._authed and (not email and not password):
            self.logger.error(
                'A login for Zattoo is required, use --zattoo-email EMAIL --zattoo-password PASSWORD to set them')
            return

        if self._authed:
            if self._expires < time.time():
                # login after 24h
                expires = time.time() + 3600 * 24
                self._session_attributes.set('expires', expires, expires=3600 * 24)
                self._authed = False

        if not self._authed:
            __hello = self._hello()
            if not self._login(email, password, __hello):
                self.logger.error('Failed to login, check your username/password')
                return

        return self._watch()


__plugin__ = Zattoo
