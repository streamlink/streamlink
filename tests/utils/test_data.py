import unittest

from streamlink.utils.data import search_dict


class TestUtilsData(unittest.TestCase):
    def test_search_dict(self):
        self.assertSequenceEqual(
            list(search_dict(["one", "two"], "one")),
            []
        )
        self.assertSequenceEqual(
            list(search_dict({"two": "test2"}, "one")),
            []
        )
        self.assertSequenceEqual(
            list(search_dict({"one": "test1", "two": "test2"}, "one")),
            ["test1"]
        )
        self.assertSequenceEqual(
            list(search_dict({"one": {"inner": "test1"}, "two": "test2"}, "inner")),
            ["test1"]
        )
        self.assertSequenceEqual(
            list(search_dict({"one": [{"inner": "test1"}], "two": "test2"}, "inner")),
            ["test1"]
        )
        self.assertSequenceEqual(
            list(sorted(search_dict({"one": [{"inner": "test1"}], "two": {"inner": "test2"}}, "inner"))),
            list(sorted(["test1", "test2"]))
        )
