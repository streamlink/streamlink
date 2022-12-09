"""
$description Live TV channels from SBS, a South Korean public broadcaster.
$url play.sbs.co.kr
$type live
$region South Korea
"""

import logging
import random
import re

from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://play\.sbs\.co\.kr/onair/pc/index\.html'
))
@pluginargument(
    "id",
    metavar="CHANNELID",
    type=str.upper,
    help="""
        Channel ID to play.

        Example:

            %(prog)s http://play.sbs.co.kr/onair/pc/index.html best --sbscokr-id S01

    """,
)
class SBScokr(Plugin):
    api_channel = 'http://apis.sbs.co.kr/play-api/1.0/onair/channel/{0}'
    api_channels = 'http://static.apis.sbs.co.kr/play-api/1.0/onair/channels'

    _channels_schema = validate.Schema({
        'list': [{
            'channelname': validate.all(
                validate.text,
            ),
            'channelid': validate.text,
            validate.optional('type'): validate.text,
        }]},
        validate.get('list'),
    )

    _channel_schema = validate.Schema(
        {
            'onair': {
                'info': {
                    'onair_yn': validate.text,
                    'overseas_yn': validate.text,
                    'overseas_text': validate.text,
                },
                'source': {
                    'mediasourcelist': validate.any([{
                        validate.optional('default'): validate.text,
                        'mediaurl': validate.text,
                    }], [])
                },
            }
        },
        validate.get('onair'),
    )

    def _get_streams(self):
        user_channel_id = self.get_option('id')

        res = self.session.http.get(self.api_channels)
        res = self.session.http.json(res, schema=self._channels_schema)

        channels = {
            channel["channelid"]: channel["channelname"]
            for channel in sorted(res, key=lambda x: x["channelid"])
            if channel.get("type") in ("TV", "Radio")
        }

        log.info('Available IDs: {0}'.format(', '.join(
            '{0} ({1})'.format(key, value) for key, value in channels.items())))
        if not user_channel_id:
            log.error('No channel selected, use --sbscokr-id CHANNELID')
            return
        elif user_channel_id not in channels.keys():
            log.error('Channel ID "{0}" is not available.'.format(user_channel_id))
            return

        params = {
            'v_type': '2',
            'platform': 'pcweb',
            'protocol': 'hls',
            'jwt-token': '',
            'rnd': random.randint(50, 300)
        }

        res = self.session.http.get(self.api_channel.format(user_channel_id),
                                    params=params)
        res = self.session.http.json(res, schema=self._channel_schema)

        streams = []
        for media in res['source']['mediasourcelist']:
            if media['mediaurl']:
                streams.extend(HLSStream.parse_variant_playlist(self.session, media["mediaurl"]).items())
        if streams:
            return streams

        if res["info"]["onair_yn"] != "Y":
            log.error("This channel is currently unavailable")
        elif res["info"]["overseas_yn"] != "Y":
            log.error(res["info"]["overseas_text"])


__plugin__ = SBScokr
