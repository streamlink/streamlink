from streamlink.utils.thread import NamedThread


def test_named_thread():
    class One(NamedThread):
        pass

    class Two(NamedThread):
        pass

    assert One().name == "One-0"
    assert One().name == "One-1"
    assert Two().name == "Two-0"
    assert Two().name == "Two-1"

    assert One(name="foo").name == "One-foo-0"
    assert One(name="foo").name == "One-foo-1"
    assert One(name="bar").name == "One-bar-0"
    assert One(name="bar").name == "One-bar-1"
    assert One().name == "One-2"
