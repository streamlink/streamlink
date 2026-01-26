from __future__ import annotations

import ssl
from operator import itemgetter
from socket import AF_INET, AF_INET6
from ssl import SSLContext
from typing import TYPE_CHECKING
from unittest.mock import Mock, PropertyMock, call

import pytest
import requests
import requests_mock as rm
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.response import HTTPResponse

from streamlink.exceptions import PluginError, StreamlinkDeprecationWarning
from streamlink.session.http import HTTPSession, SSLContextAdapter, TLSNoDHAdapter, TLSSecLevel1Adapter
from streamlink.session.http_useragents import DEFAULT


if TYPE_CHECKING:
    from streamlink import Streamlink


_original_allowed_gai_family = urllib3.util.connection.allowed_gai_family  # type: ignore[attr-defined]


class TestUrllib3Overrides:
    @pytest.fixture(scope="class")
    def httpsession(self) -> HTTPSession:
        return HTTPSession()

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            pytest.param(
                "https://foo/bar%3F?baz%21",
                "https://foo/bar%3F?baz%21",
                id="keep-encoded-reserved-characters",
            ),
            pytest.param(
                "https://foo/%62%61%72?%62%61%7A",
                "https://foo/bar?baz",
                id="decode-encoded-unreserved-characters",
            ),
            pytest.param(
                "https://foo/bär?bäz",
                "https://foo/b%C3%A4r?b%C3%A4z",
                id="encode-other-characters",
            ),
            pytest.param(
                "https://foo/b%c3%a4r?b%c3%a4z",
                "https://foo/b%c3%a4r?b%c3%a4z",
                id="keep-percent-encodings-with-lowercase-characters",
            ),
            pytest.param(
                "https://foo/b%C3%A4r?b%C3%A4z",
                "https://foo/b%C3%A4r?b%C3%A4z",
                id="keep-percent-encodings-with-uppercase-characters",
            ),
            pytest.param(
                "https://foo/%?%",
                "https://foo/%25?%25",
                id="empty-percent-encodings-without-valid-encodings",
            ),
            pytest.param(
                "https://foo/%0?%0",
                "https://foo/%250?%250",
                id="incomplete-percent-encodings-without-valid-encodings",
            ),
            pytest.param(
                "https://foo/%zz?%zz",
                "https://foo/%25zz?%25zz",
                id="invalid-percent-encodings-without-valid-encodings",
            ),
            pytest.param(
                "https://foo/%3F%?%3F%",
                "https://foo/%253F%25?%253F%25",
                id="empty-percent-encodings-with-valid-encodings",
            ),
            pytest.param(
                "https://foo/%3F%0?%3F%0",
                "https://foo/%253F%250?%253F%250",
                id="incomplete-percent-encodings-with-valid-encodings",
            ),
            pytest.param(
                "https://foo/%3F%zz?%3F%zz",
                "https://foo/%253F%25zz?%253F%25zz",
                id="invalid-percent-encodings-with-valid-encodings",
            ),
        ],
    )
    def test_encode_invalid_chars(self, httpsession: HTTPSession, url: str, expected: str):
        req = requests.Request(method="GET", url=url)
        prep = httpsession.prepare_request(req)
        assert prep.url == expected


