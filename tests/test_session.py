import re
from contextlib import nullcontext
from pathlib import Path
from socket import AF_INET, AF_INET6
from typing import Dict
from unittest.mock import Mock

import pytest
import requests_mock as rm
import urllib3
from requests.adapters import HTTPAdapter

import tests.plugin
from streamlink.exceptions import NoPluginError, StreamlinkDeprecationWarning
from streamlink.plugin import HIGH_PRIORITY, LOW_PRIORITY, NO_PRIORITY, NORMAL_PRIORITY, Plugin, pluginmatcher
from streamlink.plugin.api.http_session import TLSNoDHAdapter
from streamlink.session import Streamlink
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


PATH_TESTPLUGINS = Path(tests.plugin.__path__[0])
PATH_TESTPLUGINS_OVERRIDE = PATH_TESTPLUGINS / "override"

_original_allowed_gai_family = urllib3.util.connection.allowed_gai_family  # type: ignore[attr-defined]


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
        monkeypatch.setattr("streamlink.session.Streamlink.load_builtin_plugins", Mock())
        monkeypatch.setattr("streamlink.session.load_module", Mock(side_effect=side_effect))
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
        pluginname, pluginclass, resolved_url = session.resolve_url("http://test.se/channel")

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
        pluginname, pluginclass, resolved_url = session.resolve_url("http://redirect1")
        assert issubclass(pluginclass, Plugin)
        assert pluginclass is plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"

    def test_resolve_url_no_redirect(self, session: Streamlink):
        plugins = session.get_plugins()
        pluginname, pluginclass, resolved_url = session.resolve_url_no_redirect("http://test.se/channel")
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


def test_options(session: Streamlink):
    session.set_option("test_option", "option")
    assert session.get_option("test_option") == "option"
    assert session.get_option("non_existing") is None


def test_options_locale(monkeypatch: pytest.MonkeyPatch, session: Streamlink):
    monkeypatch.setattr("locale.getlocale", lambda: ("C", None))
    assert session.get_option("locale") is None

    localization = session.localization
    assert localization.explicit is False
    assert localization.language_code == "en_US"
    assert localization.country.alpha2 == "US"
    assert localization.country.name == "United States"
    assert localization.language.alpha2 == "en"
    assert localization.language.name == "English"

    session.set_option("locale", "de_DE")
    assert session.get_option("locale") == "de_DE"

    localization = session.localization
    assert localization.explicit is True
    assert localization.language_code == "de_DE"
    assert localization.country.alpha2 == "DE"
    assert localization.country.name == "Germany"
    assert localization.language.alpha2 == "de"
    assert localization.language.name == "German"


class TestOptionsInterface:
    @pytest.fixture()
    def adapters(self, monkeypatch: pytest.MonkeyPatch):
        adapters = {
            scheme: Mock(poolmanager=Mock(connection_pool_kw={}))
            for scheme in ("http://", "https://", "foo://")
        }
        monkeypatch.setattr("streamlink.session.HTTPSession", Mock(return_value=Mock(adapters=adapters)))

        return adapters

    def test_options_interface(self, adapters: Dict[str, Mock], session: Streamlink):
        assert session.get_option("interface") is None

        session.set_option("interface", "my-interface")
        assert adapters["http://"].poolmanager.connection_pool_kw == {"source_address": ("my-interface", 0)}
        assert adapters["https://"].poolmanager.connection_pool_kw == {"source_address": ("my-interface", 0)}
        assert adapters["foo://"].poolmanager.connection_pool_kw == {}
        assert session.get_option("interface") == "my-interface"

        session.set_option("interface", None)
        assert adapters["http://"].poolmanager.connection_pool_kw == {}
        assert adapters["https://"].poolmanager.connection_pool_kw == {}
        assert adapters["foo://"].poolmanager.connection_pool_kw == {}
        assert session.get_option("interface") is None

        # doesn't raise
        session.set_option("interface", None)


