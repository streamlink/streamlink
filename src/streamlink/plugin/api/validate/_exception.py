from textwrap import indent


class ValidationError(ValueError):
    def __init__(self, *errors, schema=None, context: "ValidationError" = None):
        self.schema = schema
        self.errors = errors
        self.context = context

    def _get_schema_name(self) -> str:
        if not self.schema:
            return ""
        if type(self.schema) is str:
            return f"({self.schema})"
        return f"({self.schema.__name__})"

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

            context = error.context
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
