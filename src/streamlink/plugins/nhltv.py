# -*- coding: utf-8 -*-

import base64
import logging
import re
import time

import requests.cookies

from streamlink.plugin import Plugin, PluginArgument, PluginArguments, PluginError
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


NHL_TEAMS = {
    'ANA': 'Anaheim Ducks',
    'ARI': 'Arizona Coyotes',
    'BOS': 'Boston Bruins',
    'BUF': 'Buffalo Sabres',
    'CAR': 'Carolina Hurricanes',
    'CBJ': 'Columbus Blue Jackets',
    'CGY': 'Calgary Flames',
    'COL': 'Colorado Avalanche',
    'CHI': 'Chicago Blackhawks',
    'DAL': 'Dallas Stars',
    'DET': 'Detroit Red Wings',
    'EDM': 'Edmonton Oilers',
    'FLA': 'Florida Panthers',
    'LAK': 'Los Angeles Kings',
    'MIN': 'Minnesota Wild',
    'MTL': 'Montreal Canadiens',
    'NJD': 'New Jersey Devils',
    'NSH': 'Nashville Predators',
    'NYI': 'New York Islanders',
    'NYR': 'New York Rangers',
    'OTT': 'Ottawa Senators',
    'PHI': 'Philadelphia Flyers',
    'PIT': 'Pittsburgh Penguins',
    'SJS': 'San Jose Sharks',
    'STL': 'St Louis Blues',
    'TBL': 'Tampa Bay Lightning',
    'TOR': 'Toronto Maple Leafs',
    'VAN': 'Vancouver Canucks',
    'VGK': 'Vegas Golden Knights',
    'WPG': 'Winnipeg Jets',
    'WSH': 'Washington Capitals',
}


_URL_RE = re.compile(r'https://www.nhl.com/tv/(?P<game_pk>\d+)')
_STATS_API_URL = 'https://statsapi.web.nhl.com/api/v1'
_MEDIA_API_URL = 'https://mf.svc.nhl.com/ws/media/mf/v2.4'
_LOGIN_URL = 'https://gateway.web.nhl.com/ws/subscription/flow/nhlPurchase.login'
_OAUTH_URL = 'https://user.svc.nhl.com/oauth/token'
_NHL_WEBAPP_VER = b'web_nhl-v1.0.0:2d1d846ea3b194a18ef40ac9fbce97e3'


def now_ms():
    return int(round(time.time() * 1000))


