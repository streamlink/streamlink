from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from functools import partial
from typing import Any

import pytest
import requests_mock as rm

from streamlink.session import Streamlink


_TEST_CONDITION_MARKERS: Mapping[str, tuple[bool, str] | Callable[[Any], tuple[bool, str]]] = {
    "posix_only": (os.name == "posix", "only applicable on a POSIX OS"),
    "windows_only": (os.name == "nt", "only applicable on Windows"),
    "python": lambda *ver, **_: (  # pragma: no cover
        sys.version_info >= ver,
        f"only applicable on Python {'.'.join(str(v) for v in ver)} and above",
    ),
}

_TEST_PRIORITIES = (
    "build_backend/",
    "tests/testutils/",
    "tests/utils/",
    "tests/session/",
    None,
    "tests/stream/",
    "tests/test_plugins.py",
    "tests/plugins/",
    "tests/cli/",
)


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "posix_only: tests which are only applicable on a POSIX OS")
    config.addinivalue_line("markers", "windows_only: tests which are only applicable on Windows")
    config.addinivalue_line("markers", "python(version): tests which are only applicable on specific Python versions")
    config.addinivalue_line("markers", "nomockedhttprequest: tests where no mocked HTTP request will be made")


def pytest_runtest_setup(item: pytest.Item):
    _check_test_condition(item)


def pytest_collection_modifyitems(items: list[pytest.Item]):  # pragma: no cover
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
    }  # fmt: skip
    items.sort(key=lambda item: priorities.get(item, default))


def _check_test_condition(item: pytest.Item):  # pragma: no cover
    for m in item.iter_markers():
        if m.name not in _TEST_CONDITION_MARKERS:
            continue
        data = _TEST_CONDITION_MARKERS[m.name]
        kwargs = dict(m.kwargs)
        reason = kwargs.pop("reason", None)
        if callable(data):
            cond, msg = data(*m.args, **kwargs)
        else:
            cond, msg = data
        if not cond:
            pytest.skip(msg if not reason else f"{msg} ({reason})")


# ========================
# globally shared fixtures
# ========================


@pytest.fixture()
def session(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    options = getattr(request, "param", {})
    plugins_builtin = options.pop("plugins-builtin", False)
    plugins_lazy = options.pop("plugins-lazy", False)

    session = Streamlink(
        options=options,
        plugins_builtin=plugins_builtin,
        plugins_lazy=plugins_lazy,
    )

    try:
        yield session
    finally:
        Streamlink.resolve_url.cache_clear()


@pytest.fixture()
def requests_mock(requests_mock: rm.Mocker) -> rm.Mocker:
    """
    Override of the default `requests_mock` fixture, with `InvalidRequest` raised on unknown requests
    """
    requests_mock.register_uri(rm.ANY, rm.ANY, exc=rm.exceptions.InvalidRequest)
    return requests_mock


@pytest.fixture()
def os_environ(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    class FakeEnviron(dict):
        def __setitem__(self, key, value):
            if key == "PYTEST_CURRENT_TEST":
                return
            return super().__setitem__(key, value)

    fakeenviron = FakeEnviron(getattr(request, "param", {}))
    monkeypatch.setattr("os.environ", fakeenviron)

    return fakeenviron


@pytest.fixture(autouse=True, scope="session")
def _patch_trio_run():
    import trio  # noqa: PLC0415

    trio_run = trio.run
    # `strict_exception_groups` changed from False to True in `trio==0.25`:
    # Patch `trio.run()` and make older versions of trio behave like `trio>=0.25`
    # as pytest-trio doesn't allow setting custom `trio.run()` args/kwargs
    trio.run = partial(trio.run, strict_exception_groups=True)
    yield
    trio.run = trio_run
