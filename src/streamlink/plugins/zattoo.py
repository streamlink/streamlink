import logging
import re
import uuid

from requests.cookies import cookiejar_from_dict

from streamlink import PluginError
from streamlink.cache import Cache
from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import useragents, validate
from streamlink.stream import DASHStream, HLSStream
from streamlink.utils.args import comma_list_filter

log = logging.getLogger(__name__)


class Zattoo(Plugin):
    API_CHANNELS = '{0}/zapi/v2/cached/channels/{1}?details=False'
    API_HELLO = '{0}/zapi/session/hello'
    API_HELLO_V2 = '{0}/zapi/v2/session/hello'
    API_HELLO_V3 = '{0}/zapi/v3/session/hello'
    API_LOGIN = '{0}/zapi/v2/account/login'
    API_LOGIN_V3 = '{0}/zapi/v3/account/login'
    API_SESSION = '{0}/zapi/v2/session'
    API_WATCH = '{0}/zapi/watch'
    API_WATCH_REC = '{0}/zapi/watch/recording/{1}'
    API_WATCH_VOD = '{0}/zapi/avod/videos/{1}/watch'

    STREAMS_ZATTOO = ['dash', 'hls', 'hls5']

    TIME_CONTROL = 60 * 60 * 2
    TIME_SESSION = 60 * 60 * 24 * 30

    _url_re = re.compile(r'''(?x)
        https?://
        (?P<base_url>
            (?:(?:
                iptv\.glattvision|www\.(?:myvisiontv|saktv|vtxtv)
            )\.ch
            )|(?:(?:
                mobiltv\.quickline|www\.quantum-tv|zattoo
            )\.com
            )|(?:(?:
                tvonline\.ewe|nettv\.netcologne|tvplus\.m-net
            )\.de
            )|(?:(?:
                player\.waly|www\.(?:1und1|netplus)
            )\.tv)
            |www\.bbv-tv\.net
            |www\.meinewelt\.cc
        )/
        (?:
            (?:
                recording(?:s\?recording=|/)
                |
                (?:ondemand/)?(?:watch/(?:[^/\s]+)(?:/[^/]+/))
            )(?P<recording_id>\d+)
            |
            (?:
                (?:live/|watch/)|(?:channels(?:/\w+)?|guide)\?channel=
            )(?P<channel>[^/\s]+)
            |
            ondemand(?:\?video=|/watch/)(?P<vod_id>[^-]+)
        )
        ''')

    _app_token_re = re.compile(r"""window\.appToken\s+=\s+'([^']+)'""")

    _channels_schema = validate.Schema({
        'success': bool,
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

    _session_schema = validate.Schema({
        'success': bool,
        'session': {
            'loggedin': bool
        }
    }, validate.get('session'))

    arguments = PluginArguments(
        PluginArgument(
            "email",
            requires=["password"],
            metavar="EMAIL",
            help="""
            The email associated with your zattoo account,
            required to access any zattoo stream.
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
            """),
        PluginArgument(
            'stream-types',
            metavar='TYPES',
            type=comma_list_filter(STREAMS_ZATTOO),
            default=['hls'],
            help='''
            A comma-delimited list of stream types which should be used,
            the following types are allowed:

            - {0}

            Default is "hls".
            '''.format('\n            - '.join(STREAMS_ZATTOO))
        )
    )

    def __init__(self, url):
        super().__init__(url)
        self.domain = self._url_re.match(url).group('base_url')
        self._session_attributes = Cache(
            filename='plugin-cache.json',
            key_prefix='zattoo:attributes:{0}'.format(self.domain))
        self._uuid = self._session_attributes.get('uuid')
        self._authed = (self._session_attributes.get('power_guide_hash')
                        and self._uuid
                        and self.session.http.cookies.get('pzuid', domain=self.domain)
                        and self.session.http.cookies.get('beaker.session.id', domain=self.domain)
                        )
        self._session_control = self._session_attributes.get('session_control',
                                                             False)
        self.base_url = 'https://{0}'.format(self.domain)
        self.headers = {
            'User-Agent': useragents.CHROME,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self.base_url
        }

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _hello(self):
        log.debug('_hello ...')

        # a new session is required for the app_token
        self.session.http.cookies = cookiejar_from_dict({})
        if self.base_url == 'https://zattoo.com':
            app_token_url = 'https://zattoo.com/client/token-2fb69f883fea03d06c68c6e5f21ddaea.json'
        elif self.base_url == 'https://www.quantum-tv.com':
            app_token_url = 'https://www.quantum-tv.com/token-4d0d61d4ce0bf8d9982171f349d19f34.json'
        else:
            app_token_url = self.base_url

        res = self.session.http.get(app_token_url)
        if self.base_url == 'https://www.quantum-tv.com':
            app_token = self.session.http.json(res)["session_token"]
            hello_url = self.API_HELLO_V3.format(self.base_url)
        elif self.base_url == 'https://zattoo.com':
            app_token = self.session.http.json(res)['app_tid']
            hello_url = self.API_HELLO_V2.format(self.base_url)
        else:
            match = self._app_token_re.search(res.text)
            app_token = match.group(1)
            hello_url = self.API_HELLO.format(self.base_url)

        if self._uuid:
            __uuid = self._uuid
        else:
            __uuid = str(uuid.uuid4())
            self._session_attributes.set(
                'uuid', __uuid, expires=self.TIME_SESSION)

        if self.base_url == 'https://zattoo.com':
            params = {
                'uuid': __uuid,
                'app_tid': app_token,
                'app_version': '1.0.0'
            }
        else:
            params = {
                'client_app_token': app_token,
                'uuid': __uuid,
            }

        if self.base_url == 'https://www.quantum-tv.com':
            params['app_version'] = '3.2028.3'
        else:
            params['lang'] = 'en'
            params['format'] = 'json'

        res = self.session.http.post(hello_url, headers=self.headers, data=params)

    def _login(self, email, password):
        log.debug('_login ... Attempting login as {0}'.format(email))

        params = {
            'login': email,
            'password': password,
            'remember': 'true'
        }

        if self.base_url == 'https://quantum-tv.com':
            login_url = self.API_LOGIN_V3.format(self.base_url)
        else:
            login_url = self.API_LOGIN.format(self.base_url)

        try:
            res = self.session.http.post(login_url, headers=self.headers, data=params)
        except Exception as e:
            if '400 Client Error' in str(e):
                raise PluginError(
                    'Failed to login, check your username/password')
            raise e

        data = self.session.http.json(res)
        self._authed = data['success']
        log.debug('New Session Data')
        self.save_cookies(default_expires=self.TIME_SESSION)
        self._session_attributes.set('power_guide_hash',
                                     data['session']['power_guide_hash'],
                                     expires=self.TIME_SESSION)
        self._session_attributes.set(
            'session_control', True, expires=self.TIME_CONTROL)

    def _watch(self):
        log.debug('_watch ...')
        match = self._url_re.match(self.url)
        if not match:
            log.debug('_watch ... no match')
            return
        channel = match.group('channel')
        vod_id = match.group('vod_id')
        recording_id = match.group('recording_id')

        params = {'https_watch_urls': True}
        if channel:
            watch_url = self.API_WATCH.format(self.base_url)
            params_cid = self._get_params_cid(channel)
            if not params_cid:
                return
            params.update(params_cid)
        elif vod_id:
            log.debug('Found vod_id: {0}'.format(vod_id))
            watch_url = self.API_WATCH_VOD.format(self.base_url, vod_id)
        elif recording_id:
            log.debug('Found recording_id: {0}'.format(recording_id))
            watch_url = self.API_WATCH_REC.format(self.base_url, recording_id)
        else:
            log.debug('Missing watch_url')
            return

        zattoo_stream_types = self.get_option('stream-types') or ['hls']
        for stream_type in zattoo_stream_types:
            params_stream_type = {'stream_type': stream_type}
            params.update(params_stream_type)

            try:
                res = self.session.http.post(watch_url, headers=self.headers, data=params)
            except Exception as e:
                if '404 Client Error' in str(e):
                    log.error('Unfortunately streaming is not permitted in '
                              'this country or this channel does not exist.')
                elif '402 Client Error: Payment Required' in str(e):
                    log.error('Paid subscription required for this channel.')
                    log.info('If paid subscription exist, use --zattoo-purge'
                             '-credentials to start a new session.')
                elif '403 Client Error' in str(e):
                    log.debug('Force session reset for watch_url')
                    self.reset_session()
                else:
                    log.error(str(e))
                return

            data = self.session.http.json(res)
            log.debug('Found data for {0}'.format(stream_type))
            if data['success'] and stream_type in ['hls', 'hls5']:
                for url in data['stream']['watch_urls']:
                    yield from HLSStream.parse_variant_playlist(self.session, url['url']).items()
            elif data['success'] and stream_type == 'dash':
                for url in data['stream']['watch_urls']:
                    yield from DASHStream.parse_manifest(self.session, url['url']).items()

    def _get_params_cid(self, channel):
        log.debug('get channel ID for {0}'.format(channel))

        channels_url = self.API_CHANNELS.format(
            self.base_url,
            self._session_attributes.get('power_guide_hash'))

        try:
            res = self.session.http.get(channels_url, headers=self.headers)
        except Exception:
            log.debug('Force session reset for _get_params_cid')
            self.reset_session()
            return False

        data = self.session.http.json(res, schema=self._channels_schema)

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

        log.debug('Available zattoo channels in this country: {0}'.format(
            ', '.join(sorted(zattoo_list))))

        if not cid:
            cid = channel

        log.debug('CHANNEL ID: {0}'.format(cid))

        return {'cid': cid}

    def reset_session(self):
        self._session_attributes.set('power_guide_hash', None, expires=0)
        self._session_attributes.set('uuid', None, expires=0)
        self.clear_cookies()
        self._authed = False

    def _get_streams(self):
        email = self.get_option('email')
        password = self.get_option('password')

        if self.options.get('purge_credentials'):
            self.reset_session()
            log.info('All credentials were successfully removed.')
        elif (self._authed and not self._session_control):
            # check every two hours, if the session is actually valid
            log.debug('Session control for {0}'.format(self.domain))
            res = self.session.http.get(self.API_SESSION.format(self.base_url))
            res = self.session.http.json(res, schema=self._session_schema)
            if res['loggedin']:
                self._session_attributes.set(
                    'session_control', True, expires=self.TIME_CONTROL)
            else:
                log.debug('User is not logged in')
                self._authed = False

        if not self._authed and (not email and not password):
            log.error(
                'A login for Zattoo is required, use --zattoo-email EMAIL'
                ' --zattoo-password PASSWORD to set them')
            return

        if not self._authed:
            self._hello()
            self._login(email, password)

        return self._watch()


__plugin__ = Zattoo
