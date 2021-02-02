from streamlink.plugins.lrt import LRT
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLRT(PluginCanHandleUrl):
    __plugin__ = LRT

    should_match = [
        "https://www.lrt.lt/mediateka/tiesiogiai/lrt-opus",
        "https://www.lrt.lt/mediateka/tiesiogiai/lrt-klasika",
        "https://www.lrt.lt/mediateka/tiesiogiai/lrt-radijas",
        "https://www.lrt.lt/mediateka/tiesiogiai/lrt-lituanica",
        "https://www.lrt.lt/mediateka/tiesiogiai/lrt-plius",
        "https://www.lrt.lt/mediateka/tiesiogiai/lrt-televizija",
    ]

    should_not_match = [
        "https://www.lrt.lt",
        "https://www.lrt.lt/mediateka/irasas/1013694276/savanoriai-tures-galimybe-pamatyti-popieziu-is-arciau",
    ]
