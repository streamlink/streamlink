import sys
from typing import List

import pytest


_TEST_PRIORITIES = (
    "tests/testutils/",
    "tests/utils/",
    None,
    "tests/stream/",
    "tests/test_plugins.py",
    "tests/plugins/",
    "tests/cli/",
)


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
