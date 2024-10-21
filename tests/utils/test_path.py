from __future__ import annotations

from pathlib import Path

import pytest

from streamlink.utils.path import resolve_executable


RESOLVE_EXECUTABLE_LOOKUPS = {
    "foo": "/usr/bin/foo",
    "/usr/bin/foo": "/usr/bin/foo",
    "/other/bar": "/other/bar",
}


@pytest.mark.parametrize(
    ("custom", "names", "fallbacks", "expected"),
    [
        pytest.param(
            None,
            [],
            [],
            None,
            id="Empty",
        ),
        pytest.param(
            "foo",
            [],
            [],
            "/usr/bin/foo",
            id="Custom executable success",
        ),
        pytest.param(
            "bar",
            [],
            [],
            None,
            id="Custom executable failure",
        ),
        pytest.param(
            "bar",
            ["foo"],
            ["/usr/bin/foo"],
            None,
            id="Custom executable overrides names+fallbacks",
        ),
        pytest.param(
            None,
            ["bar", "foo"],
            [],
            "/usr/bin/foo",
            id="Default names success",
        ),
        pytest.param(
            None,
            ["bar", "baz"],
            [],
            None,
            id="Default names failure",
        ),
        pytest.param(
            None,
            [],
            ["/usr/bin/unknown", "/other/bar"],
            "/other/bar",
            id="Fallbacks success",
        ),
        pytest.param(
            None,
            [],
            ["/usr/bin/unknown", "/other/baz"],
            None,
            id="Fallbacks failure",
        ),
        pytest.param(
            None,
            ["bar", "foo"],
            ["/usr/bin/bar", "/other/baz"],
            "/usr/bin/foo",
            id="Successful name lookup with fallbacks",
        ),
        pytest.param(
            None,
            ["bar", "baz"],
            ["/usr/bin/bar", "/other/bar"],
            "/other/bar",
            id="Unsuccessful name lookup with successful fallbacks",
        ),
        pytest.param(
            None,
            ["bar", "baz"],
            ["/usr/bin/unknown", "/other/baz"],
            None,
            id="Failure",
        ),
    ],
)
def test_resolve_executable(
    monkeypatch: pytest.MonkeyPatch,
    custom: str | None,
    names: list[str] | None,
    fallbacks: list[str | Path] | None,
    expected: str,
):
    monkeypatch.setattr("streamlink.utils.path.which", RESOLVE_EXECUTABLE_LOOKUPS.get)
    assert resolve_executable(custom, names, fallbacks) == expected
