import unittest

from streamlink.plugins.radionet import RadioNet


class TestPluginRadioNet(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(RadioNet.can_handle_url("http://radioparadise.radio.net/"))
        self.assertTrue(RadioNet.can_handle_url("http://oe1.radio.at/"))
        self.assertTrue(RadioNet.can_handle_url("http://deutschlandfunk.radio.de/"))
        self.assertTrue(RadioNet.can_handle_url("http://rneradionacional.radio.es/"))
        self.assertTrue(RadioNet.can_handle_url("http://franceinfo.radio.fr/"))
        self.assertTrue(RadioNet.can_handle_url("https://drp1bagklog.radio.dk/"))
        self.assertTrue(RadioNet.can_handle_url("http://rairadiouno.radio.it/"))
        self.assertTrue(RadioNet.can_handle_url("http://program1jedynka.radio.pl/"))
        self.assertTrue(RadioNet.can_handle_url("http://rtpantena1983fm.radio.pt/"))
        self.assertTrue(RadioNet.can_handle_url("http://sverigesp1.radio.se/"))

        # shouldn't match
        self.assertFalse(RadioNet.can_handle_url("http://radio.net/"))
        self.assertFalse(RadioNet.can_handle_url("http://radio.com/"))
        self.assertFalse(RadioNet.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(RadioNet.can_handle_url("http://www.youtube.com/"))
