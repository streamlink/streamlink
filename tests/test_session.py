import re
import unittest
import warnings
from pathlib import Path
from socket import AF_INET, AF_INET6
from unittest.mock import Mock, call, patch

import pytest
import requests_mock
import urllib3

import tests.plugin
from streamlink import NoPluginError, Streamlink
from streamlink.exceptions import StreamlinkDeprecationWarning
from streamlink.plugin import HIGH_PRIORITY, LOW_PRIORITY, NO_PRIORITY, NORMAL_PRIORITY, Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


PATH_TESTPLUGINS = Path(tests.plugin.__path__[0])
PATH_TESTPLUGINS_OVERRIDE = PATH_TESTPLUGINS / "override"

_original_allowed_gai_family = urllib3.util.connection.allowed_gai_family  # type: ignore[attr-defined]


@pytest.fixture()
def session():
    with patch("streamlink.session.Streamlink.load_builtin_plugins"):
        yield Streamlink()


class EmptyPlugin(Plugin):
    def _get_streams(self):
        pass  # pragma: no cover


# TODO: rewrite using pytest
class TestSession(unittest.TestCase):
    mocker: requests_mock.Mocker

    def setUp(self):
        self.mocker = requests_mock.Mocker()
        self.mocker.register_uri(requests_mock.ANY, requests_mock.ANY, text="")
        self.mocker.start()

    def tearDown(self):
        self.mocker.stop()
        Streamlink.resolve_url.cache_clear()

    def subject(self, load_plugins=True):
        session = Streamlink()
        if load_plugins:
            session.load_plugins(str(PATH_TESTPLUGINS))
            session.load_plugins(str(PATH_TESTPLUGINS_OVERRIDE))

        return session

    # ----

    def test_load_plugins(self):
        session = self.subject()
        plugins = session.get_plugins()
        assert "testplugin" in plugins
        assert "testplugin_missing" not in plugins
        assert "testplugin_invalid" not in plugins

    def test_load_plugins_builtin(self):
        session = self.subject()
        plugins = session.get_plugins()
        assert "twitch" in plugins
        assert plugins["twitch"].__module__ == "streamlink.plugins.twitch"

    @patch("streamlink.session.log")
    def test_load_plugins_override(self, mock_log):
        session = self.subject()
        plugins = session.get_plugins()
        assert "testplugin" in plugins
        assert "testplugin_override" not in plugins
        assert plugins["testplugin"].__name__ == "TestPluginOverride"
        assert plugins["testplugin"].__module__ == "streamlink.plugins.testplugin"
        assert mock_log.debug.call_args_list == [
            call(f"Plugin testplugin is being overridden by {PATH_TESTPLUGINS_OVERRIDE / 'testplugin.py'}"),
        ]

    @patch("streamlink.session.load_module")
    @patch("streamlink.session.log")
    def test_load_plugins_importerror(self, mock_log, mock_load_module):
        mock_load_module.side_effect = ImportError()
        session = self.subject()
        assert not session.get_plugins()
        assert len(mock_log.exception.call_args_list) > 0

    @patch("streamlink.session.load_module")
    @patch("streamlink.session.log")
    def test_load_plugins_syntaxerror(self, mock_log, mock_load_module):
        mock_load_module.side_effect = SyntaxError()
        with pytest.raises(SyntaxError):
            self.subject()

    def test_resolve_url(self):
        session = self.subject()
        plugins = session.get_plugins()

        with warnings.catch_warnings(record=True) as record_warnings:
            pluginname, pluginclass, resolved_url = session.resolve_url("http://test.se/channel")

        assert issubclass(pluginclass, Plugin)
        assert pluginclass is plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"
        assert hasattr(session.resolve_url, "cache_info"), "resolve_url has a lookup cache"
        assert record_warnings == []

    def test_resolve_url__noplugin(self):
        session = self.subject()
        self.mocker.get("http://invalid2", status_code=301, headers={"Location": "http://invalid3"})

        with pytest.raises(NoPluginError):
            session.resolve_url("http://invalid1")
        with pytest.raises(NoPluginError):
            session.resolve_url("http://invalid2")

    def test_resolve_url__redirected(self):
        session = self.subject()
        plugins = session.get_plugins()
        self.mocker.head("http://redirect1", status_code=501)
        self.mocker.get("http://redirect1", status_code=301, headers={"Location": "http://redirect2"})
        self.mocker.head("http://redirect2", status_code=301, headers={"Location": "http://test.se/channel"})

        pluginname, pluginclass, resolved_url = session.resolve_url("http://redirect1")
        assert issubclass(pluginclass, Plugin)
        assert pluginclass is plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"

    def test_resolve_url_no_redirect(self):
        session = self.subject()
        plugins = session.get_plugins()

        pluginname, pluginclass, resolved_url = session.resolve_url_no_redirect("http://test.se/channel")
        assert issubclass(pluginclass, Plugin)
        assert pluginclass is plugins["testplugin"]
        assert resolved_url == "http://test.se/channel"

    def test_resolve_url_no_redirect__noplugin(self):
        session = self.subject()
        with pytest.raises(NoPluginError):
            session.resolve_url_no_redirect("http://invalid")

    def test_resolve_url_scheme(self):
        @pluginmatcher(re.compile("http://insecure"))
        class PluginHttp(EmptyPlugin):
            pass

        @pluginmatcher(re.compile("https://secure"))
        class PluginHttps(EmptyPlugin):
            pass

        session = self.subject(load_plugins=False)
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

    def test_resolve_url_priority(self):
        @pluginmatcher(priority=HIGH_PRIORITY, pattern=re.compile(
            "https://(high|normal|low|no)$",
        ))
        class HighPriority(EmptyPlugin):
            pass

        @pluginmatcher(priority=NORMAL_PRIORITY, pattern=re.compile(
            "https://(normal|low|no)$",
        ))
        class NormalPriority(EmptyPlugin):
            pass

        @pluginmatcher(priority=LOW_PRIORITY, pattern=re.compile(
            "https://(low|no)$",
        ))
        class LowPriority(EmptyPlugin):
            pass

        @pluginmatcher(priority=NO_PRIORITY, pattern=re.compile(
            "https://(no)$",
        ))
        class NoPriority(EmptyPlugin):
            pass

        session = self.subject(load_plugins=False)
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

    def test_resolve_deprecated(self):
        @pluginmatcher(priority=LOW_PRIORITY, pattern=re.compile(
            "https://low",
        ))
        class LowPriority(EmptyPlugin):
            pass

        class DeprecatedNormalPriority(EmptyPlugin):
            # noinspection PyUnusedLocal
            @classmethod
            def can_handle_url(cls, url):
                return True

        class DeprecatedHighPriority(DeprecatedNormalPriority):
            # noinspection PyUnusedLocal
            @classmethod
            def priority(cls, url):
                return HIGH_PRIORITY

        session = self.subject(load_plugins=False)
        session.plugins = {
            "empty": EmptyPlugin,
            "low": LowPriority,
            "dep-normal-one": DeprecatedNormalPriority,
            "dep-normal-two": DeprecatedNormalPriority,
            "dep-high": DeprecatedHighPriority,
        }

        with pytest.warns() as recwarn:
            plugin = session.resolve_url_no_redirect("low")[1]

        assert plugin is DeprecatedHighPriority
        assert [(record.category, str(record.message)) for record in recwarn.list] == [
            (StreamlinkDeprecationWarning, "Resolved plugin dep-normal-one with deprecated can_handle_url API"),
            (StreamlinkDeprecationWarning, "Resolved plugin dep-high with deprecated can_handle_url API"),
        ]

    def test_options(self):
        session = self.subject()
        session.set_option("test_option", "option")
        assert session.get_option("test_option") == "option"
        assert session.get_option("non_existing") is None

        assert session.get_plugin_option("testplugin", "a_option") == "default"
        session.set_plugin_option("testplugin", "another_option", "test")
        assert session.get_plugin_option("testplugin", "another_option") == "test"
        assert session.get_plugin_option("non_existing", "non_existing") is None
        assert session.get_plugin_option("testplugin", "non_existing") is None

    def test_streams(self):
        session = self.subject()
        streams = session.streams("http://test.se/channel")

        assert "best" in streams
        assert "worst" in streams
        assert streams["best"] is streams["1080p"]
        assert streams["worst"] is streams["350k"]
        assert isinstance(streams["http"], HTTPStream)
        assert isinstance(streams["hls"], HLSStream)

    def test_streams_stream_types(self):
        session = self.subject()

        streams = session.streams("http://test.se/channel", stream_types=["http", "hls"])
        assert isinstance(streams["480p"], HTTPStream)
        assert isinstance(streams["480p_hls"], HLSStream)

        streams = session.streams("http://test.se/channel", stream_types=["hls", "http"])
        assert isinstance(streams["480p"], HLSStream)
        assert isinstance(streams["480p_http"], HTTPStream)

    def test_streams_stream_sorting_excludes(self):
        session = self.subject()

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

    def test_set_and_get_locale(self):
        session = Streamlink()
        session.set_option("locale", "en_US")
        assert session.localization.country.alpha2 == "US"
        assert session.localization.language.alpha2 == "en"
        assert session.localization.language_code == "en_US"

    @patch("streamlink.session.HTTPSession")
    def test_interface(self, mock_httpsession):
        adapter_http = Mock(poolmanager=Mock(connection_pool_kw={}))
        adapter_https = Mock(poolmanager=Mock(connection_pool_kw={}))
        adapter_foo = Mock(poolmanager=Mock(connection_pool_kw={}))
        mock_httpsession.return_value = Mock(adapters={
            "http://": adapter_http,
            "https://": adapter_https,
            "foo://": adapter_foo,
        })
        session = self.subject(load_plugins=False)
        assert session.get_option("interface") is None

        session.set_option("interface", "my-interface")
        assert adapter_http.poolmanager.connection_pool_kw == {"source_address": ("my-interface", 0)}
        assert adapter_https.poolmanager.connection_pool_kw == {"source_address": ("my-interface", 0)}
        assert adapter_foo.poolmanager.connection_pool_kw == {}
        assert session.get_option("interface") == "my-interface"

        session.set_option("interface", None)
        assert adapter_http.poolmanager.connection_pool_kw == {}
        assert adapter_https.poolmanager.connection_pool_kw == {}
        assert adapter_foo.poolmanager.connection_pool_kw == {}
        assert session.get_option("interface") is None

    @patch("streamlink.session.urllib3_util_connection", allowed_gai_family=_original_allowed_gai_family)
    def test_ipv4_ipv6(self, mock_urllib3_util_connection):
        session = self.subject(load_plugins=False)
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

    @patch("streamlink.session.urllib3_util_ssl", DEFAULT_CIPHERS="foo:!bar:baz")
    def test_http_disable_dh(self, mock_urllib3_util_ssl):
        session = self.subject(load_plugins=False)
        assert mock_urllib3_util_ssl.DEFAULT_CIPHERS == "foo:!bar:baz"

        session.set_option("http-disable-dh", True)
        assert mock_urllib3_util_ssl.DEFAULT_CIPHERS == "foo:!bar:baz:!DH"

        session.set_option("http-disable-dh", True)
        assert mock_urllib3_util_ssl.DEFAULT_CIPHERS == "foo:!bar:baz:!DH"

        session.set_option("http-disable-dh", False)
        assert mock_urllib3_util_ssl.DEFAULT_CIPHERS == "foo:!bar:baz"


class TestSessionOptionHttpProxy:
    @pytest.fixture()
    def _no_deprecation(self, recwarn: pytest.WarningsRecorder):
        yield
        assert recwarn.list == []

    @pytest.fixture()
    def _logs_deprecation(self, recwarn: pytest.WarningsRecorder):
        yield
        assert [(record.category, str(record.message)) for record in recwarn.list] == [
            (
                StreamlinkDeprecationWarning,
                "The `https-proxy` option has been deprecated in favor of a single `http-proxy` option",
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
