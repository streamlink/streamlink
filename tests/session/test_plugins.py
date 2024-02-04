from pathlib import Path
from typing import Type
from unittest.mock import Mock, call

import pytest

import streamlink.plugins
import tests.plugin
from streamlink.plugin.plugin import Plugin, pluginargument
from streamlink.session import Streamlink
from streamlink.session.plugins import StreamlinkPlugins


PATH_BUILTINPLUGINS = Path(streamlink.plugins.__path__[0])
PATH_TESTPLUGINS = Path(tests.plugin.__path__[0])
PATH_TESTPLUGINS_OVERRIDE = PATH_TESTPLUGINS / "override"


@pytest.fixture(autouse=True)
def caplog(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(1, "streamlink")
    return caplog


@pytest.fixture(scope="module")
def fake_plugin():
    @pluginargument("foo")
    @pluginargument("bar")
    class FakePlugin(Plugin):
        __module__ = "streamlink.plugins.fake"

        def _get_streams(self): pass  # pragma: no cover

    return FakePlugin


def test_empty(caplog: pytest.LogCaptureFixture, session: Streamlink):
    assert session.plugins.get_names() == []
    assert session.plugins.get_loaded() == {}
    assert caplog.record_tuples == []


def test_set_get_del(session: Streamlink, fake_plugin: Type[Plugin]):
    assert "fake" not in session.plugins

    session.plugins["fake"] = fake_plugin
    assert "fake" in session.plugins
    assert session.plugins["fake"] is fake_plugin
    assert session.plugins.get_names() == ["fake"]
    assert session.plugins.get_loaded() == {"fake": fake_plugin}
    assert session.plugins.get_loaded() is not session.plugins.get_loaded()

    del session.plugins["fake"]
    assert "fake" not in session.plugins
    assert session.plugins.get_names() == []
    assert session.plugins.get_loaded() == {}


def test_update_clear(session: Streamlink, fake_plugin: Type[Plugin]):
    assert "fake" not in session.plugins

    session.plugins.update({"fake": fake_plugin})
    assert "fake" in session.plugins
    assert session.plugins["fake"] is fake_plugin
    assert session.plugins.get_names() == ["fake"]
    assert session.plugins.get_loaded() == {"fake": fake_plugin}

    session.plugins.clear()
    assert "fake" not in session.plugins
    assert session.plugins.get_names() == []
    assert session.plugins.get_loaded() == {}


def test_iter_arguments(session: Streamlink, fake_plugin: Type[Plugin]):
    session.plugins.update({"fake": fake_plugin})
    assert [(name, [arg.argument_name(name) for arg in args]) for name, args in session.plugins.iter_arguments()] == [
        ("fake", ["--fake-foo", "--fake-bar"]),
    ]


class TestLoad:
    def test_load_builtin(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, fake_plugin: Type[Plugin]):
        mock = Mock(return_value={"fake": fake_plugin})
        monkeypatch.setattr(StreamlinkPlugins, "_load_from_path", mock)
        session = Streamlink(plugins_builtin=True)

        assert mock.call_args_list == [call(PATH_BUILTINPLUGINS)]
        assert "fake" in session.plugins
        assert session.plugins.get_names() == ["fake"]
        assert session.plugins.get_loaded() == {"fake": fake_plugin}
        assert session.plugins["fake"].__module__ == "streamlink.plugins.fake"
        assert caplog.record_tuples == []

    def test_load_path_empty(self, tmp_path: Path, caplog: pytest.LogCaptureFixture, session: Streamlink):
        assert not session.plugins.load_path(tmp_path)
        assert session.plugins.get_names() == []
        assert session.plugins.get_loaded() == {}
        assert caplog.record_tuples == []

    def test_load_path_testplugins(self, caplog: pytest.LogCaptureFixture, session: Streamlink):
        assert session.plugins.load_path(PATH_TESTPLUGINS)
        assert "testplugin" in session.plugins
        assert "testplugin_invalid" not in session.plugins
        assert "testplugin_missing" not in session.plugins
        assert session.plugins.get_names() == ["testplugin"]
        assert session.plugins["testplugin"].__name__ == "TestPlugin"
        assert session.plugins["testplugin"].__module__ == "streamlink.plugins.testplugin"
        assert caplog.record_tuples == []

        assert session.plugins.load_path(PATH_TESTPLUGINS_OVERRIDE)
        assert "testplugin" in session.plugins
        assert session.plugins.get_names() == ["testplugin"]
        assert session.plugins["testplugin"].__name__ == "TestPluginOverride"
        assert session.plugins["testplugin"].__module__ == "streamlink.plugins.testplugin"
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.session",
                "info",
                f"Plugin testplugin is being overridden by {PATH_TESTPLUGINS_OVERRIDE / 'testplugin.py'}",
            ),
        ]

    def test_importerror(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, session: Streamlink):
        monkeypatch.setattr("importlib.machinery.FileFinder.find_spec", Mock(return_value=None))
        assert not session.plugins.load_path(PATH_TESTPLUGINS)
        assert "testplugin" not in session.plugins
        assert session.plugins.get_names() == []
        assert [(record.name, record.levelname, record.message, bool(record.exc_info)) for record in caplog.records] == [
            (
                "streamlink.session",
                "error",
                f"Failed to load plugin testplugin from {PATH_TESTPLUGINS}\n",
                True,
            ),
            (
                "streamlink.session",
                "error",
                f"Failed to load plugin testplugin_invalid from {PATH_TESTPLUGINS}\n",
                True,
            ),
            (
                "streamlink.session",
                "error",
                f"Failed to load plugin testplugin_missing from {PATH_TESTPLUGINS}\n",
                True,
            ),
        ]

    def test_syntaxerror(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, session: Streamlink):
        monkeypatch.setattr("importlib.machinery.SourceFileLoader.exec_module", Mock(side_effect=SyntaxError))
        with pytest.raises(SyntaxError):
            session.plugins.load_path(PATH_TESTPLUGINS)
        assert session.plugins.get_names() == []
        assert caplog.record_tuples == []
