from streamlink.plugins.abweb import ABweb
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlABweb(PluginCanHandleUrl):
    __plugin__ = ABweb

    should_match = [
        'http://www.abweb.com/bis-tv-online/bistvo-tele-universal.aspx?chn=ab1',
        'http://www.abweb.com/BIS-TV-Online/bistvo-tele-universal.aspx?chn=ab1',
        'http://www.abweb.com/BIS-TV-Online/bistvo-tele-universal.aspx?chn=luckyjack',
        'https://www.abweb.com/BIS-TV-Online/bistvo-tele-universal.aspx?chn=action',
    ]

    should_not_match = [
        'http://www.abweb.com',
    ]
