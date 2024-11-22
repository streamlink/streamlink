import re
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests_mock as rm

import tests.plugin
from streamlink.exceptions import NoPluginError, StreamlinkDeprecationWarning
from streamlink.options import Options
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.session import Streamlink
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


PATH_TESTPLUGINS = Path(tests.plugin.__path__[0])


class TestPluginsDeprecations:
    def test_get_plugins(self, monkeypatch: pytest.MonkeyPatch, recwarn: pytest.WarningsRecorder, session: Streamlink):
        mock = Mock(return_value={})
        monkeypatch.setattr(session.plugins, "get_loaded", mock)
        assert session.get_plugins() == {}
        assert mock.call_count == 1
        assert [(record.filename, record.category, str(record.message)) for record in recwarn.list] == [
            (
                __file__,
                StreamlinkDeprecationWarning,
                "`Streamlink.get_plugins()` has been deprecated in favor of `Streamlink.plugins.get_loaded()`",
            ),
        ]

    def test_load_builtin_plugins(self, monkeypatch: pytest.MonkeyPatch, recwarn: pytest.WarningsRecorder, session: Streamlink):
        mock = Mock(return_value={})
        monkeypatch.setattr(session.plugins, "load_builtin", mock)
        assert session.load_builtin_plugins() is None
        assert mock.call_count == 1
        assert [(record.filename, record.category, str(record.message)) for record in recwarn.list] == [
            (
                __file__,
                StreamlinkDeprecationWarning,
                "`Streamlink.load_builtin_plugins()` has been deprecated in favor of the `plugins_builtin` keyword argument",
            ),
        ]

    def test_load_plugins(self, recwarn: pytest.WarningsRecorder, session: Streamlink):
        session.load_plugins(str(PATH_TESTPLUGINS))
        assert session.plugins.get_names() == ["testplugin"]
        assert session.plugins["testplugin"].__name__ == "TestPlugin"
        assert session.plugins["testplugin"].__module__ == "streamlink.plugins.testplugin"
        assert [(record.filename, record.category, str(record.message)) for record in recwarn.list] == [
            (
                __file__,
                StreamlinkDeprecationWarning,
                "`Streamlink.load_plugins()` has been deprecated in favor of `Streamlink.plugins.load_path()`",
            ),
        ]


class _EmptyPlugin(Plugin):
    def _get_streams(self):
        pass  # pragma: no cover


class TestResolveURL:
    @pytest.fixture(autouse=True)
    def _load_plugins(self, session: Streamlink):
        session.plugins.load_path(PATH_TESTPLUGINS)

    @pytest.fixture(autouse=True)
    def requests_mock(self, requests_mock: rm.Mocker):
        return requests_mock

    def test_resolve_url(self, recwarn: pytest.WarningsRecorder, session: Streamlink):
        _pluginname, pluginclass, resolved_url = session.resolve_url("http://test.se/channel")

        assert issubclass(pluginclass, Plugin)
        assert pluginclass is session.plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"
        assert hasattr(session.resolve_url, "cache_info"), "resolve_url has a lookup cache"
        assert recwarn.list == []

    def test_resolve_url_noplugin(self, requests_mock: rm.Mocker, session: Streamlink):
        requests_mock.get("http://invalid2", status_code=301, headers={"Location": "http://invalid3"})

        with pytest.raises(NoPluginError):
            session.resolve_url("http://invalid1")
        with pytest.raises(NoPluginError):
            session.resolve_url("http://invalid2")

    def test_resolve_url_redirected(self, requests_mock: rm.Mocker, session: Streamlink):
        requests_mock.request("HEAD", "http://redirect1", status_code=501)
        requests_mock.request("GET", "http://redirect1", status_code=301, headers={"Location": "http://redirect2"})
        requests_mock.request("GET", "http://redirect2", status_code=301, headers={"Location": "http://test.se/channel"})
        requests_mock.request("GET", "http://test.se/channel", content=b"")

        _pluginname, pluginclass, resolved_url = session.resolve_url("http://redirect1")
        assert issubclass(pluginclass, Plugin)
        assert pluginclass is session.plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"

    def test_resolve_url_no_redirect(self, session: Streamlink):
        _pluginname, pluginclass, resolved_url = session.resolve_url_no_redirect("http://test.se/channel")
        assert issubclass(pluginclass, Plugin)
        assert pluginclass is session.plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"

    def test_resolve_url_no_redirect_noplugin(self, session: Streamlink):
        with pytest.raises(NoPluginError):
            session.resolve_url_no_redirect("http://invalid")

    def test_resolve_url_scheme(self, session: Streamlink):
        @pluginmatcher(re.compile(r"http://insecure"))
        class PluginHttp(_EmptyPlugin):
            pass

        @pluginmatcher(re.compile(r"https://secure"))
        class PluginHttps(_EmptyPlugin):
            pass

        session.plugins.update({
            "insecure": PluginHttp,
            "secure": PluginHttps,
        })

        with pytest.raises(NoPluginError):
            session.resolve_url("insecure")
        assert session.resolve_url("http://insecure")[1] is PluginHttp
        with pytest.raises(NoPluginError):
            session.resolve_url("https://insecure")

        assert session.resolve_url("secure")[1] is PluginHttps
        with pytest.raises(NoPluginError):
            session.resolve_url("http://secure")
        assert session.resolve_url("https://secure")[1] is PluginHttps


class TestStreams:
    @pytest.fixture(autouse=True)
    def _load_plugins(self, session: Streamlink):
        session.plugins.load_path(PATH_TESTPLUGINS)

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
