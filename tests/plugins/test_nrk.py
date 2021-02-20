from streamlink.plugins.nrk import NRK
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNRK(PluginCanHandleUrl):
    __plugin__ = NRK

    should_match = [
        'https://tv.nrk.no/direkte/nrk1',
        'https://tv.nrk.no/direkte/nrk2',
        'https://tv.nrk.no/direkte/nrk3',
        'https://tv.nrk.no/direkte/nrksuper',

        'https://tv.nrk.no/serie/nytt-paa-nytt/2020/MUHH43003020',
        'https://tv.nrk.no/serie/kongelige-fotografer/sesong/1/episode/2/avspiller',

        'https://tv.nrk.no/program/NNFA51102617',

        'https://radio.nrk.no/direkte/p1',
        'https://radio.nrk.no/direkte/p2',

        'https://radio.nrk.no/podkast/oppdatert/l_5005d62a-7f4f-4581-85d6-2a7f4f2581f2',
    ]

    should_not_match = [
        'https://tv.nrk.no/',
        'https://radio.nrk.no/',
        'https://nrk.no/',
    ]
