from __future__ import annotations

from urllib.parse import quote

import pytest

# noinspection PyProtectedMember
from streamlink.utils.url import (
    _proxymatcher_to_prio_and_pattern,  # noqa: PLC2701
    absolute_url,
    prepend_www,
    select_proxy,
    update_qsd,
    update_scheme,
    url_concat,
    url_equal,
)


class TestProxyMatcher:
    @pytest.fixture(autouse=True)
    def _reset_cache(self):
        yield
        _proxymatcher_to_prio_and_pattern.cache_clear()

    @pytest.mark.parametrize(
        ("matcher", "url", "expected"),
        [
            # empty
            pytest.param("", "http://host", True, id="empty-matches-http"),
            pytest.param("", "https://host", True, id="empty-matches-https"),
            # "all" matcher, no netloc
            pytest.param("all", "http://host", True, id="all-scheme-matches-http"),
            pytest.param("all", "https://host", True, id="all-scheme-matches-https"),
            # specific scheme, no netloc
            pytest.param("http", "http://host", True, id="http-matches-http"),
            pytest.param("http", "https://host", False, id="http-does-not-match-https"),
            pytest.param("https", "https://host", True, id="https-matches-https"),
            pytest.param("https", "http://host", False, id="https-does-not-match-http"),
            # no scheme, host
            pytest.param("host", "http://host", True, id="no-scheme-matches-http"),
            pytest.param("host", "https://host", True, id="no-scheme-matches-https"),
            pytest.param("host", "https://other", False, id="no-scheme-other-host"),
            pytest.param("host:80", "http://host:80", True, id="no-scheme-host-port"),
            pytest.param("host", "http://host:80", False, id="no-scheme-host-no-implicit-port"),
            # scheme, host and port
            pytest.param("http://host", "http://host", True, id="scheme-host"),
            pytest.param("http://host/foo", "http://host/bar", True, id="ignore-path"),
            pytest.param("HTTP://HOST", "http://host", True, id="case-insensitive"),
            pytest.param("http://host:80", "http://host:80", True, id="scheme-host-port"),
            pytest.param("http://127.0.0.1", "http://127.0.0.1", True, id="scheme-ipv4"),
            pytest.param("http://127.0.0.1:80", "http://127.0.0.1:80", True, id="scheme-ipv4-port"),
            pytest.param("http://[::1]", "http://[::1]", True, id="scheme-ipv6"),
            pytest.param("http://[::1]:80", "http://[::1]:80", True, id="scheme-ipv6-port"),
            pytest.param("http://:80", "http://host:80", True, id="only-port"),
            pytest.param("http://host", "https://host", False, id="other-scheme"),
            pytest.param("http://host", "http://other", False, id="other-host"),
            pytest.param("http://host:80", "http://other:8080", False, id="other-port"),
            pytest.param("http://127.0.0.1", "http://0.0.0.0", False, id="other-ipv4"),
            pytest.param("http://[::1]", "http://[::0]", False, id="other-ipv6"),
            pytest.param("http://host", "http://host:80", True, id="http-implicit-port"),
            pytest.param("https://host", "https://host:443", True, id="https-implicit-port"),
            # wildcards
            pytest.param("http://*", "http://foo.bar.baz", True, id="wildcard-any"),
            pytest.param("http://*:80", "http://foo.bar.baz:80", True, id="wildcard-any-with-port"),
            pytest.param("http://*:80", "http://foo.bar.baz:8080", False, id="wildcard-any-with-port-no-match"),
            pytest.param("http://:80", "http://foo.bar.baz:80", True, id="wildcard-no-host-port"),
            pytest.param("http://*foo", "http://foo", True, id="wildcard"),
            pytest.param("http://*foo", "http://bar.foo", True, id="wildcard-opt-subdomain"),
            pytest.param("http://*foo:80", "http://foo:80", True, id="wildcard-with-port"),
            pytest.param("http://*foo", "http://barfoo", False, id="wildcard-no-match"),
            pytest.param("http://*.foo", "http://bar.foo", True, id="wildcard-subdomain"),
            pytest.param("http://*.foo", "http://foo", False, id="wildcard-subdomain-no-match"),
            pytest.param("http://foo*baz", "http://foobarbaz", False, id="wildcard-invalid"),
            # invalid
            pytest.param("http://[foo]", "http://foo", False, id="invalid-not-an-ipv6"),
            pytest.param("http://foo:bar", "http://foo", False, id="invalid-not-a-port"),
        ],
    )
    def test_matcher(self, matcher: str, url: str, expected: bool):
        assert (select_proxy(url, {matcher: "proxy"}) == "proxy") is expected

    @pytest.mark.parametrize(
        ("proxies", "expected"),
        [
            pytest.param(
                {},
                None,
            ),
            pytest.param(
                {
                    "all": "four",
                    "foo.bar": "three",
                    "https": "two",
                    "https://foo.bar": "one",
                },
                "one",
            ),
            pytest.param(
                {
                    "all": "four",
                    "foo.bar": "three",
                    "https": "two",
                    "https://asdf": "one",
                },
                "two",
            ),
            pytest.param(
                {
                    "all": "four",
                    "foo.bar": "three",
                    "http": "two",
                    "https://asdf": "one",
                },
                "three",
            ),
            pytest.param(
                {
                    "all": "four",
                    "asdf": "three",
                    "http": "two",
                    "https://asdf": "one",
                },
                "four",
            ),
            pytest.param(
                {
                    "asdf": "three",
                    "http": "two",
                    "https://asdf": "one",
                },
                None,
            ),
        ],
    )
    def test_priority(self, proxies: dict[str, str], expected: str | None):
        assert select_proxy("https://foo.bar/baz", proxies) == expected

    @pytest.mark.parametrize(
        ("proxies", "expected"),
        [
            pytest.param(
                {},
                None,
            ),
            pytest.param(
                {
                    "all": "two",
                    "https": "one",
                },
                "one",
            ),
            pytest.param(
                {
                    "all": "two",
                    "http": "one",
                },
                "two",
            ),
        ],
    )
    def test_no_hostname(self, proxies: dict[str, str], expected: str | None):
        assert select_proxy("https://", proxies) == expected


