from string import Formatter as StringFormatter

try:
    from typing import Any, Callable, Dict, Optional
except ImportError:
    pass

from streamlink.compat import str

# we only need string.Formatter for calling its parse() method, which returns `_string.formatter_parser(string)`.
_stringformatter = StringFormatter()


def _identity(obj):
    return obj


class Formatter(object):
    def __init__(self, mapping, formatting=None):
        # type: (Dict[str, Callable], Optional[Dict[str, Callable]])
        super(Formatter, self).__init__()
        self.mapping = mapping
        self.formatting = formatting or {}
        self.cache = {}

    def _get_value(self, field_name, format_spec, defaults):
        # type: (str, str, Dict[str, str]) -> Any
        if field_name not in self.mapping:
            return defaults.get(
                field_name, "{{{0}}}".format(field_name) if not format_spec else "{{{0}:{1}}}".format(field_name, format_spec)
            )

        if field_name in self.cache:
            value = self.cache[field_name]
        else:
            value = self.mapping[field_name]()
            self.cache[field_name] = value

        if value is None:
            value = defaults.get(field_name, "")

        if format_spec and field_name in self.formatting:
            # noinspection PyBroadException
            try:
                return self.formatting[field_name](value, format_spec)
            except Exception:
                return "{{{0}:{1}}}".format(field_name, format_spec)

        return value

    def _format(self, string, mapper, defaults):
        # type: (str, Callable[[str], str], Dict[str, str]) -> str
        result = []

        for literal_text, field_name, format_spec, conversion in _stringformatter.parse(string):
            if literal_text:
                result.append(literal_text)

            if field_name is None:
                continue

            value = self._get_value(field_name, format_spec, defaults)
            result.append(mapper(str(value)))

        return "".join(result)

    def format(self, title, defaults=None):
        # type: (str, Optional[Dict[str, str]]) -> str
        return self._format(title, _identity, defaults or {})
