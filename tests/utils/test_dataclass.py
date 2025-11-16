from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from streamlink.utils.dataclass import FormattedDataclass
from streamlink.utils.times import fromtimestamp


if TYPE_CHECKING:
    from datetime import datetime, timedelta


@pytest.fixture(scope="module")
def baseclass() -> type:
    @dataclass(kw_only=True)
    class Foo(
        metaclass=FormattedDataclass,
        formatters={
            str: lambda s: f"{s.upper()!r}",
        },
    ):
        foo: str
        bar: int
        baz: float
        qux: str = field(repr=False)
        abc: datetime = field(default=fromtimestamp(0.5))
        xyz: timedelta = field(default=fromtimestamp(1.5) - fromtimestamp(0))

    return Foo


@pytest.fixture(scope="module")
def subclass(baseclass: type) -> type:
    @dataclass(kw_only=True)
    class Bar(
        baseclass,
        metaclass=FormattedDataclass,
        formatters={
            float: lambda x: f"{(x * 2.0):.3f}",
        },
        extra=["oof"],
    ):
        @property
        def oof(self) -> str:
            return self.foo[::-1]

    return Bar


@pytest.fixture(scope="module")
def subsubclass(subclass: type) -> type:
    @dataclass(kw_only=True)
    class Baz(subclass, metaclass=FormattedDataclass, extra=["barbar"]):
        @property
        def barbar(self) -> int:
            return self.bar * self.bar

    return Baz


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        pytest.param(
            "baseclass",
            "Foo(foo='FOO', bar=123, baz=3.142, abc=1970-01-01T00:00:00.500000Z, xyz=0:00:01.500000)",
            id="baseclass",
        ),
        pytest.param(
            "subclass",
            "Bar(foo='FOO', bar=123, baz=6.283, abc=1970-01-01T00:00:00.500000Z, xyz=0:00:01.500000, oof='OOF')",
            id="subclass",
        ),
        pytest.param(
            "subsubclass",
            "Baz(foo='FOO', bar=123, baz=6.283, abc=1970-01-01T00:00:00.500000Z, xyz=0:00:01.500000, oof='OOF', barbar=15129)",
            id="subsubclass",
        ),
    ],
)
def test_serialize(request: pytest.FixtureRequest, fixture: str, expected: str):
    dc = request.getfixturevalue(fixture)
    item = dc(
        foo="foo",
        bar=123,
        baz=math.pi,
        qux="qux",
    )
    assert str(item) == repr(item) == expected
