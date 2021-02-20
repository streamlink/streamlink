from streamlink.plugins.streamingvideoprovider import Streamingvideoprovider
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlStreamingvideoprovider(PluginCanHandleUrl):
    __plugin__ = Streamingvideoprovider

    should_match = [
        'http://www.streamingvideoprovider.co.uk/example',
    ]
