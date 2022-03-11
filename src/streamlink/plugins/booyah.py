"""
$description Global live streaming and video hosting community platform designed for gaming enthusiasts.
$url booyah.live
$type live, vod
"""

import logging
import re
import sys

from streamlink.compat import urljoin
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?booyah\.live/(?:(?P<type>channels|clips|vods)/)?(?P<id>[^?]+)"
))
class Booyah(Plugin):
    auth_api_url = 'https://booyah.live/api/v3/auths/sessions'
    vod_api_url = 'https://booyah.live/api/v3/playbacks/{0}'
    live_api_url = 'https://booyah.live/api/v3/channels/{0}'
    streams_api_url = 'https://booyah.live/api/v3/channels/{0}/streams'

    auth_schema = validate.Schema({
        'expiry_time': int,
        'uid': int,
    })

    vod_schema = validate.Schema({
        'user': {
            'nickname': validate.text,
        },
        'playback': {
            'name': validate.text,
            'endpoint_list': [{
                'stream_url': validate.url(),
                'resolution': validate.all(
                    int,
                    validate.transform(lambda x: '{}p'.format(x)),
                ),
            }],
        },
    })

    live_schema = validate.Schema({
        'user': {
            'nickname': validate.text,
        },
        'channel': {
            'channel_id': int,
            'name': validate.text,
            'is_streaming': bool,
            validate.optional('hostee'): {
                'channel_id': int,
                'nickname': validate.text,
            },
        },
    })

    @classmethod
    def stream_weight(cls, stream):
        if stream == "source":
            return sys.maxsize, "source"
        return super(Booyah, cls).stream_weight(stream)

    def do_auth(self):
        res = self.session.http.post(self.auth_api_url)
        self.session.http.json(res, self.auth_schema)

    def get_vod(self, id):
        res = self.session.http.get(self.vod_api_url.format(id))
        user_data = self.session.http.json(res, schema=self.vod_schema)

        self.author = user_data['user']['nickname']
        self.category = 'VOD'
        self.title = user_data['playback']['name']

        for stream in user_data['playback']['endpoint_list']:
            if stream['stream_url'].endswith('.mp4'):
                yield stream['resolution'], HTTPStream(
                    self.session,
                    stream['stream_url'],
                )
            else:
                yield stream['resolution'], HLSStream(
                    self.session,
                    stream['stream_url'],
                )

    def get_live(self, id):
        res = self.session.http.get(self.live_api_url.format(id))
        user_data = self.session.http.json(res, schema=self.live_schema)

        if user_data['channel']['is_streaming']:
            self.category = 'Live'
            stream_id = user_data['channel']['channel_id']
        elif 'hostee' in user_data['channel']:
            self.category = 'Hosted by {}'.format(user_data["channel"]["hostee"]["nickname"])
            stream_id = user_data['channel']['hostee']['channel_id']
        else:
            log.info('User is offline')
            return

        self.author = user_data['user']['nickname']
        self.title = user_data['channel']['name']

        res = self.session.http.get(self.streams_api_url.format(stream_id))
        streams = self.session.http.json(res, schema=validate.Schema({
            "default_mirror": validate.text,
            "mirror_list": [{
                "name": validate.text,
                "url_domain": validate.url(),
            }],
            "source_stream_url_path": validate.text,
            "stream_addr_list": [{
                "resolution": validate.text,
                "url_path": validate.text,
            }],
        }))

        mirror = (
            next(filter(lambda item: item["name"] == streams["default_mirror"], streams["mirror_list"]), None)
            or next(iter(streams["mirror_list"]), None)
        )
        if not mirror:
            return

        auto = next(filter(lambda item: item["resolution"] == "Auto", streams["stream_addr_list"]), None)
        if auto:
            for s in HLSStream.parse_variant_playlist(self.session, urljoin(mirror["url_domain"], auto["url_path"])).items():
                yield s

        if streams["source_stream_url_path"]:
            yield "source", HLSStream(self.session, urljoin(mirror["url_domain"], streams["source_stream_url_path"]))

    def _get_streams(self):
        self.do_auth()

        url_data = self.match.groupdict()
        log.debug('ID={}'.format(url_data["id"]))

        if not url_data['type'] or url_data['type'] == 'channels':
            log.debug('Type=Live')
            return self.get_live(url_data['id'])
        else:
            log.debug('Type=VOD')
            return self.get_vod(url_data['id'])


__plugin__ = Booyah
