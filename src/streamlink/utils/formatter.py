import re

from streamlink_cli.compat import is_win32
from streamlink_cli.constants import DEFAULT_STREAM_METADATA, FS_SAFE_REPLACEMENT_CHAR, INVALID_FILENAME_CHARS


class Formatter(dict):
    def __init__(self, plugin, args):
        self.plugin = plugin
        self.args = args
        self.cache = self.Cache(self.plugin)

    def __missing__(self, k):
        if k in ("title", "author", "category", "game", "url"):
            self[k] = self._make_fs_safe(self.cache[k])
        else:
            return f"{{{k}}}"

        return self[k]

    def _make_fs_safe(self, unsafe_str):
        if self.args.fs_safe_rules in INVALID_FILENAME_CHARS:
            rules = self.args.fs_safe_rules
        else:
            if is_win32:
                rules = "Windows"
            else:
                rules = "POSIX"

        sub_re = re.compile(
            "[{:s}]".format(re.escape(INVALID_FILENAME_CHARS[rules])), re.UNICODE
        )

        return sub_re.sub(FS_SAFE_REPLACEMENT_CHAR, unsafe_str)

    def get_formatted_filename(self, unformatted_filename):
        return unformatted_filename.format_map(self)

    def get_formatted_title(self, unformatted_title):
        if self.args.title:
            return unformatted_title.format_map(self.cache)
        else:
            return self.args.url

    class Cache(dict):
        def __init__(self, plugin):
            self.plugin = plugin

        def __missing__(self, k):
            if k == "title":
                v = self.plugin.get_title() or DEFAULT_STREAM_METADATA["title"]
            elif k == "author":
                v = self.plugin.get_author() or DEFAULT_STREAM_METADATA["author"]
            elif k == "category":
                v = self.plugin.get_category() or DEFAULT_STREAM_METADATA["category"]
            elif k == "game":
                v = self.plugin.get_category() or DEFAULT_STREAM_METADATA["game"]
            elif k == "url":
                v = self.plugin.url
            else:
                return f"{{{k}}}"

            self[k] = v
            return v
