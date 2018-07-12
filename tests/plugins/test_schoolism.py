import unittest

from streamlink.plugins.schoolism import Schoolism


class TestPluginSchoolism(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.schoolism.com/watchLesson.php',
        ]
        for url in should_match:
            self.assertTrue(Schoolism.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.schoolism.com',
        ]
        for url in should_not_match:
            self.assertFalse(Schoolism.can_handle_url(url))
