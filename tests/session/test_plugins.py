from __future__ import annotations

import base64
import hashlib
import re

# noinspection PyProtectedMember
from importlib.metadata import FileHash, PackagePath
from pathlib import Path
from typing import cast
from unittest.mock import Mock, call

import pytest

import streamlink.plugins
import tests.plugin
from streamlink.options import Argument, Arguments

# noinspection PyProtectedMember
from streamlink.plugin.plugin import (
    HIGH_PRIORITY,
    LOW_PRIORITY,
    NO_PRIORITY,
    NORMAL_PRIORITY,
    Matcher,
    Matchers,
    Plugin,
    pluginargument,
    pluginmatcher,
)
from streamlink.session import Streamlink
from streamlink.session.plugins import StreamlinkPlugins
from streamlink.utils.args import boolean, comma_list_filter
from tests.plugin.testplugin import TestPlugin as _TestPlugin


PATH_BUILTINPLUGINS = Path(streamlink.plugins.__path__[0])
PATH_TESTPLUGINS = Path(tests.plugin.__path__[0])
PATH_TESTPLUGINS_OVERRIDE = PATH_TESTPLUGINS / "override"


class _Plugin(Plugin):
    def _get_streams(self):  # pragma: no cover
        pass


@pytest.fixture(autouse=True)
def caplog(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(1, "streamlink")
    return caplog


@pytest.fixture(scope="module")
def fake_plugin():
    @pluginmatcher(re.compile(r"fake"))
    @pluginargument("foo")
    @pluginargument("bar")
    class FakePlugin(_Plugin):
        __module__ = "streamlink.plugins.fake"

    return FakePlugin


def test_empty(caplog: pytest.LogCaptureFixture, session: Streamlink):
    assert session.plugins.get_names() == []
    assert session.plugins.get_loaded() == {}
    assert caplog.record_tuples == []


def test_set_get_del(session: Streamlink, fake_plugin: type[Plugin]):
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


def test_update_clear(session: Streamlink, fake_plugin: type[Plugin]):
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


def test_iter_arguments(session: Streamlink, fake_plugin: type[Plugin]):
    session.plugins.update({"fake": fake_plugin})
    assert [(name, [arg.argument_name(name) for arg in args]) for name, args in session.plugins.iter_arguments()] == [
        ("fake", ["--fake-foo", "--fake-bar"]),
    ]


class TestLoad:
    def test_load_builtin(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, fake_plugin: type[Plugin]):
        mock = Mock(return_value={"fake": fake_plugin})
        monkeypatch.setattr(StreamlinkPlugins, "_load_plugins_from_path", mock)
        session = Streamlink(plugins_builtin=True, plugins_lazy=False)

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

    def test_load_path_testplugins_override(self, caplog: pytest.LogCaptureFixture, session: Streamlink):
        assert session.plugins.load_path(PATH_TESTPLUGINS)
        assert "testplugin" in session.plugins
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
                f"Plugin testplugin is being overridden by {PATH_TESTPLUGINS_OVERRIDE / 'testplugin.py'}"
                + " (sha256:47d9c5ec4167565db13aae76f2fbedcf961f5fca386e60c4384ee5e92714b5f3)",
            ),
        ]

    def test_load_path_testplugins_override_matchers(self, caplog: pytest.LogCaptureFixture, session: Streamlink):
        assert _TestPlugin.matchers
        session.plugins._matchers.update({"testplugin": _TestPlugin.matchers})

        assert "testplugin" not in session.plugins
        assert session.plugins.get_names() == ["testplugin"]
        assert caplog.record_tuples == []

        assert session.plugins.load_path(PATH_TESTPLUGINS)
        assert session.plugins.get_names() == ["testplugin"]
        assert session.plugins["testplugin"].__name__ == "TestPlugin"
        assert session.plugins["testplugin"].__module__ == "streamlink.plugins.testplugin"
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.session",
                "info",
                f"Plugin testplugin is being overridden by {PATH_TESTPLUGINS / 'testplugin.py'}"
                + " (sha256:088c9f6ddbe5ff046c0ea1ce0cacb7baff46189d153cf3f149b2e023ddf66f6c)",
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


