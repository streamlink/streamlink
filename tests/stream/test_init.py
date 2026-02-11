import importlib.util

import pytest

from streamlink.exceptions import StreamlinkDeprecationWarning


@pytest.mark.parametrize(
    "attr",
    [
        "DASHStream",
        "MuxedStream",
        "HLSStream",
        "MuxedHLSStream",
        "HTTPStream",
        "Stream",
        "StreamIO",
        "StreamIOIterWrapper",
        "StreamIOThreadWrapper",
        "StreamIOWrapper",
    ],
)
def test_deprecated(attr: str):
    spec = importlib.util.find_spec("streamlink.stream", "streamlink")
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.warns(StreamlinkDeprecationWarning):
        item = getattr(module, attr)

    assert item
