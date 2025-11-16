from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable, TypeAlias, TypeVar
from weakref import WeakKeyDictionary


try:
    from typing import dataclass_transform  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    from typing_extensions import dataclass_transform


if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    _Ta = TypeVar("_Ta")
    _Tb = TypeVar("_Tb")

    _TFormatters: TypeAlias = dict[type[_Tb], Callable[[_Tb], str]]


_DEFAULT_FORMATTERS: _TFormatters = {
    float: lambda n: f"{n:.3f}",
    datetime: lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    timedelta: str,
}
_FORMATTER_REFS: WeakKeyDictionary[FormattedDataclass, tuple[_TFormatters, list[str]] | None] = WeakKeyDictionary()


@dataclass_transform()
class FormattedDataclass(type):
    def __new__(
        cls,
        name,
        bases,
        namespace,
        formatters: _TFormatters | None = None,
        extra: list[str] | None = None,
        **kwargs,
    ) -> FormattedDataclass:
        obj = super().__new__(cls, name, bases, namespace, **kwargs)

        formatters = formatters or {}
        extra = extra or []

        frmttrs: _TFormatters = _DEFAULT_FORMATTERS.copy()
        for base in bases:
            if base_data := _FORMATTER_REFS.get(base):  # pragma: no branch
                frmttrs.update(base_data[0])
                extra = [*base_data[1], *extra]
        frmttrs.update(formatters)

        _FORMATTER_REFS[obj] = frmttrs, extra

        def serialize(self: DataclassInstance) -> str:
            items: list[str] = []

            def add_item(key: str) -> None:
                value = getattr(self, key, None)
                if formatter := frmttrs.get(type(value)):
                    value = formatter(value)
                else:
                    value = repr(value)
                items.append(f"{key}={value}")

            # noinspection PyDataclass
            for fld in dataclasses.fields(self):
                if fld.repr:
                    add_item(fld.name)
            for ex in extra:
                add_item(ex)

            return f"{self.__class__.__name__}({', '.join(items)})"

        obj.__str__ = obj.__repr__ = serialize  # type: ignore[assignment]

        return obj
