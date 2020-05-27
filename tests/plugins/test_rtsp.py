import unittest

from streamlink.plugins.rtsp import FFMPEGRTSPPlugin


class TestPluginFFMPEGRTSPPlugin(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov',
        ]
        for url in should_match:
            self.assertTrue(FFMPEGRTSPPlugin.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(FFMPEGRTSPPlugin.can_handle_url(url))
