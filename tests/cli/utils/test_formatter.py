from datetime import datetime
from os.path import sep
from pathlib import Path
from string import ascii_letters as alphabet
from unittest.mock import Mock, call, patch

import pytest
from freezegun import freeze_time

from streamlink_cli.utils.formatter import Formatter


class TestCLIFormatter:
    class Obj:
        def __str__(self):
            return "obj"

    @pytest.fixture()
    def mock_replace_chars(self):
        with patch("streamlink_cli.utils.formatter.replace_chars") as mock_replace_chars:
            yield mock_replace_chars

    @pytest.fixture()
    def prop(self):
        return Mock(return_value="prop")

    @pytest.fixture()
    def obj(self):
        return self.Obj()

    @pytest.fixture()
    def formatter(self, prop: Mock, obj: Obj):
        with freeze_time("2000-01-02T03:04:05.000006Z"):
            yield Formatter(
                {
                    "prop": prop,
                    "obj": lambda: obj,
                    "time": datetime.now,
                    "empty": lambda: "",
                    "none": lambda: None,
                },
                {
                    "time": lambda dt, fmt: dt.strftime(fmt),
                },
            )

    def test_title(self, formatter: Formatter):
        assert formatter.title == formatter.format

    def test_path(self, formatter: Formatter, prop: Mock, obj: Obj, mock_replace_chars: Mock):
        mock_replace_chars.side_effect = lambda s, *_: s.upper()

        assert formatter.path("text '{prop}' '{empty}' '{none}'") == Path("text 'PROP' '' ''")
        assert formatter.cache == dict(prop="prop", empty="", none=None)
        assert prop.call_count == 1
        assert mock_replace_chars.call_args_list == [
            call("prop", None),
            call("", None),
            call("", None),
        ]
        mock_replace_chars.reset_mock()

        assert formatter.path("text '{prop}' '{obj}' '{empty}' '{none}'", "foo") == Path("text 'PROP' 'OBJ' '' ''")
        assert formatter.cache == dict(prop="prop", obj=obj, empty="", none=None)
        assert prop.call_count == 1
        assert mock_replace_chars.call_args_list == [
            call("prop", "foo"),
            call("obj", "foo"),
            call("", "foo"),
            call("", "foo"),
        ]

    def test_path_substitute(self, formatter: Formatter):
        formatter.mapping.update({
            "current": lambda: ".",
            "parent": lambda: "..",
            "dots": lambda: "...",
            "separator": lambda: sep,
        })
        path = formatter.path(f"{{current}}{sep}{{parent}}{sep}{{dots}}{sep}{{separator}}{sep}foo{sep}.{sep}..{sep}bar")
        assert path == Path("_", "_", "...", "_", "foo", ".", "..", "bar"), \
            "Formats the path's parts separately and ignores current and parent directories in substitutions only"  # fmt: skip

    def test_path_truncation_ascii(self, formatter: Formatter):
        formatter.mapping.update({
            "dir": lambda: alphabet * 10,
            "file": lambda: alphabet * 10,
        })
        path = formatter.path(f"{{dir}}.fakeext{sep}{{file}}.ext")
        assert path == Path((alphabet * 10)[:255], f"{(alphabet * 10)[:251]}.ext")

    def test_path_truncation_unicode(self, formatter: Formatter):
        formatter.mapping.update({
            "dir": lambda: "🐻" * 512,
            "file": lambda: "🐻" * 512,
        })
        path = formatter.path(f"{{dir}}.fakeext{sep}{{file}}.ext")
        assert path == Path("🐻" * 63, f"{'🐻' * 62}.ext")
