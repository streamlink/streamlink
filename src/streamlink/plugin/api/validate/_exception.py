from typing import Optional, Sequence, Union

from streamlink.compat import indent


class ValidationError(ValueError):
    MAX_LENGTH = 60

    def __init__(self, *error, **kwargs):
        # type: (Union[str, Exception, Sequence[Union[str, Exception]]])
        self.schema = kwargs.pop("schema", None)
        # type: Optional[Union[str, object]]
        self.context = kwargs.pop("context", None)
        # type: Optional[Union[Exception]]
        if len(error) == 1 and type(error[0]) is str:
            self.errors = (self._truncate(error[0], **kwargs), )
        else:
            self.errors = error

    def _ellipsis(self, string):
        # type: (str)
        return string if len(string) <= self.MAX_LENGTH else "<{}...>".format(string[:self.MAX_LENGTH - 5])

    def _truncate(self, template, **kwargs):
        # type: (str)
        return str(template).format(
            **{k: self._ellipsis(str(v)) for k, v in kwargs.items()}
        )

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
