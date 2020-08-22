import logging
import re

from hashlib import md5
from time import time

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Huomao(Plugin):
    '''
    magic_val:

    This value is returned by the function that is an argument to md5() in
    https://m.huomao.com/static/web/js/sea.js?v=202004029 on L287 in the
    prettifyed JS source.  At the time of writing, this function returned a
    static value.  This value could change at some point in the future if
    sea.js is updated.  As it is, if a change to sea.js means this value is no
    longer static, this plugin will break and some rewriting will be required.
    The arguments to the JS md5 function are as defined by the arguments for
    'token = md5(...)' in the _get_streams_data() method within this plugin.

    With due credit to @bastimeyer:
    https://github.com/streamlink/streamlink/pull/3104#issuecomment-671095610
    '''
    magic_val = '6FE26D855E1AEAE090E243EB1AF73685'
    mobile_url = 'https://m.huomao.com/mobile/mob_live/{0}'
    live_data_url = 'https://m.huomao.com/swf/live_data'
    vod_url = 'https://www.huomao.com/video/vreplay/{0}'

    url_re = re.compile(r'''
        (?:https?://)?(?:www\.)?huomao(?:\.tv|\.com)
        (?P<path>/|/video/v/)
        (?P<room_id>\d+)
    ''', re.VERBOSE)

    author_re = re.compile(
        r'<p class="nickname_live">\s*<span>\s*(.*?)\s*</span>',
        re.DOTALL,
    )

    title_re = re.compile(
        r'<p class="title-name">\s*(.*?)\s*</p>',
        re.DOTALL,
    )

    video_id_re = re.compile(r'var stream = "([^"]+)"')
    video_res_re = re.compile(r'_([\d]+p?)\.m3u8')
    vod_data_re = re.compile(r'var video = ({.*});')

    _live_data_schema = validate.Schema({
        'roomStatus': validate.transform(lambda x: int(x)),
        'streamList': [{'list_hls': [{
            'url': validate.url(),
        }]}],
    })

    _vod_data_schema = validate.Schema({
        'title': validate.text,
        'username': validate.text,
        'vaddress': [{
            'url': validate.url(),
            'vheight': int,
        }],
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_live_streams_data(self, video_id):
        client_type = 'huomaomobileh5'
        time_now = int(time())

        token = md5(
            "{0}{1}{2}{3}".format(
                str(video_id),
                str(client_type),
                str(time_now),
                str(self.magic_val),
            )
        ).hexdigest()
        log.debug("Token={0}".format(token))

        post_data = {
            'cdns': 1,
            'streamtype': 'live',
            'VideoIDS': video_id,
            'from': client_type,
            'time': time_now,
            'token': token,
        }
        video_data = self.session.http.post(self.live_data_url, data=post_data)

        return self.session.http.json(
            video_data,
            schema=self._live_data_schema,
        )

    def _get_vod_streams(self, vod_id):
        res = self.session.http.get(self.vod_url.format(vod_id))
        m = self.vod_data_re.search(res.text)
        vod_json = m and m.group(1)

        if vod_json is None:
            raise PluginError("Failed to get VOD data")

        vod_json = vod_json.decode('unicode-escape')
        vod_json = vod_json.replace('"[', '[')
        vod_json = vod_json.replace(']"', ']')
        vod_json = vod_json.replace('\\', '')
        vod_data = parse_json(vod_json, schema=self._vod_data_schema)

        self.title = vod_data['title'].encode(res.encoding)
        self.author = vod_data['username'].encode(res.encoding)
        self.category = 'VOD'

        log.debug("Title={0}".format(self.title))
        log.debug("Author={0}".format(self.author))
        log.debug("Category={0}".format(self.category))

        vod_data = vod_data['vaddress']

        streams = {}
        for stream in vod_data:
            video_res = stream['vheight']

            if 'p' not in str(video_res):
                video_res = "{0}p".format(video_res)

            if video_res in streams:
                video_res = "{0}_alt".format(video_res)

            streams[video_res] = HLSStream(self.session, stream['url'])

        return streams

    def _get_live_streams(self, room_id):
        res = self.session.http.get(self.mobile_url.format(room_id))

        m = self.title_re.search(res.text)
        if m:
            self.title = m.group(1).encode(res.encoding)
        else:
            raise PluginError("Failed to get title")

        m = self.author_re.search(res.text)
        if m:
            self.author = m.group(1).encode(res.encoding)
        else:
            raise PluginError("Failed to get author")

        self.category = 'Live'

        log.debug("Title={0}".format(self.title))
        log.debug("Author={0}".format(self.author))
        log.debug("Category={0}".format(self.category))

        m = self.video_id_re.search(res.text)
        video_id = m and m.group(1)

        if video_id is None:
            raise PluginError("Failed to get video ID")
        else:
            log.debug("Video ID={0}".format(video_id))

        streams_data = self._get_live_streams_data(video_id)

        if streams_data['roomStatus'] == 0:
            log.info("This room is currently inactive: {0}".format(room_id))
            return

        streams_data = streams_data['streamList'][0]['list_hls']

        streams = {}
        for stream in streams_data:
            m = self.video_res_re.search(stream['url'])
            video_res = m and m.group(1)
            if video_res is None:
                continue

            if 'p' not in video_res:
                video_res = "{0}p".format(video_res)

            if video_res in streams:
                video_res = "{0}_alt".format(video_res)

            streams[video_res] = HLSStream(self.session, stream['url'])

        return streams

    def get_title(self):
        if self.title is not None:
            return self.title

    def get_author(self):
        if self.author is not None:
            return self.author

    def get_category(self):
        if self.category is not None:
            return self.category

    def _get_streams(self):
        path, url_id = self.url_re.search(self.url).groups()
        log.debug("Path={0}".format(path))
        log.debug("URL ID={0}".format(url_id))

        self.title = None
        self.author = None
        self.category = None

        if path != '/':
            return self._get_vod_streams(url_id)
        else:
            return self._get_live_streams(url_id)


__plugin__ = Huomao
