from streamlink.plugins.tvibo import Tvibo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTvibo(PluginCanHandleUrl):
    __plugin__ = Tvibo

    should_match = [
        "http://player.tvibo.com/aztv/5929820",
        "http://player.tvibo.com/aztv/6858270/",
        "http://player.tvibo.com/aztv/3977238/",
    ]
