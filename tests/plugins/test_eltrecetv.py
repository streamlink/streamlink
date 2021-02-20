from streamlink.plugins.eltrecetv import ElTreceTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlElTreceTV(PluginCanHandleUrl):
    __plugin__ = ElTreceTV

    should_match = [
        "http://www.eltrecetv.com.ar/vivo",
        "http://www.eltrecetv.com.ar/pasapalabra/capitulo-1_084027",
        "http://www.eltrecetv.com.ar/a-todo-o-nada-2014/programa-2_072251",
    ]

    should_not_match = [
        "http://eltrecetv.com.ar/",
    ]
