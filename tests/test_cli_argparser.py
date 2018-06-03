import unittest

from streamlink_cli.argparser import hours_minutes_seconds


class TestCLIArgparser(unittest.TestCase):

    def test_hours_minutes_seconds(self):
        self.assertEqual(hours_minutes_seconds("00:01:30"), 90)
        self.assertEqual(hours_minutes_seconds("01:20:15"), 4815)
        self.assertEqual(hours_minutes_seconds("26:00:00"), 93600)
        self.assertEqual(hours_minutes_seconds("444"), 444)
        self.assertEqual(hours_minutes_seconds("8888"), 8888)

        with self.assertRaises(ValueError):
            hours_minutes_seconds("FOO")

        with self.assertRaises(ValueError):
            hours_minutes_seconds("BAR")
