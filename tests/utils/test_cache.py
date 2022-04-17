from streamlink.utils.cache import LRUCache


def test_lru_cache():
    cache = LRUCache(num=3)
    assert cache.get("foo") is None, "Getter returns None for unknown items"

    cache.set("foo", "FOO")
    assert list(cache.cache.items()) == [("foo", "FOO")], "Setter adds new items"

    assert cache.get("foo") == "FOO", "Getter returns correct value of known items"

    cache.set("bar", "BAR")
    cache.set("baz", "BAZ")
    cache.set("qux", "QUX")
    assert list(cache.cache.items()) == [("bar", "BAR"), ("baz", "BAZ"), ("qux", "QUX")], "Setter respects max queue size"

    cache.get("bar")
    assert list(cache.cache.items()) == [("baz", "BAZ"), ("qux", "QUX"), ("bar", "BAR")], "Getter moves known items to the end"

    cache.get("unknown")
    assert list(cache.cache.items()) == [("baz", "BAZ"), ("qux", "QUX"), ("bar", "BAR")], "Getter keeps order on unknown items"

    cache.set("foo", "FOO")
    assert list(cache.cache.items()) == [("qux", "QUX"), ("bar", "BAR"), ("foo", "FOO")], "Setter moves new items to the end"

    cache.set("qux", "QUUX")
    assert list(cache.cache.items()) == [("bar", "BAR"), ("foo", "FOO"), ("qux", "QUUX")], "Setter moves known items to the end"
