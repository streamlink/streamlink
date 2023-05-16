from contextlib import nullcontext

import pytest
import requests_mock as rm

from streamlink import Streamlink
from streamlink.exceptions import NoStreamsError
from streamlink.plugins.vk import VK
from tests.plugins import PluginCanHandleUrl


does_not_raise = nullcontext()


class TestPluginCanHandleUrlVK(PluginCanHandleUrl):
    __plugin__ = VK

    should_match = [
        "http://vk.com/video-24136539_456239830",
        "http://vk.ru/video-24136539_456239830",
        "https://vk.com/video-9944999_456239622",
        "https://vk.ru/video-9944999_456239622",
        "https://www.vk.com/video-34453259_456240574",
        "https://www.vk.ru/video-34453259_456240574",
        "https://vk.com/videos-24136539?z=video-24136539_456241155%2Fpl_-24136539_-2",
        "https://vk.com/video?z=video-15755094_456245149%2Fpl_cat_lives",
        "https://vk.com/video?z=video132886594_167211693%2Fpl_cat_8",
        "https://vk.com/video132886594_167211693",
        "https://vk.com/videos132886594?z=video132886594_167211693",
        "https://vk.com/video-73154028_456239128",
        "https://vk.com/dota2?w=wall-126093223_1057924",
        "https://vk.com/search?c%5Bq%5D=dota&c%5Bsection%5D=auto&z=video295508334_171402661",
    ]

    should_not_match = [
        "https://vk.com/",
        "https://vk.ru/",
    ]


@pytest.mark.parametrize(("url", "newurl", "raises"), [
    # canonical video URL
    pytest.param(
        "https://vk.com/video-24136539_456241176",
        "https://vk.com/video-24136539_456241176",
        does_not_raise,
    ),

    # video ID from URL
    pytest.param(
        "https://vk.com/videos-24136539?z=video-24136539_456241181%2Fpl_-24136539_-2",
        "https://vk.com/video-24136539_456241181",
        does_not_raise,
    ),
    pytest.param(
        "https://vk.com/videos132886594?z=video132886594_167211693",
        "https://vk.com/video132886594_167211693",
        does_not_raise,
    ),
    pytest.param(
        "https://vk.com/search?c%5Bq%5D=dota&c%5Bsection%5D=auto&z=video295508334_171402661",
        "https://vk.com/video295508334_171402661",
        does_not_raise,
    ),

    # video ID from HTTP request
    pytest.param(
        "https://vk.com/dota2?w=wall-126093223_1057924",
        "https://vk.com/video-126093223_1057924",
        does_not_raise,
    ),

    # no video ID
    pytest.param(
        "https://vk.com/videos-0123456789?z=",
        "",
        pytest.raises(NoStreamsError),
    ),
    pytest.param(
        "https://vk.com/video/for_kids?z=video%2Fpl_-22277933_51053000",
        "",
        pytest.raises(NoStreamsError),
    ),
])
def test_url_redirect(url: str, newurl: str, raises: nullcontext, requests_mock: rm.Mocker):
    session = Streamlink()
    # noinspection PyTypeChecker
    plugin: VK = VK(session, url)
    requests_mock.get(url, text=f"""<!DOCTYPE html><html><head><meta property="og:url" content="{newurl}"/></head></html>""")
    with raises:
        plugin.follow_vk_redirect()
        assert plugin.url == newurl
