import unittest

from streamlink.plugins.artetv import ArteTV


class TestPluginArteTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        # new url
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/fr/direct/"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/de/live/"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/de/videos/074633-001-A/gesprach-mit-raoul-peck"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/en/videos/071437-010-A/sunday-soldiers"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/fr/videos/074633-001-A/entretien-avec-raoul-peck"))
        self.assertTrue(ArteTV.can_handle_url("http://www.arte.tv/pl/videos/069873-000-A/supermama-i-businesswoman"))

        # should match
        # old url - some of them get redirected and some are 404
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
        # shouldn't match - playlists without video ids in url
        self.assertFalse(ArteTV.can_handle_url("http://www.arte.tv/en/videos/RC-014457/the-power-of-forests/"))
        self.assertFalse(ArteTV.can_handle_url("http://www.arte.tv/en/videos/RC-013118/street-art/"))
