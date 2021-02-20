from streamlink.plugins.ine import INE
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlINE(PluginCanHandleUrl):
    __plugin__ = INE

    should_match = [
        'https://streaming.ine.com/play/11111111-2222-3333-4444-555555555555/introduction/',
    ]