class TestHTTPSession:
    def test_session_init(self):
        session = HTTPSession()
        assert session.headers.get("User-Agent") == DEFAULT
        assert session.timeout == 20.0
        assert "file://" in session.adapters.keys()

    def test_read_timeout(self, monkeypatch: pytest.MonkeyPatch):
        mock_sleep = Mock()
        mock_request = Mock(side_effect=requests.Timeout)
        monkeypatch.setattr("streamlink.session.http.time.sleep", mock_sleep)
        monkeypatch.setattr("streamlink.session.http.Session.request", mock_request)

        session = HTTPSession()
        with pytest.raises(PluginError, match=r"^Unable to open URL: http://localhost/"):
            session.get("http://localhost/", timeout=123, retries=3, retry_backoff=2, retry_max_backoff=5)

        assert mock_request.call_args_list == [
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
        ]
        assert mock_sleep.call_args_list == [
            call(2),
            call(4),
            call(5),
        ]

    @pytest.mark.parametrize("encoding", ["UTF-32BE", "UTF-32LE", "UTF-16BE", "UTF-16LE", "UTF-8"])
    def test_determine_json_encoding(self, recwarn: pytest.WarningsRecorder, encoding: str):
        data = "Hello world, Γειά σου Κόσμε, こんにちは世界".encode(encoding)  # noqa: RUF001
        assert HTTPSession.determine_json_encoding(data) == encoding
        assert [(record.category, str(record.message)) for record in recwarn.list] == [
            (StreamlinkDeprecationWarning, "Deprecated HTTPSession.determine_json_encoding() call"),
        ]

    @pytest.mark.parametrize(
        ("encoding", "override"),
        [
            ("utf-32-be", None),
            ("utf-32-le", None),
            ("utf-16-be", None),
            ("utf-16-le", None),
            ("utf-8", None),
            # With byte order mark (BOM)
            ("utf-16", None),
            ("utf-32", None),
            ("utf-8-sig", None),
            # Override
            ("utf-8", "utf-8"),
            ("cp949", "cp949"),
        ],
    )
    def test_json(self, monkeypatch: pytest.MonkeyPatch, encoding: str, override: str | None):
        mock_content = PropertyMock(return_value='{"test": "Α and Ω"}'.encode(encoding))  # noqa: RUF001
        monkeypatch.setattr("requests.Response.content", mock_content)

        res = requests.Response()
        res.encoding = override

        assert HTTPSession.json(res) == {"test": "Α and Ω"}  # noqa: RUF001

    @pytest.mark.parametrize(
        ("content_type", "encoding", "content", "expected"),
        [
            pytest.param(
                "text/html",
                None,
                b"B\xe4r",
                "ISO-8859-1",
                id="default-iso-8859-1-charset-for-text",
            ),
            pytest.param(
                "application/json",
                None,
                b"B\xc3\xa4r",
                "utf-8",
                id="default-utf-8-charset-for-json",
            ),
            pytest.param(
                'text/html; charset="ISO-8859-1"',
                None,
                b"B\xe4r",
                "ISO-8859-1",
                id="declared-iso-8859-1-charset",
            ),
            pytest.param(
                'text/html; charset="utf-8"',
                None,
                b"B\xc3\xa4r",
                "utf-8",
                id="declared-utf-8-charset",
            ),
            pytest.param(
                "text/html",
                "utf-8",
                b"B\xc3\xa4r",
                "utf-8",
                id="override-missing-charset",
            ),
            pytest.param(
                'text/html; charset="ISO-8859-1"',
                "utf-8",
                b"B\xc3\xa4r",
                "utf-8",
                id="override-incorrect-charset",
            ),
            pytest.param(
                'text/html; charset="utf-8"',
                "utf-8",
                b"B\xc3\xa4r",
                "utf-8",
                id="override-same-charset",
            ),
        ],
    )
    @pytest.mark.parametrize("method", ["get", "post", "head", "put", "patch", "delete"])
    def test_encoding_override(
        self,
        requests_mock: rm.Mocker,
        method: str,
        content_type: str,
        encoding: str,
        content: bytes,
        expected: str,
    ):
        requests_mock.register_uri(rm.ANY, "http://mocked", headers={"Content-Type": content_type}, content=content)
        httpsession = HTTPSession()
        res = getattr(httpsession, method)("http://mocked", encoding=encoding)
        assert res.encoding == expected
        assert res.text == "Bär"

    def test_set_interface(self):
        session = HTTPSession()
        session.mount("custom://", TLSNoDHAdapter())

        a_http, a_https, a_custom, a_file = itemgetter("http://", "https://", "custom://", "file://")(session.adapters)
        assert isinstance(a_http, HTTPAdapter)
        assert isinstance(a_https, HTTPAdapter)
        assert isinstance(a_custom, HTTPAdapter)
        assert not isinstance(a_file, HTTPAdapter)

        assert a_http.poolmanager.connection_pool_kw.get("source_address") is None
        assert a_https.poolmanager.connection_pool_kw.get("source_address") is None
        assert a_custom.poolmanager.connection_pool_kw.get("source_address") is None

        session.set_interface(interface="my-interface")
        assert a_http.poolmanager.connection_pool_kw.get("source_address") == ("my-interface", 0)
        assert a_https.poolmanager.connection_pool_kw.get("source_address") == ("my-interface", 0)
        assert a_custom.poolmanager.connection_pool_kw.get("source_address") == ("my-interface", 0)

        session.set_interface(interface="")
        assert a_http.poolmanager.connection_pool_kw.get("source_address") is None
        assert a_https.poolmanager.connection_pool_kw.get("source_address") is None
        assert a_custom.poolmanager.connection_pool_kw.get("source_address") is None

        session.set_interface(interface=None)
        assert a_http.poolmanager.connection_pool_kw.get("source_address") is None
        assert a_https.poolmanager.connection_pool_kw.get("source_address") is None
        assert a_custom.poolmanager.connection_pool_kw.get("source_address") is None

        # doesn't raise
        session.set_interface(interface=None)

    def test_set_address_family(self, monkeypatch: pytest.MonkeyPatch):
        session = HTTPSession()
        mock_urllib3_util_connection = Mock(allowed_gai_family=_original_allowed_gai_family)
        monkeypatch.setattr("streamlink.session.http.urllib3_util_connection", mock_urllib3_util_connection)

        assert mock_urllib3_util_connection.allowed_gai_family is _original_allowed_gai_family

        session.set_address_family(family=AF_INET)
        assert mock_urllib3_util_connection.allowed_gai_family is not _original_allowed_gai_family
        assert mock_urllib3_util_connection.allowed_gai_family() is AF_INET

        session.set_address_family(family=None)
        assert mock_urllib3_util_connection.allowed_gai_family is _original_allowed_gai_family

        session.set_address_family(family=AF_INET6)
        assert mock_urllib3_util_connection.allowed_gai_family is not _original_allowed_gai_family
        assert mock_urllib3_util_connection.allowed_gai_family() is AF_INET6

        session.set_address_family(family=None)
        assert mock_urllib3_util_connection.allowed_gai_family is _original_allowed_gai_family


