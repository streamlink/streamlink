import unittest

from streamlink.plugins.vk import VK


class TestPluginVK(unittest.TestCase):
    def test_follow_vk_redirect(self):
        # should redirect
        self.assertEqual(VK.follow_vk_redirect(
            "https://vk.com/videos-24136539?z=video-24136539_456241176%2Fclub24136539%2Fpl_-24136539_-2"),
            "https://vk.com/video-24136539_456241176"
        )
        self.assertEqual(VK.follow_vk_redirect(
            "https://vk.com/videos-24136539?z=video-24136539_456241181%2Fpl_-24136539_-2"),
            "https://vk.com/video-24136539_456241181"
        )

        # shouldn't redirect
        self.assertEqual(VK.follow_vk_redirect("http://vk.com/"), "http://vk.com/")
        self.assertEqual(VK.follow_vk_redirect("http://vk.com/videos-24136539"), "http://vk.com/videos-24136539")
        self.assertEqual(VK.follow_vk_redirect("http://www.youtube.com/"), "http://www.youtube.com/")

    def test_can_handle_url(self):
        # should match
        self.assertTrue(VK.can_handle_url("https://vk.com/video-9944999_456239622"))
        self.assertTrue(VK.can_handle_url("http://vk.com/video-24136539_456239830"))
        self.assertTrue(VK.can_handle_url("https://www.vk.com/video-34453259_456240574"))
        self.assertTrue(VK.can_handle_url("https://vk.com/videos-24136539?z=video-24136539_456241155%2Fpl_-24136539_-2"))

        # shouldn't match
        self.assertFalse(VK.can_handle_url("https://vk.com/"))
        self.assertFalse(VK.can_handle_url("https://vk.com/restore"))
        self.assertFalse(VK.can_handle_url("https://www.vk.com/videos-24136539"))
        self.assertFalse(VK.can_handle_url("http://vk.com/videos-24136539"))
        self.assertFalse(VK.can_handle_url("http://www.youtube.com/"))
