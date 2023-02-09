from streamlink.plugins.streamable import Streamable
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlStreamable(PluginCanHandleUrl):
    __plugin__ = Streamable

    should_match = [
        "https://streamable.com/example",
    ]
