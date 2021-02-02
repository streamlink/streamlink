from streamlink.plugins.radionet import RadioNet
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRadioNet(PluginCanHandleUrl):
    __plugin__ = RadioNet

    should_match = [
        "http://radioparadise.radio.net/",
        "http://oe1.radio.at/",
        "http://deutschlandfunk.radio.de/",
        "http://rneradionacional.radio.es/",
        "http://franceinfo.radio.fr/",
        "https://drp1bagklog.radio.dk/",
        "http://rairadiouno.radio.it/",
        "http://program1jedynka.radio.pl/",
        "http://rtpantena1983fm.radio.pt/",
        "http://sverigesp1.radio.se/",
    ]

    should_not_match = [
        "http://radio.net/",
        "http://radio.com/",
    ]
