from streamlink.plugins.pickleballtv import PickleballTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPickleballTV(PluginCanHandleUrl):
    __plugin__ = PickleballTV

    should_match = [
        "https://pickleballtv.com",
    ]
