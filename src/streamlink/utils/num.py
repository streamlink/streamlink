from __future__ import annotations

import math
from typing import Any, Literal, overload


@overload
def to_float(
    value: Any,
    *,
    allow_nan: bool = False,
    allow_inf: bool = False,
) -> float | None: ...  # pragma: no cover


@overload
def to_float(
    value: Any,
    *,
    allow_nan: bool = False,
    allow_inf: bool = False,
    raise_on_error: Literal[True] = True,
) -> float: ...  # pragma: no cover


@overload
def to_float(
    value: Any,
    *,
    allow_nan: bool = False,
    allow_inf: bool = False,
    raise_on_error: bool = False,
) -> float | None: ...  # pragma: no cover


def to_float(value: Any, *, allow_nan: bool = False, allow_inf: bool = False, raise_on_error: bool = False) -> float | None:
    try:
        num = float(value)
    except (ValueError, TypeError, OverflowError):
        if raise_on_error:
            raise
        return None

    if not allow_nan and math.isnan(num):
        if raise_on_error:
            raise ValueError("NaN values are not allowed")
        return None

    if not allow_inf and math.isinf(num):
        if raise_on_error:
            raise ValueError("Infinity values are not allowed")
        return None

    return num
