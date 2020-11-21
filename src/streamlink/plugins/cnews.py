import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.utils import parse_json


class CNEWS(Plugin):
    _url_re = re.compile(r'https?://(?:www\.)?cnews\.fr')
    _json_data_re = re.compile(r'jQuery\.extend\(Drupal\.settings, ({.*})\);')
    _dailymotion_url = 'https://www.dailymotion.com/embed/video/{}'

    _data_schema = validate.Schema(
        validate.transform(_json_data_re.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(parse_json),
            {
                validate.optional('dm_player_live_dailymotion'): {
                    validate.optional('video_id'): str,
                },
                validate.optional('dm_player_node_dailymotion'): {
                    validate.optional('video_id'): str,
                },
            },
        )),
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        data = self.session.http.get(self.url, schema=self._data_schema)
        if 'dm_player_node_dailymotion' in data:
            return self.session.streams(self._dailymotion_url.format(
                data['dm_player_node_dailymotion']['video_id']))
        elif 'dm_player_live_dailymotion' in data:
            return self.session.streams(self._dailymotion_url.format(
                data['dm_player_live_dailymotion']['video_id']))


__plugin__ = CNEWS
