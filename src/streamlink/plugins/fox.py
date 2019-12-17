import re

from urllib.parse import unquote
from json import loads

from streamlink.plugin import Plugin
from streamlink.plugin import PluginError
from streamlink.stream import HLSStream


class FOX(Plugin):
    url_re = re.compile(r'''
        https?://(?:www\.)?fox\.com/live/channel/
        (?P<slug>
            (W|K)[A-Z-]+|FS1|FS2|FNC|FBN|BTN|FSP|FOXDEP
        )
        $
    ''', flags=re.VERBOSE | re.IGNORECASE)

    api_url = 'https://api3.fox.com/v2.0/screens/live'

    @classmethod
    def can_handle_url(cls, url):
        url_match = cls.url_re.match(url) is not None
        return url_match

    def get_headers(self):
        bundle = self.session.http.get('https://www.fox.com/bundle.js').content.decode()
        x_api_key = re.findall(r'\{desktop:"([^"]+)"', bundle)[0]  # x-api-key always the same?
        
        mvpd_auth = None
        segment_device_id = None

        if 'mvpd-auth' in self.session.http.cookies:
            mvpd_auth = self.session.http.cookies['mvpd-auth']

        if 'segment-device-id' in self.session.http.cookies:
            segment_device_id = self.session.http.cookies['segment-device-id']

        if not mvpd_auth or not segment_device_id:
            self.logger.error("Login cookie(s) missing. Provide 'mvpd-auth' and 'segment-device-id' cookies with --http-cookie.")
            return

        access_token = loads(unquote(mvpd_auth))['accessToken']

        headers = {
            'x-api-key': x_api_key,
            'Authorization': 'Bearer %s' % access_token,
            'x-dcg-udid': segment_device_id,
        }

        return headers

    def _get_streams(self):
        slug = self.url_re.match(self.url)['slug'].upper()
        headers = self.get_headers()

        res1 = self.session.http.get(self.api_url, headers=headers)
        channels = res1.json()['panels']['member']
        channel_match = next(filter(lambda channel: channel['callSign'] == slug, channels), None)

        if not channel_match:
            self.logger.error('Callsign %s not found in channel listing. This is most likely a typo or a regional channel that is not available in your location.' % slug)
            return

        channel_index = channels.index(channel_match)

        # value doesn't matter as long as it is in range
        # different values give different links with same stream content
        # keep above zero in case current show has ended
        program_index = 1

        epg_listing_url = channels[channel_index]['items']['member'][program_index]['@id']
        epg_listing_res = self.session.http.get(epg_listing_url, headers=headers)

        live_player_url = epg_listing_res.json()['livePlayerScreenUrl']

        try:
            live_player_res = self.session.http.get(live_player_url, headers=headers) # 403 error here if channel is not included in cable subscription

        except PluginError as ex:
            if ex.err.response.status_code == 403:  # pylint: disable=no-member
                self.logger.error("Error 403: Forbidden. This is most likely because your cable subscription does not have access to this channel.")
            raise ex

        the_platform_url = live_player_res.json()['url']
        the_platform_res = self.session.http.get(the_platform_url)

        stream_url = the_platform_res.json()['playURL']
        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = FOX
