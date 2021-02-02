import unittest

from streamlink.plugins.senategov import SenateGov
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSenateGov(PluginCanHandleUrl):
    __plugin__ = SenateGov

    should_match = [
        "https://www.foreign.senate.gov/hearings/business-meeting-082218"
        "https://www.senate.gov/isvp/?comm=foreign&type=arch&stt=21:50&filename=foreign082218&auto_play=false"
        + "&wmode=transparent&poster=https%3A%2F%2Fwww%2Eforeign%2Esenate%2Egov%2Fthemes%2Fforeign%2Fimages"
        + "%2Fvideo-poster-flash-fit%2Epng"
    ]


class TestPluginSenateGov(unittest.TestCase):
    def test_stt_parse(self):
        self.assertEqual(600, SenateGov.parse_stt("10:00"))
        self.assertEqual(3600, SenateGov.parse_stt("01:00:00"))
        self.assertEqual(70, SenateGov.parse_stt("1:10"))
