from streamlink.compat import indent


class ValidationError(ValueError):
    def __init__(self, *errors, **kwargs):
        # type: ("ValidationError")
        self.schema = kwargs.get("schema")
        self.errors = errors
        self.context = kwargs.get("context")

    def _get_schema_name(self):
        # type: () -> str
        if not self.schema:
            return ""
        if type(self.schema) is str:
            return "({0})".format(self.schema)
        return "({0})".format(self.schema.__name__)

    def __str__(self):
        cls = self.__class__
        ret = []
        seen = set()

        def append(indentation, error):
            if error:
                ret.append(indent("{0}".format(error), indentation))

        def add(level, error):
            indentation = "  " * level

            if error in seen:
                append(indentation, "...")
                return
            seen.add(error)

            for err in error.errors:
                if not isinstance(err, cls):
                    append(indentation, "{0}".format(err))
                else:
                    append(indentation, "{0}{1}:".format(err.__class__.__name__, err._get_schema_name()))
                    add(level + 1, err)

            context = error.context
            if context:
                if not isinstance(context, cls):
                    append(indentation, "Context:")
                    append("{0}  ".format(indentation), context)
                else:
                    append(indentation, "Context{0}:".format(context._get_schema_name()))
                    add(level + 1, context)

        append("", "{0}{1}:".format(cls.__name__, self._get_schema_name()))
        add(1, self)

        return "\n".join(ret)
