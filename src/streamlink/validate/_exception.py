from __future__ import annotations

from collections.abc import Sequence
from textwrap import indent


class ValidationError(ValueError):
    """
    Currently not exposed in the public API.
    """

    MAX_LENGTH = 60

    errors: str | Exception | Sequence[str | Exception]

    def __init__(
        self,
        *errors,
        schema: str | object | None = None,
        **errkeywords,
    ):
        self.schema = schema
        if len(errors) == 1 and isinstance(errors[0], str):
            self.errors = (self._truncate(errors[0], **errkeywords),)
        else:
            self.errors = errors

    def _ellipsis(self, string: str):
        return string if len(string) <= self.MAX_LENGTH else f"<{string[: self.MAX_LENGTH - 5]}...>"

    def _truncate(self, template: str, **kwargs):
        return template.format(**{k: self._ellipsis(str(v)) for k, v in kwargs.items()})

    def _get_schema_name(self) -> str:
        if not self.schema:
            return ""
        if isinstance(self.schema, str):
            return f"({self.schema})"
        return f"({self.schema.__name__})"  # type: ignore[attr-defined]

    def __str__(self):
        cls = self.__class__
        ret = []
        seen = set()

        def append(indentation, error):
            if error:
                ret.append(indent(f"{error}", indentation))

        def add(level, error):
            indentation = "  " * level

            if error in seen:
                append(indentation, "...")
                return
            seen.add(error)

            for err in error.errors:
                if not isinstance(err, cls):
                    append(indentation, f"{err}")
                else:
                    append(indentation, f"{err.__class__.__name__}{err._get_schema_name()}:")
                    add(level + 1, err)

            context = error.__cause__
            if context:
                if not isinstance(context, cls):
                    append(indentation, "Context:")
                    append(f"{indentation}  ", context)
                else:
                    append(indentation, f"Context{context._get_schema_name()}:")
                    add(level + 1, context)

        append("", f"{cls.__name__}{self._get_schema_name()}:")
        add(1, self)

        return "\n".join(ret)
