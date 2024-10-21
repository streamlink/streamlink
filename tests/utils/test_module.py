import sys
from pathlib import Path

import pytest

from streamlink.utils.module import load_module


# used in the import test to verify that this module was imported
__test_marker__ = "test_marker"

_here = Path(__file__).parent


@pytest.mark.parametrize(
    ("name", "path", "expected"),
    [
        pytest.param(
            "some_module",
            _here / "does_not_exist",
            ImportError(
                f"Not a package path: {_here / 'does_not_exist'}",
                path=str(_here / "does_not_exist"),
            ),
            id="no-package",
        ),
        pytest.param(
            "does_not_exist",
            _here,
            ImportError(
                "No module named 'does_not_exist'",
                name="does_not_exist",
                path=str(_here),
            ),
            id="no-module",
        ),
    ],
)
def test_load_module_importerror(name: str, path: Path, expected: ImportError):
    with pytest.raises(ImportError) as cm:
        load_module(name, path)
    assert cm.value.msg == expected.msg
    assert cm.value.name == expected.name
    assert cm.value.path == expected.path


def test_load_module():
    name = __name__.split(".")[-1]

    try:
        assert __name__ in sys.modules
        assert name not in sys.modules

        prev = sys.modules[__name__]
        mod1 = load_module(name, Path(__file__).parent)
        assert name in sys.modules
        assert mod1 is sys.modules[name]
        assert prev is sys.modules[__name__]
        assert mod1 is not sys.modules[__name__]

        assert "__test_marker__" in mod1.__dict__
        assert mod1.__test_marker__ == sys.modules[__name__].__test_marker__

        mod2 = load_module(name, Path(__file__).parent)
        assert mod2 is mod1

        mod3 = load_module(name, Path(__file__).parent, override=True)
        assert mod1 is not sys.modules[name]
        assert mod3 is sys.modules[name]
        assert prev is sys.modules[__name__]
        assert mod3 is not sys.modules[__name__]

        assert "__test_marker__" in mod3.__dict__
        assert mod3.__test_marker__ == sys.modules[__name__].__test_marker__

    finally:
        sys.modules.pop(name, None)
