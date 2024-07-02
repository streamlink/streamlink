"""
$description Chinese live-streaming platform for live video game broadcasts and individual live streams.
$url douyin.com
$type live
$metadata id
$metadata author
$metadata title
"""

import logging
import re
from typing import Dict

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:live\.)?douyin\.com/(?P<room_id>[^/?]+)",
))
class Douyin(Plugin):
    QUALITY_WEIGHTS: Dict[str, int] = {}

    @classmethod
    def stream_weight(cls, key):
        weight = cls.QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, key

        return super().stream_weight(key)

    def _get_streams(self):
        room_id = self.match.group("room_id")
        try:
            data = self.session.http.get(
                f"https://live.douyin.com/webcast/room/web/enter/",
                params={
                    'web_rid': room_id,
                    'aid': '6383',
                    'device_platform': 'web',
                    'browser_language': 'zh-CN',
                    'browser_platform': 'Win32',
                    'browser_name': 'Chrome',
                    'browser_version': '92.0.4515.159',
                },
                schema=validate.Schema(
                    validate.parse_json(),
                    validate.get('data'),
                    validate.none_or_all({
                        'data': [
                            {
                                'title': str,
                                'status': 2,
                                'stream_url': {
                                    'live_core_sdk_data': {
                                        'pull_data': {
                                            'stream_data': validate.all(
                                                validate.parse_json(),
                                                validate.get('data'),
                                                {
                                                    validate.any("md", 'ld', 'ao', 'origin', 'hd', 'uhd', 'sd'): {
                                                        'main': {
                                                            'flv': validate.url(),
                                                            'sdk_params': validate.all(
                                                                validate.parse_json(),
                                                                {
                                                                    'VCodec': str,
                                                                    'vbitrate': int,
                                                                    'resolution': str,
                                                                }
                                                            )
                                                        }
                                                    }
                                                }
                                            )
                                        }
                                    }
                                }
                            }
                        ],
                        'user': {'nickname': str},
                        'enter_room_id': str,
                    }),
                    validate.union_get(
                        'enter_room_id',
                        ('user', 'nickname'),
                        ('data', 0, "title"),
                        ('data', 0, "stream_url", "live_core_sdk_data", "pull_data", "stream_data"),
                    ),
                ))
        except Exception as e:
            log.error(format(e))
            return
        if not data:
            return

        self.id, self.author, self.title, stream_data = data

        self.session.http.headers.update({
            "Origin": self.url,
            "Referer": self.url,
        })

        for k, v in stream_data.items():
            url = v['main']['flv']
            name = k
            vbitrate = v['main']['sdk_params']['vbitrate']

            self.QUALITY_WEIGHTS[name] = vbitrate

            yield name, HTTPStream(self.session, url)

        log.debug(f"QUALITY_WEIGHTS: {self.QUALITY_WEIGHTS!r}")


__plugin__ = Douyin