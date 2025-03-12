from __future__ import annotations

from pathlib import Path

from streamlink.utils.formatter import Formatter as _BaseFormatter
from streamlink_cli.utils.path import replace_chars, replace_path, truncate_path


class Formatter(_BaseFormatter):
    title = _BaseFormatter.format

    def path(self, pathlike: str, charmap: str | None = None, max_filename_length: int = 255) -> Path:
        def mapper(s):
            return replace_chars(s, charmap)

        def format_part(part: str, isfile: bool) -> str:
            formatted = self._format(part, mapper, {})
            return truncate_path(formatted, max_filename_length, keep_extension=isfile)

        return replace_path(pathlike, format_part)
