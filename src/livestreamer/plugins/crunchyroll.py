import requests
import string
import random
import datetime

from livestreamer import utils, options, plugin, exceptions, stream

API_URL = 'https://api.crunchyroll.com/{0}.0.json'
API_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (PLAYSTATION 3; 4.46)',
    'Host': 'api.crunchyroll.com',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Content-Type': 'application/x-www-form-urlencoded'
}
API_VERSION = '1.0.1'
API_LOCALE = 'enUS'
API_ACCESS_TOKEN = 'S7zg3vKx6tRZ0Sf'
API_DEVICE_TYPE = 'com.crunchyroll.ps3'


def parse_timestamp(ts):
    '''Takes ISO 8601 format(string) and converts into a utc datetime(naive)'''
    dt = datetime.datetime.strptime(ts[:-7], '%Y-%m-%dT%H:%M:%S') +\
        datetime.timedelta(hours=int(ts[-5:-3]), minutes=int(ts[-2:])) *\
        int(ts[-6:-5] + '1')

    return dt


class APIError(Exception):
    '''Exception throw by the CrunchyrollAPI when an error occurs'''
    pass


class CrunchyrollAPI(object):
    def __init__(self, session_id=None, auth=None):
        '''Abstract the API to access to Crunchyroll data.
        Can take saved credentials to use on it's calls to the API.
        '''
        self.session_id = session_id
        self.auth = auth
        self.session = requests.session()
        self.session.headers = API_HEADERS

    def _api_call(self, entrypoint, params):
        '''Makes a call against the api.
        :param entrypoint: API method to call.
        :param params: parameters to include in the request data.
        '''
        url = API_URL.format(entrypoint)

        # default params
        params.update({
            'version': API_VERSION,
            'locale': API_LOCALE,
        })

        if self.session_id:
            params['session_id'] = self.session_id

        response = utils.urlget(url, params=params, session=self.session)
        json_response = utils.res_json(response)

        if json_response['error']:
            raise APIError(json_response['message'])

        return json_response

    def start_session(self, device_id):
        '''Starts a session against Crunchyroll's server.
        Is recommended that you call this method before making any other calls
        to make sure you have a valid session against the server.
        '''
        params = {
            'device_id': device_id,
            'device_type': API_DEVICE_TYPE,
            'access_token': API_ACCESS_TOKEN,
        }

        if self.auth:
            params['auth'] = self.auth

        response = self._api_call('start_session', params)
        self.session_id = response['data']['session_id']

        return datetime.datetime.utcnow() + datetime.timedelta(hours=4)

    def login(self, username, password):
        '''Authenticates the session to be able to access restricted data from
        the server (e.g. premium restricted videos).
        '''
        params = {
            'account': username,
            'password': password
        }

        response = self._api_call('login', params)
        self.auth = response['data']['auth']

        return parse_timestamp(response['data']['expires'])

    def get_info(self, media_id, fields=None):
        '''Returns the data for a certain media item.

        :param media_id: id that identifies the media item to be accessed.
        :param fields: list of the media's field to be returned. By default the
        API returns some fields, but others are not returned unless they are
        explicity asked for. I have no real documentation on the fields, but
        they all seem to start with the 'media.' prefix (e.g. media.name,
        media.stream_data).
        '''
        params = {
            'media_id': media_id
        }

        if fields:
            params['fields'] = ','.join(fields)

        response = self._api_call('info', params)

        return response['data']


class Crunchyroll(plugin.Plugin):

    options = options.Options({
        'username': None,
        'password': None,
        'purge_credentials': None,
    })

    WEIGHTS = {
        'low': 240,
        'mid': 420,
        'high': 720,
        'ultra': 1080,
    }

    @classmethod
    def can_handle_url(self, url):
        return 'crunchyroll.com' in url

    @classmethod
    def stream_weight(cls, key):
        weight = cls.WEIGHTS.get(key)

        if weight:
            return weight, "crunchyroll"

        return plugin.Plugin.stream_weight(key)

    def _get_streams(self):
        # create a new api
        api = self._create_api()

        try:
            # parse the media id from the url
            media_id = int(self.url.split('/')[-1].split('-')[-1])
        except ValueError:
            raise exceptions.PluginError('Invalid url')

        try:
            # try to obtain the info on streams for this media item
            stream_data = api.get_info(
                media_id, fields=['media.stream_data']
            )['stream_data']
        except APIError as e:
            raise exceptions.PluginError(
                'Media lookup error: {0}'.format(e.message))

        if stream_data:
            streams_raw = stream_data['streams']
        else:
            raise exceptions.NoStreamsError(self.url)

        # convert the raw stream data into the stream list expected by
        # livestreamer (adaptive get's filtered since it isn't supported)
        streams = dict(
            (s['quality'], stream.HLSStream(self.session, s['url']))
            for s in streams_raw
            if s['quality'] != 'adaptive'
        )

        return streams

    def _get_device_id(self):
        '''Returns the saved device id or creates a new one an saves it'''
        device_id = self.cache.get('device_id')

        if not device_id:
            # create a random device id
            char_set = string.ascii_letters + string.digits
            device_id = ''.join(random.sample(char_set, 32))
            self.cache.set('device_id', device_id, 31536000)

        return device_id

    def _create_api(self):
        '''Creates a new CrunchyrollAPI object, initiates it's session and
        tries to authenticate it either by using saved credentials or the
        user's username and password.
        '''
        if self.options.get('purge_credentials'):
            self.cache.set('session_id', None, 0)
            self.cache.set('auth', None, 0)

        current_time = datetime.datetime.utcnow()
        api = CrunchyrollAPI(
            self.cache.get('session_id'), self.cache.get('auth'))

        self.logger.debug('Creating session...')
        try:
            expires = api.start_session(self._get_device_id())
        except APIError as e:
            if e.message == 'Unauthenticated request':
                self.logger.info('Aparently credentials got debunked')
                api = CrunchyrollAPI()
                expires = api.start_session(self._get_device_id())
            else:
                raise e

        self.cache.set(
            'session_id',
            api.session_id,
            (expires - current_time).total_seconds()
        )
        self.logger.debug('Success!')

        if api.auth:
            self.logger.info('Using saved credentials')
        elif self.options.get('username'):
            try:
                self.logger.info(
                    'Trying to login using user and password...')
                expires = api.login(
                    self.options.get('username'),
                    self.options.get('password')
                )
                self.cache.set(
                    'auth',
                    api.auth,
                    (expires - current_time).total_seconds()
                )

                self.logger.info('Success!')
            except APIError as e:
                raise exceptions.PluginError(
                    'Authentication error: {0}'.format(e.message))
        else:
            self.logger.warning(
                "No authentication provided, you won't be able to access "
                "premium restricted content"
            )

        return api


__plugin__ = Crunchyroll
