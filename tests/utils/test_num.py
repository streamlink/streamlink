from __future__ import annotations

import math
from contextlib import nullcontext
from typing import Any

import pytest

from streamlink.utils.num import to_float


class TestToFloat:
    class Pi:
        def __float__(self):
            return math.pi

    raises_typeerror = pytest.raises(TypeError)
    raises_overflowerror = pytest.raises(OverflowError)
    raises_valueerror_convert_str = pytest.raises(ValueError, match=r"could not convert string to float")
    raises_valueerror_nan = pytest.raises(ValueError, match=r"^NaN values are not allowed$")
    raises_valueerror_inf = pytest.raises(ValueError, match=r"^Infinity values are not allowed$")

    @pytest.mark.parametrize(
        ("value", "raises"),
        [
            pytest.param(None, raises_typeerror, id="none"),
            pytest.param({}, raises_typeerror, id="TypeError"),
            pytest.param(10**9999, raises_overflowerror, id="OverflowError"),
            pytest.param("", raises_valueerror_convert_str, id="empty"),
            pytest.param("invalid", raises_valueerror_convert_str, id="ValueError-1"),
            pytest.param("foo123", raises_valueerror_convert_str, id="ValueError-2"),
            pytest.param("123foo", raises_valueerror_convert_str, id="ValueError-3"),
            pytest.param("True", raises_valueerror_convert_str, id="bool-as-str"),
            pytest.param("0b11", raises_valueerror_convert_str, id="no-binary"),
            pytest.param("0o11", raises_valueerror_convert_str, id="no-octal"),
            pytest.param("0x11", raises_valueerror_convert_str, id="no-hexadecimal"),
            pytest.param("NaN", raises_valueerror_nan, id="nan-disallowed"),
            pytest.param("-NaN", raises_valueerror_nan, id="nan-negative-disallowed"),
            pytest.param(math.nan, raises_valueerror_nan, id="nan-obj-disallowed"),
            pytest.param("Infinity", raises_valueerror_inf, id="infinity-disallowed"),
            pytest.param("-Infinity", raises_valueerror_inf, id="infinity-negative-disallowed"),
            pytest.param(math.inf, raises_valueerror_inf, id="infinity-obj-disallowed"),
            pytest.param("1e9999", raises_valueerror_inf, id="rounded-to-infinity-disallowed"),
        ],
    )
    @pytest.mark.parametrize(
        "raise_on_error",
        [
            pytest.param(True, id="raise-on-error"),
            pytest.param(False, id="no-raise-on-error"),
        ],
    )
    def test_invalid(self, value: Any, raises: nullcontext, raise_on_error: bool):
        if not raise_on_error:
            raises = nullcontext()
        with raises:
            assert to_float(value, raise_on_error=raise_on_error) is None

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(" 123 ", 123.0, id="int"),
            pytest.param(" 123.45 ", 123.45, id="float"),
            pytest.param(" .123 ", 0.123, id="float-no-whole-number"),
            pytest.param(" 123. ", 123.0, id="float-no-decimal-place"),
            pytest.param(" -123 ", -123.0, id="int-negative"),
            pytest.param(" -123.45 ", -123.45, id="float-negative"),
            pytest.param(" +123 ", 123.0, id="int-positive"),
            pytest.param(" +123.45 ", 123.45, id="float-positive"),
            pytest.param(" 1e10 ", 1e10, id="exponent-notation"),
            pytest.param(" 1e-10 ", 1e-10, id="exponent-notation-negative"),
            pytest.param(" 1e+10 ", 1e10, id="exponent-notation-positive"),
            pytest.param("011", 11, id="leading-zero"),
            pytest.param("1_2.3_4", 12.34, id="digit-separators"),
            pytest.param(123, 123.0, id="obj-int"),
            pytest.param(123.45, 123.45, id="obj-float"),
            pytest.param(Pi(), math.pi, id="__float__"),
        ],
    )
    def test_floats(self, value: Any, expected: float):
        res = to_float(value)
        assert type(res) is float
        assert res == expected

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("NaN"),
            pytest.param("-NaN"),
            pytest.param(math.nan),
        ],
    )
    def test_nan(self, value: str):
        res = to_float(value, allow_nan=True)
        assert res is not None
        assert math.isnan(res)

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("Infinity"),
            pytest.param("-Infinity"),
            pytest.param("Inf"),
            pytest.param("-Inf"),
            pytest.param("1e9999"),
            pytest.param(math.inf),
        ],
    )
    def test_inf(self, value: str):
        res = to_float(value, allow_inf=True)
        assert res is not None
        assert math.isinf(res)
