from collections import OrderedDict

from streamlink.utils.url import update_qsd, update_scheme, url_concat, url_equal


def test_update_scheme():
    assert update_scheme("https://other.com/bar", "//example.com/foo") == "https://example.com/foo", "should become https"
    assert update_scheme("http://other.com/bar", "//example.com/foo") == "http://example.com/foo", "should become http"
    assert update_scheme("https://other.com/bar", "http://example.com/foo") == "http://example.com/foo", "should remain http"
    assert update_scheme("https://other.com/bar", "example.com/foo") == "https://example.com/foo", "should become https"


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
    assert update_qsd("http://test.se", OrderedDict([("one", ""), ("two", "")])) == "http://test.se?one=&two=", \
        "should add empty params"
    assert update_qsd("http://test.se?one=", {"one": None}) == "http://test.se?one=", "should leave empty params unchanged"
    assert update_qsd("http://test.se?one=", keep_blank_values=False) == "http://test.se", "should strip blank params"
    assert update_qsd("http://test.se?one=&two=", {"one": None}, keep_blank_values=False) == "http://test.se?one=", \
        "should leave one"
    assert update_qsd("http://test.se?&two=", {"one": ''}, keep_blank_values=False) == "http://test.se?one=", \
        "should set one blank"
    assert update_qsd("http://test.se?one=", {"two": 2}) == "http://test.se?one=&two=2"