def test_options_ipv4_ipv6(monkeypatch: pytest.MonkeyPatch, session: Streamlink):
    mock_urllib3_util_connection = Mock(allowed_gai_family=_original_allowed_gai_family)
    monkeypatch.setattr("streamlink.session.urllib3_util_connection", mock_urllib3_util_connection)

    assert session.get_option("ipv4") is False
    assert session.get_option("ipv6") is False
    assert mock_urllib3_util_connection.allowed_gai_family is _original_allowed_gai_family

    session.set_option("ipv4", True)
    assert session.get_option("ipv4") is True
    assert session.get_option("ipv6") is False
    assert mock_urllib3_util_connection.allowed_gai_family is not _original_allowed_gai_family
    assert mock_urllib3_util_connection.allowed_gai_family() is AF_INET

    session.set_option("ipv4", False)
    assert session.get_option("ipv4") is False
    assert session.get_option("ipv6") is False
    assert mock_urllib3_util_connection.allowed_gai_family is _original_allowed_gai_family

    session.set_option("ipv6", True)
    assert session.get_option("ipv4") is False
    assert session.get_option("ipv6") is True
    assert mock_urllib3_util_connection.allowed_gai_family is not _original_allowed_gai_family
    assert mock_urllib3_util_connection.allowed_gai_family() is AF_INET6

    session.set_option("ipv6", False)
    assert session.get_option("ipv4") is False
    assert session.get_option("ipv6") is False
    assert mock_urllib3_util_connection.allowed_gai_family is _original_allowed_gai_family

    session.set_option("ipv4", True)
    session.set_option("ipv6", False)
    assert session.get_option("ipv4") is True
    assert session.get_option("ipv6") is False
    assert mock_urllib3_util_connection.allowed_gai_family is _original_allowed_gai_family


def test_options_http_disable_dh(session: Streamlink):
    assert isinstance(session.http.adapters["https://"], HTTPAdapter)
    assert not isinstance(session.http.adapters["https://"], TLSNoDHAdapter)

    session.set_option("http-disable-dh", True)
    assert isinstance(session.http.adapters["https://"], TLSNoDHAdapter)

    session.set_option("http-disable-dh", False)
    assert isinstance(session.http.adapters["https://"], HTTPAdapter)
    assert not isinstance(session.http.adapters["https://"], TLSNoDHAdapter)


class TestOptionsHttpProxy:
    @pytest.fixture()
    def _no_deprecation(self, recwarn: pytest.WarningsRecorder):
        yield
        assert recwarn.list == []

    @pytest.fixture()
    def _logs_deprecation(self, recwarn: pytest.WarningsRecorder):
        yield
        assert [(record.category, str(record.message), record.filename) for record in recwarn.list] == [
            (
                StreamlinkDeprecationWarning,
                "The `https-proxy` option has been deprecated in favor of a single `http-proxy` option",
                __file__,
            ),
        ]

    @pytest.mark.usefixtures("_no_deprecation")
    def test_https_proxy_default(self, session: Streamlink):
        session.set_option("http-proxy", "http://testproxy.com")

        assert session.http.proxies["http"] == "http://testproxy.com"
        assert session.http.proxies["https"] == "http://testproxy.com"

    @pytest.mark.usefixtures("_logs_deprecation")
    def test_https_proxy_set_first(self, session: Streamlink):
        session.set_option("https-proxy", "https://testhttpsproxy.com")
        session.set_option("http-proxy", "http://testproxy.com")

        assert session.http.proxies["http"] == "http://testproxy.com"
        assert session.http.proxies["https"] == "http://testproxy.com"

    @pytest.mark.usefixtures("_logs_deprecation")
    def test_https_proxy_default_override(self, session: Streamlink):
        session.set_option("http-proxy", "http://testproxy.com")
        session.set_option("https-proxy", "https://testhttpsproxy.com")

        assert session.http.proxies["http"] == "https://testhttpsproxy.com"
        assert session.http.proxies["https"] == "https://testhttpsproxy.com"

    @pytest.mark.usefixtures("_logs_deprecation")
    def test_https_proxy_set_only(self, session: Streamlink):
        session.set_option("https-proxy", "https://testhttpsproxy.com")

        assert session.http.proxies["http"] == "https://testhttpsproxy.com"
        assert session.http.proxies["https"] == "https://testhttpsproxy.com"

    @pytest.mark.usefixtures("_no_deprecation")
    def test_http_proxy_socks(self, session: Streamlink):
        session.set_option("http-proxy", "socks5://localhost:1234")

        assert session.http.proxies["http"] == "socks5://localhost:1234"
        assert session.http.proxies["https"] == "socks5://localhost:1234"

    @pytest.mark.usefixtures("_logs_deprecation")
    def test_https_proxy_socks(self, session: Streamlink):
        session.set_option("https-proxy", "socks5://localhost:1234")

        assert session.http.proxies["http"] == "socks5://localhost:1234"
        assert session.http.proxies["https"] == "socks5://localhost:1234"

    @pytest.mark.usefixtures("_no_deprecation")
    def test_get_http_proxy(self, session: Streamlink):
        session.http.proxies["http"] = "http://testproxy1.com"
        session.http.proxies["https"] = "http://testproxy2.com"
        assert session.get_option("http-proxy") == "http://testproxy1.com"

    @pytest.mark.usefixtures("_logs_deprecation")
    def test_get_https_proxy(self, session: Streamlink):
        session.http.proxies["http"] = "http://testproxy1.com"
        session.http.proxies["https"] = "http://testproxy2.com"
        assert session.get_option("https-proxy") == "http://testproxy2.com"

    @pytest.mark.usefixtures("_logs_deprecation")
    def test_https_proxy_get_directly(self, session: Streamlink):
        # The DeprecationWarning's origin must point to this call, even without the set_option() wrapper
        session.options.get("https-proxy")

    @pytest.mark.usefixtures("_logs_deprecation")
    def test_https_proxy_set_directly(self, session: Streamlink):
        # The DeprecationWarning's origin must point to this call, even without the set_option() wrapper
        session.options.set("https-proxy", "https://foo")


