from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import pytest


_TESTSUITE_DIRS = {
    "default": [],
    "plugins": [
        Path("tests", "plugins_remote"),
    ],
}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--test-suite",
        type=str,
        choices=set(_TESTSUITE_DIRS.keys()),
        default="default",
        help="""
            Select the test suite:
            - 'default' is the regular test suite with unit and integration tests
            - 'plugins' runs real-world plugin data tests and is only meant to be run by developers
        """,
    )


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    if (
        collection_path.is_dir()
        or collection_path.parent == config.rootpath
        or not any(collection_path.match(matcher) for matcher in config.getini("python_files"))
    ):
        return None

    test_suite: str = config.getoption("--test-suite", "default")
    others: set[str] = set(_TESTSUITE_DIRS.keys()) - {test_suite}
    rel = collection_path.parent.relative_to(config.rootpath)

    if (dirs := _TESTSUITE_DIRS.get(test_suite, [])) and rel not in dirs:
        return True

    if rel in (d for o in others for d in _TESTSUITE_DIRS[o]):
        return True

    return None
