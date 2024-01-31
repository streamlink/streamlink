import re
from socket import AF_INET, AF_INET6
from typing import Dict
from unittest.mock import Mock

import pytest
import urllib3
from requests.adapters import HTTPAdapter

from streamlink.exceptions import StreamlinkDeprecationWarning
from streamlink.session import Streamlink
from streamlink.session.http import TLSNoDHAdapter


_original_allowed_gai_family = urllib3.util.connection.allowed_gai_family  # type: ignore[attr-defined]


class TestOptionsDocumentation:
    @pytest.fixture()
    def docstring(self, session: Streamlink):
        docstring = session.options.__doc__
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


def test_session_wrapper_methods(session: Streamlink):
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
        monkeypatch.setattr("streamlink.session.session.HTTPSession", Mock(return_value=Mock(adapters=adapters)))

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
    monkeypatch.setattr("streamlink.session.options.urllib3_util_connection", mock_urllib3_util_connection)

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
        key, attr = request.param
        httpsessionattr = getattr(session.http, attr)
        assert session.get_option(key) is httpsessionattr
        assert "foo" not in httpsessionattr
        assert "bar" not in httpsessionattr
        yield key
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
