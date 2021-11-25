from typing import Dict, Optional

from streamlink.utils.formatter import Formatter as _BaseFormatter
from streamlink_cli.utils.path import replace_chars


class Formatter(_BaseFormatter):
    def path(self, filename, charmap=None):
        # type: (str, Optional[str]) -> str
        return self._format(filename, lambda s: replace_chars(s, charmap), {})

    def title(self, title, defaults=None):
        # type: (str, Optional[Dict[str, str]]) -> str
        return self.format(title, defaults)
