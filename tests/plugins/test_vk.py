from unittest.mock import Mock

import pytest

from streamlink.exceptions import NoStreamsError
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
    ]


@pytest.mark.parametrize("url,newurl,raises", [
    ("https://vk.com/videos-24136539?z=video-24136539_456241176%2Fclub24136539%2Fpl_-24136539_-2",
     "https://vk.com/video-24136539_456241176",
     False),
    ("https://vk.com/videos-24136539?z=video-24136539_456241181%2Fpl_-24136539_-2",
     "https://vk.com/video-24136539_456241181",
     False),
    ("https://vk.com/videos132886594?z=video132886594_167211693",
     "https://vk.com/video132886594_167211693",
     False),
    ("http://vk.com/",
     "http://vk.com/",
     False),
    ("http://vk.com/videos-24136539",
     "http://vk.com/videos-24136539",
     True),
    ("http://vk.com/videos-24136539?z=",
     "http://vk.com/videos-24136539?z=",
     True),
])
def test_url_redirect(url, newurl, raises):
    VK.bind(Mock(), "tests.plugins.test_vk")
    plugin = VK(url)
    try:
        plugin.follow_vk_redirect()
        assert not raises
    except NoStreamsError:
        assert raises
    assert plugin.url == newurl
