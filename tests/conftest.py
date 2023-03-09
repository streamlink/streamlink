import os
import sys
from typing import Dict, List, Tuple

import pytest


_TEST_CONDITION_MARKERS: Dict[str, Tuple[bool, str]] = {
    "posix_only": (os.name == "posix", "only applicable on a POSIX OS"),
    "windows_only": (os.name == "nt", "only applicable on Windows"),
}

_TEST_PRIORITIES = (
    "tests/testutils/",
    "tests/utils/",
    None,
    "tests/stream/",
    "tests/test_plugins.py",
    "tests/plugins/",
    "tests/cli/",
)


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "posix_only: tests which are only applicable on a POSIX OS")
    config.addinivalue_line("markers", "windows_only: tests which are only applicable on Windows")
    config.addinivalue_line("markers", "nomockedhttprequest: tests where no mocked HTTP request will be made")


def pytest_runtest_setup(item: pytest.Item):
    _check_test_condition(item)


def pytest_collection_modifyitems(items: List[pytest.Item]):  # pragma: no cover
    default = next((idx for idx, string in enumerate(_TEST_PRIORITIES) if string is None), sys.maxsize)
    priorities = {
        item: next(
            (
                idx
                for idx, string in enumerate(_TEST_PRIORITIES)
                if string is not None and item.nodeid.startswith(string)
            ),
            default,
        )
        for item in items
    }
    items.sort(key=lambda item: priorities.get(item, default))


def _check_test_condition(item: pytest.Item):  # pragma: no cover
    for m in item.iter_markers():
        if m.name not in _TEST_CONDITION_MARKERS:
            continue
        cond, msg = _TEST_CONDITION_MARKERS[m.name]
        if not cond:
            pytest.skip(msg if not m.args and not m.kwargs else f"{msg} ({m.kwargs.get('reason') or m.args[0]})")