class TestLoadPluginsData:
    @pytest.fixture()
    def session(self, monkeypatch: pytest.MonkeyPatch, fake_plugin: type[Plugin], metadata_files: Mock):
        class MockStreamlinkPlugins(StreamlinkPlugins):
            def load_builtin(self):
                self._plugins.update({"fake": fake_plugin})
                return True

        monkeypatch.setattr("streamlink.session.session.StreamlinkPlugins", MockStreamlinkPlugins)

        return Streamlink(plugins_builtin=True, plugins_lazy=True)

    @pytest.fixture(autouse=True)
    def metadata_files(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, pluginsdata: str | None):
        options = getattr(request, "param", {})
        package_record = options.get("package-record", True)
        mode = options.get("package-record-hash-mode", "sha256")
        filehash = options.get("package-record-hash-value", None)

        mock = Mock(return_value=[])
        monkeypatch.setattr("importlib.metadata.files", mock)

        if not package_record or pluginsdata is None:
            yield mock
            return

        if filehash is None:
            # https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-record-file
            digest = hashlib.sha256(pluginsdata.encode("utf-8")).digest()
            filehash = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

        packagepath = PackagePath("streamlink", "plugins", "_plugins.json")
        packagepath.hash = FileHash(f"{mode}={filehash}")

        mock.return_value = [packagepath]
        yield mock

        assert mock.call_args_list == [call("streamlink")]

    @pytest.fixture()
    def pluginsdata(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        data = getattr(request, "param", "{}")

        mock = Mock()
        monkeypatch.setattr("streamlink.session.plugins._PLUGINSDATA_PATH", mock)

        if data is None:
            mock.read_bytes.side_effect = FileNotFoundError
        else:
            mock.read_bytes.return_value = data.encode("utf-8")

        return data

    # noinspection PyTestParametrized
    @pytest.mark.parametrize(
        ("metadata_files", "pluginsdata", "logs"),
        [
            pytest.param(
                {},
                None,
                [],
                id="empty-json-file",
            ),
            pytest.param(
                {"package-record": False},
                """{}""",
                [],
                id="no-package-record",
            ),
            pytest.param(
                {"package-record-hash-mode": "unknown"},
                """{}""",
                [("streamlink.session", "error", "Unknown plugins data hash mode, falling back to loading all plugins")],
                id="invalid-package-record-hash-mode",
            ),
            pytest.param(
                {"package-record-hash-value": "invalid"},
                """{}""",
                [("streamlink.session", "error", "Plugins data checksum mismatch, falling back to loading all plugins")],
                id="invalid-package-record-hash-value",
            ),
        ],
        indirect=["metadata_files", "pluginsdata"],
    )
    def test_fallback_load_builtin(self, caplog: pytest.LogCaptureFixture, session: Streamlink, logs: list):
        assert session.plugins.get_names() == ["fake"]
        assert [(record.name, record.levelname, record.message) for record in caplog.get_records(when="setup")] == logs

    # noinspection JsonStandardCompliance
    @pytest.mark.parametrize(
        "pluginsdata",
        [
            pytest.param(
                # language=json
                """
                    // foo
                    // bar
                    {
                        "testplugin": {
                            "matchers": [
                                {"pattern": "foo"}
                            ],
                            "arguments": []
                        }
                    }
                """,
                id="json-comments",
            ),
        ],
        indirect=True,
    )
    def test_strip_json_comment(self, caplog: pytest.LogCaptureFixture, session: Streamlink, pluginsdata: str):
        assert "fake" not in session.plugins
        assert "testplugin" not in session.plugins
        assert session.plugins.get_names() == ["testplugin"]
        assert [(record.name, record.levelname, record.message) for record in caplog.get_records(when="setup")] == []

    @pytest.mark.parametrize(
        "pluginsdata",
        [
            pytest.param(
                # language=json
                """
                    {
                        "testpluginA": {
                            "matchers": [
                                {"pattern": "foo"},
                                {"pattern": "bar", "flags": 64, "priority": 10, "name": "bar"}
                            ],
                            "arguments": []
                        },
                        "testpluginB": {
                            "matchers": [
                                {"pattern": "baz"}
                            ],
                            "arguments": []
                        }
                    }
                """,
                id="matchers",
            ),
        ],
        indirect=True,
    )
    def test_matchers(self, caplog: pytest.LogCaptureFixture, session: Streamlink, pluginsdata: str):
        assert "fake" not in session.plugins
        assert "testpluginA" not in session.plugins
        assert "testpluginB" not in session.plugins
        assert session.plugins.get_names() == ["testpluginA", "testpluginB"]
        assert [(record.name, record.levelname, record.message) for record in caplog.get_records(when="setup")] == []

        matchers_a = Matchers()
        matchers_a.add(Matcher(pattern=re.compile(r"foo"), priority=NORMAL_PRIORITY, name=None))
        matchers_a.add(Matcher(pattern=re.compile(r"bar", re.VERBOSE), priority=10, name="bar"))
        matchers_b = Matchers()
        matchers_b.add(Matcher(pattern=re.compile(r"baz"), priority=NORMAL_PRIORITY, name=None))
        assert list(session.plugins.iter_matchers()) == [("testpluginA", matchers_a), ("testpluginB", matchers_b)]

    @pytest.mark.parametrize(
        "pluginsdata",
        [
            pytest.param(
                # language=json
                """
                    {
                        "success": {
                            "matchers": [{"pattern": "foo"}],
                            "arguments": []
                        },
                        "fail": {
                            "matchers": [{"pattern": {"invalid": "type"}}],
                            "arguments": []
                        }
                    }
                """,
                id="matchers",
            ),
        ],
        indirect=True,
    )
    def test_matchers_failure(self, caplog: pytest.LogCaptureFixture, session: Streamlink, pluginsdata: str):
        assert "fake" in session.plugins
        assert "success" not in session.plugins
        assert "fail" not in session.plugins
        assert session.plugins.get_names() == ["fake"]
        assert [name for name, matchers in session.plugins.iter_matchers()] == ["fake"]
        assert [(record.name, record.levelname, record.message) for record in caplog.get_records(when="setup")] == [
            ("streamlink.session", "error", "Error while loading pluginmatcher data from JSON"),
        ]

    @pytest.mark.parametrize(
        "pluginsdata",
        [
            pytest.param(
                # language=json
                """
                    {
                        "empty": {
                            "matchers": [{"pattern": "foo"}]
                        },
                        "testpluginA": {
                            "matchers": [{"pattern": "bar"}],
                            "arguments": [
                                {
                                    "name": "foo",
                                    "action": "store",
                                    "nargs": 1,
                                    "default": "foo",
                                    "choices": ["foo", "bar"],
                                    "required": true,
                                    "help": "foo",
                                    "metavar": "FOO",
                                    "dest": "oof",
                                    "argument_name": "oof"
                                },
                                {
                                    "name": "bar",
                                    "const": "bar"
                                }
                            ]
                        },
                        "testpluginB": {
                            "matchers": [{"pattern": "baz"}],
                            "arguments": [
                                {
                                    "name": "invalid",
                                    "type": "type_which_does_not_exist"
                                },
                                {
                                    "name": "bool",
                                    "type": "bool"
                                },
                                {
                                    "name": "cmf",
                                    "type": "comma_list_filter",
                                    "type_args": [["1", "2", "3"]],
                                    "type_kwargs": {"unique": true}
                                }
                            ]
                        }
                    }
                """,
                id="arguments",
            ),
        ],
        indirect=True,
    )
    def test_arguments(self, caplog: pytest.LogCaptureFixture, session: Streamlink, pluginsdata: str):
        assert "fake" not in session.plugins
        assert "testpluginA" not in session.plugins
        assert "testpluginB" not in session.plugins
        assert session.plugins.get_names() == ["empty", "testpluginA", "testpluginB"]
        assert [(record.name, record.levelname, record.message) for record in caplog.get_records(when="setup")] == []

        # arguments are added in reverse order:
        # `Arguments` does this because of the reverse order of the @pluginargument decorator
        arguments_a = Arguments()
        arguments_a.add(
            Argument(
                name="bar",
                const="bar",
            ),
        )
        arguments_a.add(
            Argument(
                name="foo",
                action="store",
                nargs=1,
                default="foo",
                choices=["foo", "bar"],
                required=True,
                help="foo",
                metavar="FOO",
                dest="oof",
                argument_name="oof",
            ),
        )
        arguments_b = Arguments()
        arguments_b.add(
            Argument(
                name="cmf",
                type=comma_list_filter(["1", "2", "3"], unique=True),
            ),
        )
        arguments_b.add(
            Argument(
                name="bool",
                type=boolean,
            ),
        )
        assert list(session.plugins.iter_arguments()) == [("testpluginA", arguments_a), ("testpluginB", arguments_b)]

    @pytest.mark.parametrize(
        "pluginsdata",
        [
            pytest.param(
                # language=json
                """
                    {
                        "success": {
                            "matchers": [{"pattern": "foo"}],
                            "arguments": [{"name": "foo"}]
                        },
                        "fail": {
                            "matchers": [{"pattern": "bar"}],
                            "arguments": [{"name": {"invalid": "type"}}]
                        }
                    }
                """,
                id="arguments",
            ),
        ],
        indirect=True,
    )
    def test_arguments_failure(self, caplog: pytest.LogCaptureFixture, session: Streamlink, pluginsdata: str):
        assert "fake" in session.plugins
        assert "success" not in session.plugins
        assert "fail" not in session.plugins
        assert session.plugins.get_names() == ["fake"]
        assert [name for name, arguments in session.plugins.iter_arguments()] == ["fake"]
        assert [(record.name, record.levelname, record.message) for record in caplog.get_records(when="setup")] == [
            ("streamlink.session", "error", "Error while loading pluginargument data from JSON"),
        ]


class TestMatchURL:
    def test_priority(self, session: Streamlink):
        @pluginmatcher(priority=HIGH_PRIORITY, pattern=re.compile(r"^(high|normal|low|no)$"))
        class HighPriority(_Plugin):
            pass

        @pluginmatcher(priority=NORMAL_PRIORITY, pattern=re.compile(r"^(normal|low|no)$"))
        class NormalPriority(_Plugin):
            pass

        @pluginmatcher(priority=LOW_PRIORITY, pattern=re.compile(r"^(low|no)$"))
        class LowPriority(_Plugin):
            pass

        @pluginmatcher(priority=NO_PRIORITY, pattern=re.compile(r"^no$"))
        class NoPriority(_Plugin):
            pass

        session.plugins.update({
            "high": HighPriority,
            "normal": NormalPriority,
            "low": LowPriority,
            "no": NoPriority,
        })

        assert session.plugins.match_url("no") == ("high", HighPriority)
        assert session.plugins.match_url("low") == ("high", HighPriority)
        assert session.plugins.match_url("normal") == ("high", HighPriority)
        assert session.plugins.match_url("high") == ("high", HighPriority)

        del session.plugins["high"]

        assert session.plugins.match_url("no") == ("normal", NormalPriority)
        assert session.plugins.match_url("low") == ("normal", NormalPriority)
        assert session.plugins.match_url("normal") == ("normal", NormalPriority)
        assert session.plugins.match_url("high") is None

    def test_no_priority(self, session: Streamlink):
        @pluginmatcher(priority=NO_PRIORITY, pattern=re.compile(r"^no$"))
        class NoPriority(_Plugin):
            pass

        session.plugins.update({
            "no": NoPriority,
        })
        assert session.plugins.match_url("no") is None


class TestMatchURLLoadLazy:
    @pytest.fixture(autouse=True)
    def _pluginsdir(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("streamlink.session.plugins._PLUGINS_PATH", PATH_TESTPLUGINS)

    @pytest.fixture()
    def _loaded_plugins(self, session: Streamlink):
        # loaded built-in or custom plugin
        session.plugins.update({"testplugin": _TestPlugin})
        assert session.plugins.get_loaded() == {"testplugin": _TestPlugin}

    @pytest.fixture()
    def _loaded_matchers(self, session: Streamlink):
        matchers = cast(Matchers, _TestPlugin.matchers)
        session.plugins._matchers.update({"testplugin": matchers})
        assert session.plugins.get_loaded() == {}
        assert session.plugins.get_names() == ["testplugin"]

    @pytest.mark.usefixtures("_loaded_plugins")
    def test_loaded(self, caplog: pytest.LogCaptureFixture, session: Streamlink):
        assert session.plugins.match_url("http://test.se") == ("testplugin", _TestPlugin)
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == []

    @pytest.mark.usefixtures("_loaded_matchers")
    def test_load(self, caplog: pytest.LogCaptureFixture, session: Streamlink):
        lookup = session.plugins.match_url("http://test.se")
        assert lookup is not None
        name, plugin = lookup
        assert name == "testplugin"
        # can't compare plugin classes here due to exec_module(), so just compare module name, matchers and arguments
        assert plugin.__module__ == "streamlink.plugins.testplugin"
        assert plugin.matchers == _TestPlugin.matchers
        assert plugin.arguments == _TestPlugin.arguments
        assert "testplugin" in session.plugins.get_loaded()
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            ("streamlink.session", "debug", "Loading plugin: testplugin"),
        ]

    @pytest.mark.usefixtures("_loaded_matchers")
    def test_fail_builtin(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, session: Streamlink):
        path = str(PATH_TESTPLUGINS / "testplugin.py")
        mock = Mock(side_effect=ImportError("", path=path))
        monkeypatch.setattr("streamlink.session.plugins.exec_module", mock)

        assert session.plugins.match_url("http://test.se") is None
        assert session.plugins.get_loaded() == {}
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            ("streamlink.session", "debug", "Loading plugin: testplugin"),
            ("streamlink.session", "error", f"Failed to load plugin testplugin from {path}\n"),
        ]
