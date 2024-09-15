from argparse import Namespace
from unittest.mock import Mock

import pytest

from streamlink.plugin import Plugin
from streamlink_cli.main import get_formatter
from streamlink_cli.utils import datetime


@pytest.fixture(scope="module")
def plugin():
    class FakePlugin(Plugin):
        __module__ = "FAKE"

        def _get_streams(self):  # pragma: no cover
            pass

    plugin = FakePlugin(Mock(), "https://foo/bar")
    plugin.id = "ID"
    plugin.author = "AUTHOR"
    plugin.category = "CATEGORY"
    plugin.title = "TITLE"

    return plugin


@pytest.mark.parametrize(
    ("formatterinput", "expected"),
    [
        pytest.param("{url}", "https://foo/bar", id="url"),
        pytest.param("{plugin}", "FAKE", id="plugin-name"),
        pytest.param("{id}", "ID", id="id"),
        pytest.param("{author}", "AUTHOR", id="author"),
        pytest.param("{category}", "CATEGORY", id="category"),
        pytest.param("{game}", "CATEGORY", id="category-fallback-game"),
        pytest.param("{title}", "TITLE", id="title"),
        pytest.param("{time}", "2000-01-01_00-00-00", id="time"),
        pytest.param("{time:%Y}", "2000", id="time-formatted"),
    ],
)
def test_get_formatter(monkeypatch: pytest.MonkeyPatch, plugin: Plugin, formatterinput: str, expected: str):
    # workaround for freezegun not being able to patch the subclassed datetime class in streamlink_cli.utils
    # which defines the default datetime->str conversion format (needed for path outputs)
    monkeypatch.setattr("streamlink_cli.utils.datetime.now", Mock(return_value=datetime(2000, 1, 1, 0, 0, 0, 0)))
    monkeypatch.setattr("streamlink_cli.main.args", Namespace(url="https://foo/bar"))

    formatter = get_formatter(plugin)
    assert formatter.title(formatterinput) == expected
