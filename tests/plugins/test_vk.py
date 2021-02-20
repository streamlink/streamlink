import unittest

from streamlink.plugins.vk import VK
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVK(PluginCanHandleUrl):
    __plugin__ = VK

    should_match = [
        "https://vk.com/video-9944999_456239622",
        "http://vk.com/video-24136539_456239830",
        "https://www.vk.com/video-34453259_456240574",
        "https://vk.com/videos-24136539?z=video-24136539_456241155%2Fpl_-24136539_-2",
        "https://vk.com/video?z=video-15755094_456245149%2Fpl_cat_lives",
        "https://vk.com/video?z=video132886594_167211693%2Fpl_cat_8",
        "https://vk.com/video132886594_167211693",
        "https://vk.com/videos132886594?z=video132886594_167211693",
        "https://vk.com/video-73154028_456239128",
    ]

    should_not_match = [
        "https://vk.com/",
        "https://vk.com/restore",
        "https://www.vk.com/videos-24136539",
        "http://vk.com/videos-24136539",
    ]


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
        self.assertEqual(VK.follow_vk_redirect(
            "https://vk.com/videos132886594?z=video132886594_167211693"),
            "https://vk.com/video132886594_167211693"
        )

        # shouldn't redirect
        self.assertEqual(VK.follow_vk_redirect("http://vk.com/"), "http://vk.com/")
        self.assertEqual(VK.follow_vk_redirect("http://vk.com/videos-24136539"), "http://vk.com/videos-24136539")
        self.assertEqual(VK.follow_vk_redirect("http://www.youtube.com/"), "http://www.youtube.com/")
