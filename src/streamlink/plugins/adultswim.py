import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class AdultSwim(Plugin):
    api_url = "https://api.adultswim.com/v1"
    hash = "b27de189d91c06d5646dc7faea49282b97a4a25247e0927aa9bec7dd74ab6c71"
    video_data_url = "https://www.adultswim.com/api/shows/v1/media/{0}/desktop"

    json_data_re = re.compile(
        '.*<script id="__NEXT_DATA__" type="application/json">'
        '({.*?}})'
        '</script>.*', re.S
    )

    url_re = re.compile(
        r"""https?://(?:www\.)?adultswim\.com
        (?:/(streams|videos))
        (?:/([^/]+))?
        (?:/([^/]+))?
        """, re.VERBOSE
    )

    _api_schema = validate.Schema({
        'data': {
            'show': {
                'collection': {
                    'video': {
                        'id': validate.text
                    }
                }
            }
        }
    })

    _video_data_schema = validate.Schema({
        'media': {
            'desktop': {
                'unprotected': {
                    'url': validate.url()
                }
            }
        }
    })

    _json_schema = validate.Schema({
        'props': {
            '__REDUX_STATE__': {
                'streams': [{
                    'id': validate.text,
                    'stream': validate.text
                }]
            }
        }
    })

    @classmethod
    def can_handle_url(cls, url):
        match = AdultSwim.url_re.match(url)
        return match is not None

    def _get_json_data(self, res_data, key):
        json_data = parse_json(
            self.json_data_re.match(res_data.text).group(1),
            schema=self._json_schema
        )

        for stream in json_data['props']['__REDUX_STATE__']['streams']:
            if key == stream['id']:
                return stream['stream']

    def _get_streams(self):
        url_match = self.url_re.match(self.url)
        url_type, show_name, episode_name = url_match.groups()

        if url_type == 'streams' and not show_name:
            url_type = 'live-stream'
        elif not show_name:
            return

        log.debug("URL type: {0}".format(url_type))

        if url_type == 'live-stream':
            res = self.session.http.get(self.url)
            video_id = self._get_json_data(res, url_type)
        elif url_type == 'streams':
            res = self.session.http.get(self.url)
            video_id = self._get_json_data(res, show_name)
        elif url_type == 'videos':
            if show_name is None or episode_name is None:
                return

            api_params = dict(
                operationName='ShowVideo',
                variables='{"show":"'
                          + show_name
                          + '","video":"'
                          + episode_name
                          + '"}',
                extensions='{"persistedQuery":{"version":1,"sha256Hash":'
                          + '"'
                          + self.hash
                          + '"'
                          + '}}'
            )

            res = self.session.http.get(self.api_url, params=api_params)
            try:
                api_res = self.session.http.json(res, schema=self._api_schema)
            except Exception:
                return
            video_id = api_res['data']['show']['collection']['video']['id']
        else:
            return

        log.debug("Video ID: {0}".format(video_id))

        res = self.session.http.get(self.video_data_url.format(video_id))
        data_res = self.session.http.json(res, schema=self._video_data_schema)
        m3u8_url = data_res['media']['desktop']['unprotected']['url']
        log.debug("URL = {0}".format(m3u8_url))

        return HLSStream.parse_variant_playlist(
            self.session, m3u8_url
        )


__plugin__ = AdultSwim
