from streamlink.plugins.huomao import Huomao
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHuomao(PluginCanHandleUrl):
    __plugin__ = Huomao

    should_match = [
        # Assert that an URL containing the http:// prefix is correctly read.
        "http://www.huomao.com/123456",
        "http://www.huomao.tv/123456",
        "http://huomao.com/123456",
        "http://huomao.tv/123456",
        "http://www.huomao.com/video/v/123456",
        "http://www.huomao.tv/video/v/123456",
        "http://huomao.com/video/v/123456",
        "http://huomao.tv/video/v/123456",

        # Assert that an URL containing the https:// prefix is correctly read.
        "https://www.huomao.com/123456",
        "https://www.huomao.tv/123456",
        "https://huomao.com/123456",
        "https://huomao.tv/123456",
        "https://www.huomao.com/video/v/123456",
        "https://www.huomao.tv/video/v/123456",
        "https://huomao.com/video/v/123456",
        "https://huomao.tv/video/v/123456",

        # Assert that an URL without the http(s):// prefix is correctly read.
        "www.huomao.com/123456",
        "www.huomao.tv/123456",
        "www.huomao.com/video/v/123456",
        "www.huomao.tv/video/v/123456",

        # Assert that an URL without the www prefix is correctly read.
        "huomao.com/123456",
        "huomao.tv/123456",
        "huomao.com/video/v/123456",
        "huomao.tv/video/v/123456",
    ]

    should_not_match = [
        # Assert that an URL without a room_id can't be read.
        "http://www.huomao.com/",
        "http://www.huomao.tv/",
        "http://huomao.com/",
        "http://huomao.tv/",
        "https://www.huomao.com/",
        "https://www.huomao.tv/",
        "https://huomao.com/",
        "https://huomao.tv/",
        "www.huomao.com/",
        "www.huomao.tv/",
        "huomao.tv/",
        "huomao.tv/",
    ]
