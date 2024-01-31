import re
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests_mock as rm

import tests.plugin
from streamlink.exceptions import NoPluginError
from streamlink.options import Options
from streamlink.plugin import HIGH_PRIORITY, LOW_PRIORITY, NO_PRIORITY, NORMAL_PRIORITY, Plugin, pluginmatcher
from streamlink.session import Streamlink
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


PATH_TESTPLUGINS = Path(tests.plugin.__path__[0])
PATH_TESTPLUGINS_OVERRIDE = PATH_TESTPLUGINS / "override"


class TestLoadPlugins:
    @pytest.fixture(autouse=True)
    def caplog(self, caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
        caplog.set_level(1, "streamlink")
        return caplog

    def test_load_plugins(self, caplog: pytest.LogCaptureFixture, session: Streamlink):
        session.load_plugins(str(PATH_TESTPLUGINS))
        plugins = session.get_plugins()
        assert list(plugins.keys()) == ["testplugin"]
        assert plugins["testplugin"].__name__ == "TestPlugin"
        assert plugins["testplugin"].__module__ == "streamlink.plugins.testplugin"
        assert caplog.records == []

    def test_load_plugins_override(self, caplog: pytest.LogCaptureFixture, session: Streamlink):
        session.load_plugins(str(PATH_TESTPLUGINS))
        session.load_plugins(str(PATH_TESTPLUGINS_OVERRIDE))
        plugins = session.get_plugins()
        assert list(plugins.keys()) == ["testplugin"]
        assert plugins["testplugin"].__name__ == "TestPluginOverride"
        assert plugins["testplugin"].__module__ == "streamlink.plugins.testplugin"
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.session",
                "debug",
                f"Plugin testplugin is being overridden by {PATH_TESTPLUGINS_OVERRIDE / 'testplugin.py'}",
            ),
        ]

    def test_load_plugins_builtin(self):
        session = Streamlink()
        plugins = session.get_plugins()
        assert "twitch" in plugins
        assert plugins["twitch"].__module__ == "streamlink.plugins.twitch"

    @pytest.mark.parametrize(("side_effect", "raises", "logs"), [
        pytest.param(
            ImportError,
            nullcontext(),
            [
                (
                    "streamlink.session",
                    "error",
                    f"Failed to load plugin testplugin from {PATH_TESTPLUGINS}",
                    True,
                ),
                (
                    "streamlink.session",
                    "error",
                    f"Failed to load plugin testplugin_invalid from {PATH_TESTPLUGINS}",
                    True,
                ),
                (
                    "streamlink.session",
                    "error",
                    f"Failed to load plugin testplugin_missing from {PATH_TESTPLUGINS}",
                    True,
                ),
            ],
            id="ImportError",
        ),
        pytest.param(
            SyntaxError,
            pytest.raises(SyntaxError),
            [],
            id="SyntaxError",
        ),
    ])
    def test_load_plugins_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        side_effect: Exception,
        raises: nullcontext,
        logs: list,
    ):
        monkeypatch.setattr("streamlink.session.session.Streamlink.load_builtin_plugins", Mock())
        monkeypatch.setattr("streamlink.session.session.exec_module", Mock(side_effect=side_effect))
        session = Streamlink()
        with raises:
            session.load_plugins(str(PATH_TESTPLUGINS))
        assert session.get_plugins() == {}
        assert [(record.name, record.levelname, record.message, bool(record.exc_info)) for record in caplog.records] == logs


class _EmptyPlugin(Plugin):
    def _get_streams(self):
        pass  # pragma: no cover


