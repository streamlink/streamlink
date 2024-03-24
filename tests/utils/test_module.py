import sys
from pathlib import Path

import pytest

from streamlink.utils.module import load_module


# used in the import test to verify that this module was imported
__test_marker__ = "test_marker"

_here = Path(__file__).parent


@pytest.mark.parametrize(("name", "path", "expected"), [
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
])
def test_load_module_importerror(name: str, path: Path, expected: ImportError):
    with pytest.raises(ImportError) as cm:
        load_module(name, path)
    assert cm.value.msg == expected.msg
    assert cm.value.name == expected.name
    assert cm.value.path == expected.path


def test_load_module():
    mod = load_module(__name__.split(".")[-1], Path(__file__).parent)
    assert "__test_marker__" in mod.__dict__
    assert mod is not sys.modules[__name__]
    assert mod.__test_marker__ == sys.modules[__name__].__test_marker__
