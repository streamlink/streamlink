import pytest

from streamlink.utils.data import search_dict


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ((["one", "two"], "one"), []),
        (({"two": "test2"}, "one"), []),
        (({"one": "test1", "two": "test2"}, "one"), ["test1"]),
        (({"one": {"inner": "test1"}, "two": "test2"}, "inner"), ["test1"]),
        (({"one": [{"inner": "test1"}], "two": "test2"}, "inner"), ["test1"]),
        (({"one": [{"inner": "test1"}], "two": {"inner": "test2"}}, "inner"), ["test1", "test2"]),
    ],
)
def test_search_dict(args, expected):
    assert list(search_dict(*args)) == expected