class TestResolveURL:
    @pytest.fixture(autouse=True)
    def _load_builtins(self, session: Streamlink):
        session.load_plugins(str(PATH_TESTPLUGINS))

    @pytest.fixture(autouse=True)
    def requests_mock(self, requests_mock: rm.Mocker):
        return requests_mock

    def test_resolve_url(self, recwarn: pytest.WarningsRecorder, session: Streamlink):
        plugins = session.get_plugins()
        _pluginname, pluginclass, resolved_url = session.resolve_url("http://test.se/channel")

        assert issubclass(pluginclass, Plugin)
        assert pluginclass is plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"
        assert hasattr(session.resolve_url, "cache_info"), "resolve_url has a lookup cache"
        assert recwarn.list == []

    def test_resolve_url__noplugin(self, requests_mock: rm.Mocker, session: Streamlink):
        requests_mock.get("http://invalid2", status_code=301, headers={"Location": "http://invalid3"})

        with pytest.raises(NoPluginError):
            session.resolve_url("http://invalid1")
        with pytest.raises(NoPluginError):
            session.resolve_url("http://invalid2")

    def test_resolve_url__redirected(self, requests_mock: rm.Mocker, session: Streamlink):
        requests_mock.request("HEAD", "http://redirect1", status_code=501)
        requests_mock.request("GET", "http://redirect1", status_code=301, headers={"Location": "http://redirect2"})
        requests_mock.request("GET", "http://redirect2", status_code=301, headers={"Location": "http://test.se/channel"})
        requests_mock.request("GET", "http://test.se/channel", content=b"")

        plugins = session.get_plugins()
        _pluginname, pluginclass, resolved_url = session.resolve_url("http://redirect1")
        assert issubclass(pluginclass, Plugin)
        assert pluginclass is plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"

    def test_resolve_url_no_redirect(self, session: Streamlink):
        plugins = session.get_plugins()
        _pluginname, pluginclass, resolved_url = session.resolve_url_no_redirect("http://test.se/channel")
        assert issubclass(pluginclass, Plugin)
        assert pluginclass is plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"

    def test_resolve_url_no_redirect__noplugin(self, session: Streamlink):
        with pytest.raises(NoPluginError):
            session.resolve_url_no_redirect("http://invalid")

    def test_resolve_url_scheme(self, session: Streamlink):
        @pluginmatcher(re.compile("http://insecure"))
        class PluginHttp(_EmptyPlugin):
            pass

        @pluginmatcher(re.compile("https://secure"))
        class PluginHttps(_EmptyPlugin):
            pass

        session.plugins = {
            "insecure": PluginHttp,
            "secure": PluginHttps,
        }

        with pytest.raises(NoPluginError):
            session.resolve_url("insecure")
        assert session.resolve_url("http://insecure")[1] is PluginHttp
        with pytest.raises(NoPluginError):
            session.resolve_url("https://insecure")

        assert session.resolve_url("secure")[1] is PluginHttps
        with pytest.raises(NoPluginError):
            session.resolve_url("http://secure")
        assert session.resolve_url("https://secure")[1] is PluginHttps

    def test_resolve_url_priority(self, session: Streamlink):
        @pluginmatcher(priority=HIGH_PRIORITY, pattern=re.compile(
            "https://(high|normal|low|no)$",
        ))
        class HighPriority(_EmptyPlugin):
            pass

        @pluginmatcher(priority=NORMAL_PRIORITY, pattern=re.compile(
            "https://(normal|low|no)$",
        ))
        class NormalPriority(_EmptyPlugin):
            pass

        @pluginmatcher(priority=LOW_PRIORITY, pattern=re.compile(
            "https://(low|no)$",
        ))
        class LowPriority(_EmptyPlugin):
            pass

        @pluginmatcher(priority=NO_PRIORITY, pattern=re.compile(
            "https://(no)$",
        ))
        class NoPriority(_EmptyPlugin):
            pass

        session.plugins = {
            "high": HighPriority,
            "normal": NormalPriority,
            "low": LowPriority,
            "no": NoPriority,
        }
        no = session.resolve_url_no_redirect("no")[1]
        low = session.resolve_url_no_redirect("low")[1]
        normal = session.resolve_url_no_redirect("normal")[1]
        high = session.resolve_url_no_redirect("high")[1]

        assert no is HighPriority
        assert low is HighPriority
        assert normal is HighPriority
        assert high is HighPriority

        session.resolve_url.cache_clear()
        session.plugins = {
            "no": NoPriority,
        }
        with pytest.raises(NoPluginError):
            session.resolve_url_no_redirect("no")


class TestStreams:
    @pytest.fixture(autouse=True)
    def _load_builtins(self, session: Streamlink):
        session.load_plugins(str(PATH_TESTPLUGINS))

    def test_streams(self, session: Streamlink):
        streams = session.streams("http://test.se/channel")

        assert "best" in streams
        assert "worst" in streams
        assert streams["best"] is streams["1080p"]
        assert streams["worst"] is streams["350k"]
        assert isinstance(streams["http"], HTTPStream)
        assert isinstance(streams["hls"], HLSStream)

    def test_streams_options(self, session: Streamlink):
        streams = session.streams("http://test.se/fromoptions", Options({"streamurl": "http://foo/"}))

        assert sorted(streams.keys()) == ["best", "fromoptions", "worst"]
        assert isinstance(streams["fromoptions"], HTTPStream)
        assert streams["fromoptions"].url == "http://foo/"

    def test_stream_types(self, session: Streamlink):
        streams = session.streams("http://test.se/channel", stream_types=["http", "hls"])
        assert isinstance(streams["480p"], HTTPStream)
        assert isinstance(streams["480p_hls"], HLSStream)

        streams = session.streams("http://test.se/channel", stream_types=["hls", "http"])
        assert isinstance(streams["480p"], HLSStream)
        assert isinstance(streams["480p_http"], HTTPStream)

    def test_stream_sorting_excludes(self, session: Streamlink):
        streams = session.streams("http://test.se/channel", sorting_excludes=[])
        assert "best" in streams
        assert "worst" in streams
        assert "best-unfiltered" not in streams
        assert "worst-unfiltered" not in streams
        assert streams["worst"] is streams["350k"]
        assert streams["best"] is streams["1080p"]

        streams = session.streams("http://test.se/channel", sorting_excludes=["1080p", "3000k"])
        assert "best" in streams
        assert "worst" in streams
        assert "best-unfiltered" not in streams
        assert "worst-unfiltered" not in streams
        assert streams["worst"] is streams["350k"]
        assert streams["best"] is streams["1500k"]

        streams = session.streams("http://test.se/channel", sorting_excludes=[">=1080p", ">1500k"])
        assert streams["best"] is streams["1500k"]

        streams = session.streams("http://test.se/channel", sorting_excludes=lambda q: not q.endswith("p"))
        assert streams["best"] is streams["3000k"]

        streams = session.streams("http://test.se/channel", sorting_excludes=lambda q: False)
        assert "best" not in streams
        assert "worst" not in streams
        assert "best-unfiltered" in streams
        assert "worst-unfiltered" in streams
        assert streams["worst-unfiltered"] is streams["350k"]
        assert streams["best-unfiltered"] is streams["1080p"]

        streams = session.streams("http://test.se/UnsortableStreamNames")
        assert "best" not in streams
        assert "worst" not in streams
        assert "best-unfiltered" not in streams
        assert "worst-unfiltered" not in streams
        assert "vod" in streams
        assert "vod_alt" in streams
        assert "vod_alt2" in streams