@pytest.mark.parametrize(
    ("baseurl", "url", "expected"),
    [
        ("http://test.se", "/test", "http://test.se/test"),
        ("http://test.se", "http/test.se/test", "http://test.se/http/test.se/test"),
        ("http://test.se", "http://test2.se/test", "http://test2.se/test"),
    ],
)
def test_absolute_url(baseurl, url, expected):
    assert expected == absolute_url(baseurl, url)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://test.se/test", "http://www.test.se/test"),
        ("http://www.test.se", "http://www.test.se"),
    ],
)
def test_prepend_www(url, expected):
    assert expected == prepend_www(url)


@pytest.mark.parametrize(
    ("assertion", "args", "expected"),
    [
        (
            "current scheme overrides target scheme (https)",
            ("https://other.com/bar", "http://example.com/foo"),
            "https://example.com/foo",
        ),
        (
            "current scheme overrides target scheme (http)",
            ("http://other.com/bar", "https://example.com/foo"),
            "http://example.com/foo",
        ),
        (
            "current scheme does not override target scheme if force is False (https)",
            ("http://other.com/bar", "https://example.com/foo", False),
            "https://example.com/foo",
        ),
        (
            "current scheme does not override target scheme if force is False (http)",
            ("https://other.com/bar", "http://example.com/foo", False),
            "http://example.com/foo",
        ),
        (
            "current scheme gets applied to scheme-less target",
            ("https://other.com/bar", "//example.com/foo"),
            "https://example.com/foo",
        ),
        (
            "current scheme gets applied to scheme-less target, even if force is False",
            ("https://other.com/bar", "//example.com/foo", False),
            "https://example.com/foo",
        ),
        (
            "current scheme gets added to target string",
            ("https://other.com/bar", "example.com/foo"),
            "https://example.com/foo",
        ),
        (
            "current scheme gets added to target string, even if force is False",
            ("https://other.com/bar", "example.com/foo", False),
            "https://example.com/foo",
        ),
        (
            "implicit scheme with IPv4+port",
            ("http://", "127.0.0.1:1234/foo"),
            "http://127.0.0.1:1234/foo",
        ),
        (
            "implicit scheme with hostname+port",
            ("http://", "foo.bar:1234/foo"),
            "http://foo.bar:1234/foo",
        ),
        (
            "correctly parses all kinds of schemes",
            ("foo.1+2-bar://baz", "FOO.1+2-BAR://qux"),
            "foo.1+2-bar://qux",
        ),
    ],
)
def test_update_scheme(assertion, args, expected):
    assert update_scheme(*args) == expected, assertion