class NHLTV(Plugin):

    NATIONAL_WEIGHT = 4
    HOME_WEIGHT = 3
    AWAY_WEIGHT = 2
    FRENCH_WEIGHT = 1

    arguments = PluginArguments(
        PluginArgument(
            'email',
            required=True,
            metavar='EMAIL',
            requires=['password'],
            help='The email associated with your NHL.tv (NHL.com) account.'
        ),
        PluginArgument(
            'password',
            sensitive=True,
            metavar='PASSWORD',
            help='An NHL.tv account password to use with --nhltv-email.'
        ),
        PluginArgument(
            'purge-credentials',
            action='store_true',
            help='Purge cached NHL.tv credentials to initiate a new session and reauthenticate.'
        ),
        PluginArgument(
            'prefer-french',
            action='store_true',
            help='''
            Prefer French language broadcasts. If this option is specified, the highest quality
            French language broadcast will be set as "best" quality whenever it is available.
            This option takes precedence over --nhltv-prefer-team.
            '''
        ),
        PluginArgument(
            'prefer-team',
            metavar='TEAM_ABBR',
            help='''
            3-letter abbreviation for your preferred NHL team. If this option is specified, the
            highest quality home/away broadcast for the specified team will be set as "best" quality
            whenever it is available.
            ''',
        ),
    )

    def __init__(self, url):
        super(NHLTV, self).__init__(url)
        self.session.http.headers.update({
            'Origin': 'https://www.nhl.com',
            'Referer': self.url,
            'User-Agent': useragents.CHROME,
        })
        match = _URL_RE.match(url).groupdict()
        self.game_pk = match.get('game_pk')
        self.prefer_team = None

    @classmethod
    def can_handle_url(cls, url):
        return _URL_RE.match(url) is not None

    @classmethod
    def stream_weight(cls, key):
        # NHL.tv may provide any combination of broadcasts depending on the game.
        # Prioritize national > home > away > french > multicam for best quality synonym
        try:
            (name, quality) = key.split('_')
            if quality == 'audio':
                # radio feeds are all 48k audio
                weight = 48
            else:
                weight = int(quality.rstrip('p'))
            if key.startswith('national'):
                weight += cls.NATIONAL_WEIGHT
            elif key.startswith('home'):
                weight += cls.HOME_WEIGHT
            elif key.startswith('away'):
                weight += cls.AWAY_WEIGHT
            elif key.startswith('french'):
                weight += cls.FRENCH_WEIGHT
            return weight, "nhltv"
        except ValueError:
            pass

        return Plugin.stream_weight(key)

    @property
    def _authed(self):
        cookies = self.session.http.cookies
        return (cookies.get('nhl_username') and cookies.get('Authorization'))

    @property
    def _session_key(self):
        return self.cache.get('session_key')

    @property
    def _auth_token(self):
        return self.session.http.cookies.get('Authorization')

    @property
    def _media_auth(self):
        return self.session.http.cookies.get('mediaAuth_v2')

    def _login(self, email, password):
        auth = 'Basic {}'.format(base64.urlsafe_b64encode(_NHL_WEBAPP_VER).decode('ascii'))
        headers = {
            'Referer': 'https://www.nhl.com/login?forwardUrl=https://www.nhl.com/tv',
            'Authorization': auth,
        }
        params = {'grant_type': 'client_credentials'}
        r = self.session.http.post(_OAUTH_URL, params=params, headers=headers)
        token = r.json().get('access_token')
        if not token:
            raise PluginError('Could not obtain oauth token')
        headers['Authorization'] = token
        data = {'nhlCredentials': {'email': email, 'password': password}}
        self.session.http.post(_LOGIN_URL, headers=headers, json=data)
        log.info('Successfully logged in as {}'.format(email))
        self.save_cookies()
        self.cache.set('session_key', None)

    def _get_feeds(self):
        """Get list of broadcast feeds for this game from the NHL schedule API."""
        url = '{}/schedule'.format(_STATS_API_URL)
        params = {
            'gamePk': self.game_pk,
            'expand': ['schedule.game.content.media.epg', 'schedule.teams'],
        }
        headers = {'Accept': 'application/json'}
        json = self.session.http.get(url, params=params, headers=headers).json()
        feeds = []
        for date in json.get('dates', []):
            for game in date.get('games', []):
                media = game.get('content', {}).get('media')
                for epg in media.get('epg', []):
                    title = epg.get('title')
                    if title in ('NHLTV', 'Audio'):
                        for item in epg.get('items', []):
                            media_state = item.get('mediaState')
                            if title == 'Audio' and media_state != 'MEDIA_ON':
                                # Radio broadcast feeds are only available for live games.
                                # We can skip them here for archived game VODs even though
                                # they are still returned by the API
                                continue
                            call_letters = item.get('callLetters', '')
                            feed_name = item.get('feedName', '')
                            feed_type = item.get('mediaFeedType', '').lower()
                            if feed_type in ('home', 'away'):
                                team = game.get('teams', {}).get(feed_type, {}).get('team', {})
                                abbr = team.get('abbreviation')
                                feed_name = '-'.join([abbr, call_letters])
                                if abbr == self.prefer_team:
                                    if feed_type == 'home':
                                        self.__class__.HOME_WEIGHT = 5
                                    else:
                                        self.__class__.AWAY_WEIGHT = 5
                            elif feed_type in ('national', 'french'):
                                feed_name = call_letters
                            audio_only = False
                            if title == 'Audio':
                                audio_only = True
                                broadcast_type = 'radio'
                            elif title == 'NHLTV':
                                broadcast_type = 'NHL.tv'
                            else:
                                broadcast_type = title
                            log.info('Found {} {} broadcast feed ({})'.format(feed_type, broadcast_type, feed_name))
                            feeds.append((item, audio_only))
        return feeds

    def _get_session_key(self, event_id):
        url = '{}/stream'.format(_MEDIA_API_URL)
        params = {
            'eventId': event_id,
            'format': 'json',
            'platform': 'WEB_MEDIAPLAYER',
            'subject': 'NHLTV',
            '_': now_ms(),
        }
        headers = {
            'Accept': 'application/json',
            'Authorization': self._auth_token,
        }
        json = self.session.http.get(url, params=params, headers=headers).json()
        session_key = json.get('session_key')
        if not session_key:
            status = json.get('status_code')
            if status == -3500:
                log.debug('Plugin is being rate-limited for making too many session key requests.')
            raise PluginError('Could not obtain session key: {}'.format(json.get('status_message')))
        # This session key is normally supposed to last for a single browser session.
        # If we repeatedly request new session keys we will get rate limited by the NHL.tv backend,
        # so we cache session keys for 2.5 hours (roughly the length of an NHL hockey game) to
        # aproximate normal behavior.
        self.cache.set('session_key', session_key, 9000)

    def _get_streams_for_feed(self, feed, audio_only=False):
        """Get HLS streams for the specified broadcast feed."""
        event_id = feed.get('eventId')
        content_id = feed.get('mediaPlaybackId')
        feed_type = feed.get('mediaFeedType')
        streams = {}
        if not self._session_key:
            self._get_session_key(event_id)
        url = '{}/stream'.format(_MEDIA_API_URL)
        if audio_only:
            scenario = 'HTTP_CLOUD_AUDIO'
        else:
            scenario = 'HTTP_CLOUD_WIRED_60_ADS'
        params = {
            'contentId': content_id,
            'playbackScenario': scenario,
            'sessionKey': self._session_key,
            'auth': 'response',
            'format': 'json',
            'platform': 'WEB_MEDIAPLAYER',
            'subject': 'NHLTV',
            '_': now_ms(),
        }
        headers = {
            'Accept': 'application/json',
            'Authorization': self._auth_token,
        }
        json = self.session.http.get(url, params=params, headers=headers).json()
        if json.get('status_code') != 1:
            log.debug('Could not get streams for {}/{}: {}'.format(event_id, content_id, json.get('status_message')))
            return streams
        for attr in json.get('session_info', {}).get('sessionAttributes', []):
            name = attr.get('attributeName')
            if name == 'mediaAuth_v2':
                auth = attr.get('attributeValue', '')
                if self._media_auth != auth:
                    cookie = requests.cookies.create_cookie(name, auth, domain='.nhl.com')
                    self.session.http.cookies.set_cookie(cookie)
        for event in json.get('user_verified_event', []):
            for content in event.get('user_verified_content', []):
                for media in content.get('user_verified_media_item', {}):
                    if media.get('auth_status') != 'SuccessStatus':
                        msg = ('Your account is not authorized to view this content.'
                               ' Accounts without an active NHL.tv subscription can only view'
                               ' designated free games. Please refer to NHL.com to see a schedule'
                               ' of upcoming free games.')
                        raise PluginError(msg)
                    if media.get('blackout_status', {}).get('status') != 'SuccessStatus':
                        msg = ('This content is unavailable in your region due to NHL blackout restrictions.'
                               ' For more information visit: https://www.nhl.com/info/nhltv-blackout-detector')
                        raise PluginError(msg)
                    url = media.get('url')
                    if url:
                        prefix = '{}_'.format(feed_type.lower())
                        if audio_only:
                            name_fmt = 'audio'
                        else:
                            name_fmt = None
                        streams.update(
                            HLSStream.parse_variant_playlist(self.session, url, name_prefix=prefix, name_fmt=name_fmt))
        return streams

    def _get_streams(self):
        streams = {}
        if self._authed and not self.options.get('purge_credentials'):
            log.info('Using cached credentials')
            if self._session_key:
                log.debug('Using cached session key')
        else:
            self.clear_cookies()
            self._login(self.options.get('email'), self.options.get('password'))

        if self.options.get('prefer_french'):
            log.info('French language broadcast will be preferred when it is available.')
            self.__class__.FRENCH_WEIGHT = 10
        prefer_team = self.options.get('prefer_team')
        if prefer_team:
            prefer_team = prefer_team.upper()
            if prefer_team in NHL_TEAMS:
                team = NHL_TEAMS[prefer_team]
                log.info('{} home/away broadcast will be preferred when it is available.'.format(team))
                self.prefer_team = prefer_team
            else:
                log.info('Unknown team {}. Valid choices for --nhltv-prefer-team are:'.format(prefer_team))
                log.info(', '.join(NHL_TEAMS.keys()))

        for feed, audio_only in self._get_feeds():
            streams.update(self._get_streams_for_feed(feed, audio_only))

        return streams


__plugin__ = NHLTV