class TestOptionsKeyEqualsValue:
    @pytest.fixture()
    def option(self, request, session: Streamlink):
        option, attr = request.param
        httpsessionattr = getattr(session.http, attr)
        assert session.get_option(option) is httpsessionattr
        assert "foo" not in httpsessionattr
        assert "bar" not in httpsessionattr
        yield option
        assert httpsessionattr.get("foo") == "foo=bar"
        assert httpsessionattr.get("bar") == "123"

    @pytest.mark.parametrize(
        "option",
        [
            pytest.param(("http-cookies", "cookies"), id="http-cookies"),
            pytest.param(("http-headers", "headers"), id="http-headers"),
            pytest.param(("http-query-params", "params"), id="http-query-params"),
        ],
        indirect=["option"],
    )
    def test_dict(self, session: Streamlink, option: str):
        session.set_option(option, {"foo": "foo=bar", "bar": "123"})

    @pytest.mark.parametrize(
        ("option", "value"),
        [
            pytest.param(("http-cookies", "cookies"), "foo=foo=bar;bar=123;baz", id="http-cookies"),
            pytest.param(("http-headers", "headers"), "foo=foo=bar;bar=123;baz", id="http-headers"),
            pytest.param(("http-query-params", "params"), "foo=foo=bar&bar=123&baz", id="http-query-params"),
        ],
        indirect=["option"],
    )
    def test_string(self, session: Streamlink, option: str, value: str):
        session.set_option(option, value)


@pytest.mark.parametrize(
    ("option", "attr", "default", "value"),
    [
        ("http-ssl-cert", "cert", None, "foo"),
        ("http-ssl-verify", "verify", True, False),
        ("http-trust-env", "trust_env", True, False),
        ("http-timeout", "timeout", 20.0, 30.0),
    ],
)
def test_options_http_other(session: Streamlink, option: str, attr: str, default, value):
    httpsessionattr = getattr(session.http, attr)
    assert httpsessionattr == default
    assert session.get_option(option) == httpsessionattr

    session.set_option(option, value)
    assert session.get_option(option) == value


class TestOptionsDocumentation:
    @pytest.fixture()
    def docstring(self, session: Streamlink):
        docstring = session.set_option.__doc__
        assert docstring is not None
        return docstring

    def test_default_option_is_documented(self, session: Streamlink, docstring: str):
        assert session.options.keys()
        for option in session.options:
            assert f"* - {option}" in docstring, f"Option '{option}' is documented"

    def test_documented_option_exists(self, session: Streamlink, docstring: str):
        options = session.options
        setters = options._MAP_SETTERS.keys()
        documented = re.compile(r"\* - (\S+)").findall(docstring)[1:]
        assert documented
        for option in documented:
            assert option in options or option in setters, f"Documented option '{option}' exists"