def test_url_equal():
    assert url_equal("http://test.com/test", "http://test.com/test")
    assert not url_equal("http://test.com/test", "http://test.com/test2")

    assert url_equal("http://test.com/test", "http://test.com/test2", ignore_path=True)
    assert url_equal("http://test.com/test", "https://test.com/test", ignore_scheme=True)
    assert not url_equal("http://test.com/test", "https://test.com/test")

    assert url_equal("http://test.com/test", "http://test.com/test#hello", ignore_fragment=True)
    assert url_equal("http://test.com/test", "http://test2.com/test", ignore_netloc=True)
    assert not url_equal("http://test.com/test", "http://test2.com/test1", ignore_netloc=True)


def test_url_concat():
    assert url_concat("http://test.se", "one", "two", "three") == "http://test.se/one/two/three"
    assert url_concat("http://test.se", "/one", "/two", "/three") == "http://test.se/one/two/three"
    assert url_concat("http://test.se/one", "../two", "three") == "http://test.se/two/three"
    assert url_concat("http://test.se/one", "../two", "../three") == "http://test.se/three"


def test_update_qsd():
    assert update_qsd("http://test.se?one=1&two=3", {"two": 2}) == "http://test.se?one=1&two=2"
    assert update_qsd("http://test.se?one=1&two=3", remove=["two"]) == "http://test.se?one=1"
    assert update_qsd("http://test.se?one=1&two=3", {"one": None}, remove="*") == "http://test.se?one=1"
    assert update_qsd("http://test.se", {"one": "", "two": ""}) == "http://test.se?one=&two=", "should add empty params"
    assert update_qsd("http://test.se?one=", {"one": None}) == "http://test.se?one=", "should leave empty params unchanged"
    assert update_qsd("http://test.se?one=", keep_blank_values=False) == "http://test.se", "should strip blank params"
    assert update_qsd("http://test.se?one=&two=", {"one": None}, keep_blank_values=False) == "http://test.se?one=", \
        "should leave one"  # fmt: skip
    assert update_qsd("http://test.se?&two=", {"one": ""}, keep_blank_values=False) == "http://test.se?one=", \
        "should set one blank"  # fmt: skip
    assert update_qsd("http://test.se?one=", {"two": 2}) == "http://test.se?one=&two=2"

    assert update_qsd("http://test.se?foo=%3F", {"bar": "!"}) == "http://test.se?foo=%3F&bar=%21", \
        "urlencode - encoded URL"  # fmt: skip
    assert update_qsd("http://test.se?foo=?", {"bar": "!"}) == "http://test.se?foo=%3F&bar=%21", \
        "urlencode - fix URL"  # fmt: skip
    assert update_qsd("http://test.se?foo=?", {"bar": "!"}, quote_via=lambda s, *_: s) == "http://test.se?foo=?&bar=!", \
        "urlencode - dummy quote method"  # fmt: skip
    assert update_qsd("http://test.se", {"foo": "/ "}) == "http://test.se?foo=%2F+", \
        "urlencode - default quote_plus"  # fmt: skip
    assert update_qsd("http://test.se", {"foo": "/ "}, safe="/", quote_via=quote) == "http://test.se?foo=/%20", \
        "urlencode - regular quote with reserved slash"  # fmt: skip
    assert update_qsd("http://test.se", {"foo": "/ "}, safe="", quote_via=quote) == "http://test.se?foo=%2F%20", \
        "urlencode - regular quote without reserved slash"  # fmt: skip
