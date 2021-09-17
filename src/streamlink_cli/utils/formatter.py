from typing import Dict, Optional

from streamlink.utils.formatter import Formatter as _BaseFormatter
from streamlink_cli.utils.path import replace_chars


class Formatter(_BaseFormatter):
    def filename(self, filename: str, charmap: Optional[str] = None) -> str:
        return self._format(filename, lambda s: replace_chars(s, charmap), {})

    def title(self, title: str, defaults: Optional[Dict[str, str]] = None) -> str:
        return self.format(title, defaults)
