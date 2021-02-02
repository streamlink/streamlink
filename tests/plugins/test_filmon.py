import unittest

from streamlink.plugins.filmon import Filmon
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlFilmon(PluginCanHandleUrl):
    __plugin__ = Filmon

    should_match = [
        'http://www.filmon.tv/channel/grandstand-show',
        'http://www.filmon.tv/index/popout?channel_id=5510&quality=low',
        'http://www.filmon.tv/tv/channel/export?channel_id=5510&autoPlay=1',
        'http://www.filmon.tv/tv/channel/grandstand-show',
        'http://www.filmon.tv/tv/channel-4',
        'https://www.filmon.com/tv/bbc-news',
        'https://www.filmon.tv/tv/55',
        'http://www.filmon.tv/vod/view/10250-0-crime-boss',
        'http://www.filmon.tv/group/comedy',
    ]


class TestPluginFilmon(unittest.TestCase):
    def _test_regex(self, url, expected):
        m = Filmon.url_re.match(url)
        self.assertIsNotNone(m, url)
        # expected must return [is_group, channel, vod_id]
        self.assertEqual(expected, list(m.groups()))

    def test_regex_live_stream_channel(self):
        self._test_regex('http://www.filmon.tv/channel/grandstand-show',
                         [None, 'grandstand-show', None])

    def test_regex_live_stream_index_popout(self):
        self._test_regex('http://www.filmon.tv/index/popout?channel_id=5510&quality=low',
                         [None, '5510', None])

    def test_regex_live_stream_export(self):
        self._test_regex('http://www.filmon.tv/tv/channel/export?channel_id=5510&autoPlay=1',
                         [None, '5510', None])

    def test_regex_live_stream_tv_channel(self):
        self._test_regex('http://www.filmon.tv/tv/channel/grandstand-show',
                         [None, 'grandstand-show', None])

    def test_regex_live_stream_tv(self):
        self._test_regex('https://www.filmon.com/tv/bbc-news',
                         [None, 'bbc-news', None])

    def test_regex_live_stream_tv_with_channel_in_name(self):
        self._test_regex('https://www.filmon.com/tv/channel-4',
                         [None, 'channel-4', None])

    def test_regex_live_stream_tv_number(self):
        self._test_regex('https://www.filmon.tv/tv/55',
                         [None, '55', None])

    def test_regex_group(self):
        self._test_regex('http://www.filmon.tv/group/comedy',
                         ['group/', 'comedy', None])

    def test_regex_vod(self):
        self._test_regex('http://www.filmon.tv/vod/view/10250-0-crime-boss',
                         [None, None, '10250'])
