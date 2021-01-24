import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class NimoTV(Plugin):
    url_re = re.compile(r'https?://(?:www\.)?nimo\.tv/(?P<username>.*)')
    data_url = 'https://m.nimo.tv/{0}'
    data_re = re.compile(r'<script>var G_roomBaseInfo = ({.*?});</script>')

    author = None
    category = None
    title = None

    data_schema = validate.Schema(
        validate.transform(data_re.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(parse_json), {
                'title': str,
                'nickname': str,
                'game': str,
                'roomLineInfo': validate.any(None, {
                    'vCodeLines2': [{
                        'iBitRate': int,
                        'vCdns': [{
                            'vCdnUrls': [{
                                'smediaUrl': validate.url(),
                            }],
                        }],
                    }],
                }),
            },
        )),
    )

    video_qualities = {
        250: '240p',
        500: '360p',
        1000: '480p',
        2000: '720p',
        6000: '1080p',
    }

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_author(self):
        if self.author is not None:
            return self.author

    def get_category(self):
        if self.category is not None:
            return self.category

    def get_title(self):
        if self.title is not None:
            return self.title

    def _get_streams(self):
        m = self.url_re.match(self.url)
        if m and m.group('username'):
            username = m.group('username')
        else:
            return

        headers = {'User-Agent': useragents.ANDROID}
        data = self.session.http.get(
            self.data_url.format(username),
            headers=headers,
            schema=self.data_schema,
        )

        if data is None or data['roomLineInfo'] is None:
            return

        self.author = data['nickname']
        self.category = data['game']
        self.title = data['title']

        for vcl2 in data['roomLineInfo']['vCodeLines2']:
            q = self.video_qualities[vcl2['iBitRate']]
            for vcdn in vcl2['vCdns']:
                for vcdnurl in vcdn['vCdnUrls']:
                    if 'tx.hls.nimo.tv' in vcdnurl['smediaUrl']:
                        log.debug(f"HLS URL={vcdnurl['smediaUrl']} ({q})")
                        yield q, HLSStream(self.session, vcdnurl['smediaUrl'])


__plugin__ = NimoTV
