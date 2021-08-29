from typing import Callable, Dict, Optional, Type, Union

from streamlink_cli.utils.path import replace_chars


class _UNKNOWN:
    pass


class Formatter(dict):
    def __init__(self, mapping: Dict[str, Callable]):
        super().__init__()
        self.mapping = mapping
        self.cache = dict()

    def __missing__(self, key: str) -> Union[Type[_UNKNOWN], None, str]:
        if key not in self.mapping:
            return _UNKNOWN

        if key in self.cache:
            return self.cache[key]

        value = self.mapping[key]()
        self.cache[key] = value

        return value

    def _format(self, string: str, wrapper: Callable[[str], str], defaults: Optional[Dict] = None) -> str:
        return string.format_map(_Wrapper(self, wrapper, defaults))

    def filename(self, filename: str, charmap: Optional[str] = None) -> str:
        return self._format(filename, lambda s: replace_chars(s, charmap))

    def title(self, title: str, defaults: Optional[Dict] = None) -> str:
        return self._format(title, lambda s: s, defaults)


class _Wrapper(dict):
    def __init__(self, formatter: Formatter, wrapper: Callable[[str], str], defaults: Optional[Dict[str, str]] = None):
        super().__init__()
        self.formatter = formatter
        self.wrapper = wrapper
        self.defaults = defaults or {}

    def __missing__(self, key: str) -> str:
        value = self.formatter[key]
        if value is _UNKNOWN:
            value = str(self.defaults.get(key, f"{{{key}}}"))
        elif value is None:
            value = str(self.defaults.get(key, ""))

        return self.wrapper(value)
