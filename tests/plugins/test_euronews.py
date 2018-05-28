import unittest

from streamlink.plugins.euronews import Euronews


class TestPluginEuronews(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Euronews.can_handle_url("http://www.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://fr.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://de.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://it.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://es.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://pt.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://ru.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://ua.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://tr.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://gr.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://hu.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://fa.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://arabic.euronews.com/live"))
        self.assertTrue(Euronews.can_handle_url("http://www.euronews.com/2017/05/10/peugeot-expects-more-opel-losses-this-year"))
        self.assertTrue(Euronews.can_handle_url("http://fr.euronews.com/2017/05/10/l-ag-de-psa-approuve-le-rachat-d-opel"))

        # shouldn't match
        self.assertFalse(Euronews.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Euronews.can_handle_url("http://www.youtube.com/"))
