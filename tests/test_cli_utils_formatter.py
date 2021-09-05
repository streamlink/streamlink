import unittest
from unittest.mock import Mock, call, patch

from streamlink_cli.utils.formatter import Formatter


class TestFormatter(unittest.TestCase):
    class Obj:
        def __str__(self):
            return "obj"

    def setUp(self):
        self.prop = Mock(return_value="prop")
        self.obj = self.Obj()
        self.formatter = Formatter({
            "prop": self.prop,
            "obj": lambda: self.obj,
            "empty": lambda: "",
            "none": lambda: None
        })

    def test_unknown(self):
        self.assertEqual(self.formatter.title("{}"), "{}")
        self.assertEqual(self.formatter.title("some {unknown} variable"), "some {unknown} variable")
        self.assertEqual(self.formatter.title("some {unknown} variable", {"unknown": "known"}), "some known variable")
        self.assertEqual(self.formatter.cache, dict())

    def test_title(self):
        self.assertEqual(self.formatter.title("text '{prop}' '{empty}' '{none}'"), "text 'prop' '' ''")
        self.assertEqual(self.formatter.cache, dict(prop="prop", empty="", none=None))
        self.assertEqual(self.prop.call_count, 1)

        self.assertEqual(self.formatter.title("text '{prop}' '{obj}' '{empty}' '{none}'"), "text 'prop' 'obj' '' ''")
        self.assertEqual(self.formatter.cache, dict(prop="prop", obj=self.obj, empty="", none=None))
        self.assertEqual(self.prop.call_count, 1)

        defaults = dict(prop="PROP", obj="OBJ", empty="EMPTY", none="NONE")
        self.assertEqual(self.formatter.title("'{prop}' '{obj}' '{empty}' '{none}'", defaults), "'prop' 'obj' '' 'NONE'")
        self.assertEqual(self.formatter.cache, dict(prop="prop", obj=self.obj, empty="", none=None))
        self.assertEqual(self.prop.call_count, 1)

    @patch("streamlink_cli.utils.formatter.replace_chars")
    def test_filename(self, mock_replace_chars: Mock):
        mock_replace_chars.side_effect = lambda s, *_: s.upper()

        self.assertEqual(self.formatter.filename("text '{prop}' '{empty}' '{none}'"), "text 'PROP' '' ''")
        self.assertEqual(self.formatter.cache, dict(prop="prop", empty="", none=None))
        self.assertEqual(self.prop.call_count, 1)
        self.assertEqual(mock_replace_chars.call_args_list, [
            call("prop", None), call("", None), call("", None)
        ])
        mock_replace_chars.reset_mock()

        self.assertEqual(self.formatter.filename("text '{prop}' '{obj}' '{empty}' '{none}'", "foo"), "text 'PROP' 'OBJ' '' ''")
        self.assertEqual(self.formatter.cache, dict(prop="prop", obj=self.obj, empty="", none=None))
        self.assertEqual(self.prop.call_count, 1)
        self.assertEqual(mock_replace_chars.call_args_list, [
            call("prop", "foo"), call("obj", "foo"), call("", "foo"), call("", "foo")
        ])