class TestHTTPAdapters:
    @staticmethod
    def _has_dh_ciphers(ssl_context: SSLContext):
        return any(cipher["kea"] == "kx-dhe" for cipher in ssl_context.get_ciphers())

    @staticmethod
    def _has_weak_digest_ciphers(ssl_context: SSLContext):
        return any(cipher["digest"] == "sha1" for cipher in ssl_context.get_ciphers())

    def test_sslcontextadapter(self):
        adapter = SSLContextAdapter()
        ssl_context = adapter.poolmanager.connection_pool_kw.get("ssl_context")
        assert isinstance(ssl_context, SSLContext)
        assert self._has_dh_ciphers(ssl_context)
        assert not self._has_weak_digest_ciphers(ssl_context)

    def test_tlsnodhadapter(self):
        adapter = TLSNoDHAdapter()
        ssl_context = adapter.poolmanager.connection_pool_kw.get("ssl_context")
        assert isinstance(ssl_context, SSLContext)
        assert not self._has_dh_ciphers(ssl_context)
        assert not self._has_weak_digest_ciphers(ssl_context)

    def test_tlsseclevel1adapter(self):
        adapter = TLSSecLevel1Adapter()
        ssl_context = adapter.poolmanager.connection_pool_kw.get("ssl_context")
        assert isinstance(ssl_context, SSLContext)
        assert self._has_dh_ciphers(ssl_context)
        assert self._has_weak_digest_ciphers(ssl_context)

    @pytest.mark.parametrize("proxy", ["http", "socks4", "socks5"])
    def test_proxymanager_ssl_context(self, proxy: str):
        adapter = SSLContextAdapter()
        proxymanager = adapter.proxy_manager_for(f"{proxy}://")
        ssl_context_poolmanager = adapter.poolmanager.connection_pool_kw.get("ssl_context")
        ssl_context_proxymanager = proxymanager.connection_pool_kw.get("ssl_context")
        assert ssl_context_poolmanager is ssl_context_proxymanager


class TestHTTPSessionVerifyAndCustomSSLContext:
    @pytest.fixture()
    def adapter(self, session: Streamlink):
        # The http-disable-dh session option mounts the TLSNoDHAdapter with a custom SSLContext
        session.set_option("http-disable-dh", True)

        adapter = session.http.adapters.get("https://")
        assert isinstance(adapter, TLSNoDHAdapter)

        return adapter

    @pytest.fixture(autouse=True)
    def _fake_request(self, monkeypatch: pytest.MonkeyPatch, session: Streamlink, adapter: HTTPAdapter):
        class FakeHTTPResponse(HTTPResponse):
            def stream(self, *_, **__):
                yield b"mocked"

        # Can't use requests_mock here, as it monkeypatches the adapter's send() method, which we want to test
        req = requests.PreparedRequest()
        resp = FakeHTTPResponse(status=200)
        # noinspection PyTypeChecker
        response = adapter.build_response(req, resp)
        monkeypatch.setattr("requests.adapters.HTTPAdapter.send", Mock(return_value=response))

        assert session.http.get("https://mocked/").text == "mocked"

    @pytest.mark.parametrize(
        ("session", "check_hostname", "verify_mode"),
        [
            pytest.param({"http-ssl-verify": True}, True, ssl.CERT_REQUIRED, id="verify"),
            pytest.param({"http-ssl-verify": False}, False, ssl.CERT_NONE, id="no-verify"),
        ],
        indirect=["session"],
    )
    def test_ssl_context_attributes(
        self,
        session: Streamlink,
        adapter: HTTPAdapter,
        check_hostname: bool,
        verify_mode: ssl.VerifyMode,
    ):
        assert session.http.verify is session.get_option("http-ssl-verify")

        ssl_context = adapter.poolmanager.connection_pool_kw.get("ssl_context")
        assert isinstance(ssl_context, SSLContext)
        assert ssl_context.check_hostname is check_hostname
        assert ssl_context.verify_mode is verify_mode
