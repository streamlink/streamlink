from string import Formatter as StringFormatter
from typing import Any, Callable, Dict, Optional

from streamlink_cli.utils.path import replace_chars


# we only need string.Formatter for calling its parse() method, which returns `_string.formatter_parser(string)`.
_stringformatter = StringFormatter()


def _identity(obj):
    return obj


class Formatter:
    def __init__(self, mapping: Dict[str, Callable], formatting: Optional[Dict[str, Callable]] = None):
        super().__init__()
        self.mapping = mapping
        self.formatting = formatting or {}
        self.cache = {}

    def _get_value(self, field_name: str, format_spec: str, defaults: Dict[str, str]) -> Any:
        if field_name not in self.mapping:
            return defaults.get(field_name, f"{{{field_name}}}" if not format_spec else f"{{{field_name}:{format_spec}}}")

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
                return f"{{{field_name}:{format_spec}}}"

        return value

    def _format(self, string: str, mapper: Callable[[str], str], defaults: Dict[str, str]) -> str:
        result = []

        for literal_text, field_name, format_spec, conversion in _stringformatter.parse(string):
            if literal_text:
                result.append(literal_text)

            if field_name is None:
                continue

            value = self._get_value(field_name, format_spec, defaults)
            result.append(mapper(str(value)))

        return "".join(result)

    def filename(self, filename: str, charmap: Optional[str] = None) -> str:
        return self._format(filename, lambda s: replace_chars(s, charmap), {})

    def title(self, title: str, defaults: Optional[Dict[str, str]] = None) -> str:
        return self._format(title, _identity, defaults or {})
