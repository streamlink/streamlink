from pathlib import Path
from typing import Dict, Optional

from streamlink.utils.formatter import Formatter as _BaseFormatter
from streamlink_cli.utils.path import replace_chars, replace_path


class Formatter(_BaseFormatter):
    def path(self, pathlike: str, charmap: Optional[str] = None) -> Path:
        def mapper(s):
            return replace_chars(s, charmap)

        def format_part(part):
            return self._format(part, mapper, {})

        return replace_path(pathlike, format_part)

    def title(self, title: str, defaults: Optional[Dict[str, str]] = None) -> str:
        return self.format(title, defaults)
