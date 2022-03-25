from streamlink.plugins.cmmedia import CMMedia
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCMMedia(PluginCanHandleUrl):
    __plugin__ = CMMedia

    should_match = [
        "http://cmmedia.es",
        "http://www.cmmedia.es",
        "http://cmmedia.es/any/path",
        "http://cmmedia.es/any/path?x",
        "http://www.cmmedia.es/any/path?x&y",
        "https://cmmedia.es",
        "https://www.cmmedia.es",
        "https://cmmedia.es/any/path",
        "https://cmmedia.es/any/path?x",
        "https://www.cmmedia.es/any/path?x&y",
    ]
