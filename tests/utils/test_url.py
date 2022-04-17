from urllib.parse import quote

import pytest

from streamlink.utils.url import absolute_url, prepend_www, update_qsd, update_scheme, url_concat, url_equal


@pytest.mark.parametrize("baseurl,url,expected", [
    ("http://test.se", "/test", "http://test.se/test"),
    ("http://test.se", "http/test.se/test", "http://test.se/http/test.se/test"),
    ("http://test.se", "http://test2.se/test", "http://test2.se/test"),
])
def test_absolute_url(baseurl, url, expected):
    assert expected == absolute_url(baseurl, url)


@pytest.mark.parametrize("url,expected", [
    ("http://test.se/test", "http://www.test.se/test"),
    ("http://www.test.se", "http://www.test.se"),
])
def test_prepend_www(url, expected):
    assert expected == prepend_www(url)


@pytest.mark.parametrize("assertion,args,expected", [
    ("current scheme overrides target scheme (https)",
     ("https://other.com/bar", "http://example.com/foo"),
     "https://example.com/foo"),
    ("current scheme overrides target scheme (http)",
     ("http://other.com/bar", "https://example.com/foo"),
     "http://example.com/foo"),
    ("current scheme does not override target scheme if force is False (https)",
     ("http://other.com/bar", "https://example.com/foo", False),
     "https://example.com/foo"),
    ("current scheme does not override target scheme if force is False (http)",
     ("https://other.com/bar", "http://example.com/foo", False),
     "http://example.com/foo"),
    ("current scheme gets applied to scheme-less target",
     ("https://other.com/bar", "//example.com/foo"),
     "https://example.com/foo"),
    ("current scheme gets applied to scheme-less target, even if force is False",
     ("https://other.com/bar", "//example.com/foo", False),
     "https://example.com/foo"),
    ("current scheme gets added to target string",
     ("https://other.com/bar", "example.com/foo"),
     "https://example.com/foo"),
    ("current scheme gets added to target string, even if force is False",
     ("https://other.com/bar", "example.com/foo", False),
     "https://example.com/foo"),
    ("implicit scheme with IPv4+port",
     ("http://", "127.0.0.1:1234/foo"),
     "http://127.0.0.1:1234/foo"),
    ("implicit scheme with hostname+port",
     ("http://", "foo.bar:1234/foo"),
     "http://foo.bar:1234/foo"),
    ("correctly parses all kinds of schemes",
     ("foo.1+2-bar://baz", "FOO.1+2-BAR://qux"),
     "foo.1+2-bar://qux"),
])
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
    assert update_qsd("http://test.se", dict([("one", ""), ("two", "")])) == "http://test.se?one=&two=", \
        "should add empty params"
    assert update_qsd("http://test.se?one=", {"one": None}) == "http://test.se?one=", "should leave empty params unchanged"
    assert update_qsd("http://test.se?one=", keep_blank_values=False) == "http://test.se", "should strip blank params"
    assert update_qsd("http://test.se?one=&two=", {"one": None}, keep_blank_values=False) == "http://test.se?one=", \
        "should leave one"
    assert update_qsd("http://test.se?&two=", {"one": ''}, keep_blank_values=False) == "http://test.se?one=", \
        "should set one blank"
    assert update_qsd("http://test.se?one=", {"two": 2}) == "http://test.se?one=&two=2"

    assert update_qsd("http://test.se?foo=%3F", {"bar": "!"}) == "http://test.se?foo=%3F&bar=%21", \
        "urlencode - encoded URL"
    assert update_qsd("http://test.se?foo=?", {"bar": "!"}) == "http://test.se?foo=%3F&bar=%21", \
        "urlencode - fix URL"
    assert update_qsd("http://test.se?foo=?", {"bar": "!"}, quote_via=lambda s, *_: s) == "http://test.se?foo=?&bar=!", \
        "urlencode - dummy quote method"
    assert update_qsd("http://test.se", {"foo": "/ "}) == "http://test.se?foo=%2F+", \
        "urlencode - default quote_plus"
    assert update_qsd("http://test.se", {"foo": "/ "}, safe="/", quote_via=quote) == "http://test.se?foo=/%20", \
        "urlencode - regular quote with reserved slash"
    assert update_qsd("http://test.se", {"foo": "/ "}, safe="", quote_via=quote) == "http://test.se?foo=%2F%20", \
        "urlencode - regular quote without reserved slash"
