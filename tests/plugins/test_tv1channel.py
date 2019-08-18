import unittest

from streamlink.plugins.tv1channel import TV1Channel


class TestPluginTV1Channel(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(TV1Channel.can_handle_url("http://tv1channel.org/"))
        self.assertTrue(TV1Channel.can_handle_url("http://tv1channel.org/index.php/livetv"))

        # shouldn't match
        self.assertFalse(TV1Channel.can_handle_url("https://local.local"))
        self.assertFalse(TV1Channel.can_handle_url("http://www.tv1channel.org/play/video.php?id=325"))
        self.assertFalse(TV1Channel.can_handle_url("http://www.tv1channel.org/play/video.php?id=340"))
