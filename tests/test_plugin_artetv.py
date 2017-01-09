import unittest

from streamlink.plugins.artetv import ArteTV


class TestPluginArteTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/guide/fr/direct"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/guide/de/live"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/guide/fr/024031-000-A/le-testament-du-docteur-mabuse"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/guide/de/024031-000-A/das-testament-des-dr-mabuse"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/guide/en/072544-002-A/christmas-carols-from-cork"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/guide/es/068380-000-A/una-noche-en-florencia"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/guide/pl/068916-006-A/belle-and-sebastian-route-du-rock"))

        # shouldn't match
        self.assertFalse(ArteTV.can_handle_url("http://www.arte.tv/guide/fr/plus7/"))
        self.assertFalse(ArteTV.can_handle_url("http://www.arte.tv/guide/de/plus7/"))
        self.assertFalse(ArteTV.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(ArteTV.can_handle_url("http://www.youtube.com/"))
