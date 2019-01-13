import unittest

from streamlink.plugins.kanal7 import Kanal7


class TestPluginKanal7(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.kanal7.com/canli-izle',
            'https://www.tvt.tv.tr/canli-yayin',
        ]
        for url in should_match:
            self.assertTrue(Kanal7.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Kanal7.can_handle_url(url))

    def test_iframe_re(self):
        test_list = [
            # http://www.kanal7.com/canli-izle
            ('<iframe id="selectFrame" src="https://www.kanal7.com/canli-yayin-iframe.php" scrolling="no"></iframe>',
             'https://www.kanal7.com/canli-yayin-iframe.php'),
            # https://www.tvt.tv.tr/canli-yayin
            ('<iframe id="selectFrame" src="/canli-yayin-iframe.php" height="650"></iframe>',
             '/canli-yayin-iframe.php'),
        ]
        for text, url in test_list:
            m = Kanal7.iframe_re.search(text)
            self.assertIsNotNone(m, url)
            self.assertEqual(m.group(1), url, url)

    def test_stream_re(self):
        test_list = [
            # http://www.kanal7.com/canli-izle
            ('''script.setAttribute('video-source','https://live/kanal7LiveDesktop/index.m3u8');''',
             'https://live/kanal7LiveDesktop/index.m3u8'),
            # https://www.tvt.tv.tr/canli-yayin
            ('''video-source="https://live/tvtLiveStream/index.m3u8"''',
             'https://live/tvtLiveStream/index.m3u8'),
        ]
        for text, url in test_list:
            m = Kanal7.stream_re.search(text)
            self.assertIsNotNone(m, url)
            self.assertEqual(m.group(1), url, url)
