from pathlib import Path
from typing import Optional

from streamlink.utils.formatter import Formatter as _BaseFormatter
from streamlink_cli.utils.path import replace_chars, replace_path


class Formatter(_BaseFormatter):
    title = _BaseFormatter.format

    def path(self, pathlike: str, charmap: Optional[str] = None) -> Path:
        def mapper(s):
            return replace_chars(s, charmap)

        def format_part(part):
            return self._format(part, mapper, {})

        return replace_path(pathlike, format_part)
