import unittest
from datetime import datetime
from unittest.mock import Mock, call, patch

from freezegun import freeze_time

from streamlink_cli.utils.formatter import Formatter


@freeze_time(datetime(2000, 1, 2, 3, 4, 5, 6, None))
class TestFormatter(unittest.TestCase):
    class Obj:
        def __str__(self):
            return "obj"

    def setUp(self):
        self.prop = Mock(return_value="prop")
        self.obj = self.Obj()
        self.formatter = Formatter(
            {
                "prop": self.prop,
                "obj": lambda: self.obj,
                "time": datetime.now,
                "empty": lambda: "",
                "none": lambda: None
            },
            {
                "time": lambda dt, fmt: dt.strftime(fmt)
            }
        )

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

    def test_format_spec(self):
        self.assertEqual(self.formatter.title("{time}"), "2000-01-02 03:04:05.000006")
        self.assertEqual(self.formatter.cache, dict(time=datetime(2000, 1, 2, 3, 4, 5, 6, None)))
        self.assertEqual(self.formatter.title("{time:%Y}"), "2000")
        self.assertEqual(self.formatter.title("{time:%Y-%m-%d}"), "2000-01-02")
        self.assertEqual(self.formatter.title("{time:%H:%M:%S}"), "03:04:05")
        with patch("datetime.datetime.strftime", side_effect=ValueError):
            self.assertEqual(self.formatter.title("{time:foo:bar}"), "{time:foo:bar}")
        self.assertEqual(self.formatter.cache, dict(time=datetime(2000, 1, 2, 3, 4, 5, 6, None)))

        self.assertEqual(self.formatter.title("{prop:foo}"), "prop")
        self.assertEqual(self.formatter.title("{none:foo}"), "")
        self.assertEqual(self.formatter.title("{unknown:format}"), "{unknown:format}")
        self.assertEqual(self.formatter.title("{unknown:format}", {"unknown": "known"}), "known")
