from streamlink.plugins.senategov import SenateGov
import unittest


class TestPluginSenateGov(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(SenateGov.can_handle_url(
            "https://www.foreign.senate.gov/hearings/business-meeting-082218"
        ))
        self.assertTrue(SenateGov.can_handle_url(
            "https://www.senate.gov/isvp/?comm=foreign&type=arch&stt=21:50&filename=foreign082218&auto_play=false"
            "&wmode=transparent&poster=https%3A%2F%2Fwww%2Eforeign%2Esenate%2Egov%2Fthemes%2Fforeign%2Fimages"
            "%2Fvideo-poster-flash-fit%2Epng"
        ))

        # shouldn't match
        self.assertFalse(SenateGov.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(SenateGov.can_handle_url("http://www.youtube.com/"))

    def test_stt_parse(self):
        self.assertEqual(600, SenateGov.parse_stt("10:00"))
        self.assertEqual(3600, SenateGov.parse_stt("01:00:00"))
        self.assertEqual(70, SenateGov.parse_stt("1:10"))
