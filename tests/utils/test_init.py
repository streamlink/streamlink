import importlib.util

import pytest

from streamlink.exceptions import StreamlinkDeprecationWarning


@pytest.mark.parametrize(
    "attr",
    [
        "LRUCache",
        "search_dict",
        "load_module",
        "NamedPipe",
        "parse_html",
        "parse_json",
        "parse_qsd",
        "parse_xml",
        "absolute_url",
        "prepend_www",
        "update_qsd",
        "update_scheme",
        "url_concat",
        "url_equal",
    ],
)
def test_deprecated(attr: str):
    spec = importlib.util.find_spec("streamlink.utils", "streamlink")
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.warns(StreamlinkDeprecationWarning):
        item = getattr(module, attr)

    assert item
