from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time

from streamlink.utils.formatter import Formatter


class TestFormatter:
    class Obj:
        def __str__(self):
            return "obj"

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
                    "time": lambda: datetime.now(timezone.utc),
                    "empty": lambda: "",
                    "none": lambda: None,
                },
                {
                    "time": lambda dt, fmt: dt.strftime(fmt),
                },
            )

    def test_unknown(self, formatter: Formatter):
        assert formatter.format("{}") == "{}"
        assert formatter.format("some {unknown} variable") == "some {unknown} variable"
        assert formatter.format("some {unknown} variable", {"unknown": "known"}) == "some known variable"
        assert formatter.cache == {}

    def test_format(self, formatter: Formatter, prop: Mock, obj: Obj):
        assert formatter.format("text '{prop}' '{empty}' '{none}'") == "text 'prop' '' ''"
        assert formatter.cache == dict(prop="prop", empty="", none=None)
        assert prop.call_count == 1

        assert formatter.format("text '{prop}' '{obj}' '{empty}' '{none}'") == "text 'prop' 'obj' '' ''"
        assert formatter.cache == dict(prop="prop", obj=obj, empty="", none=None)
        assert prop.call_count == 1

        defaults = dict(prop="PROP", obj="OBJ", empty="EMPTY", none="NONE")
        assert formatter.format("'{prop}' '{obj}' '{empty}' '{none}'", defaults) == "'prop' 'obj' '' 'NONE'"
        assert formatter.cache == dict(prop="prop", obj=obj, empty="", none=None)
        assert prop.call_count == 1

    def test_format_spec(self, formatter: Formatter):
        assert formatter.format("{time}") == "2000-01-02 03:04:05.000006+00:00"
        assert formatter.cache == dict(time=datetime(2000, 1, 2, 3, 4, 5, 6, timezone.utc))
        assert formatter.format("{time:%Y}") == "2000"
        assert formatter.format("{time:%Y-%m-%d}") == "2000-01-02"
        assert formatter.format("{time:%H:%M:%S}") == "03:04:05"
        assert formatter.format("{time:%Z}") == "UTC"
        with patch("datetime.datetime.strftime", side_effect=ValueError):
            assert formatter.format("{time:foo:bar}") == "{time:foo:bar}"
        assert formatter.cache == dict(time=datetime(2000, 1, 2, 3, 4, 5, 6, timezone.utc))

        assert formatter.format("{prop:foo}") == "prop"
        assert formatter.format("{none:foo}") == ""
        assert formatter.format("{unknown:format}") == "{unknown:format}"
        assert formatter.format("{unknown:format}", {"unknown": "known"}) == "known"
