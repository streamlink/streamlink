from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from time import time
from typing import Any

from streamlink.compat import is_win32


if is_win32:
    xdg_cache = os.environ.get("APPDATA", os.path.expanduser("~"))
else:
    xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))

# TODO: fix macOS path and deprecate old one (with fallback logic)
CACHE_DIR = Path(xdg_cache) / "streamlink"


# TODO: rewrite data structure
#  - replace prefix logic with namespaces
#  - change timestamps from (timezoned) epoch values to ISO8601 strings (UTC)
#  - add JSON schema information
#  - add translation logic, to keep backwards compatibility
class Cache:
    def __init__(
        self,
        filename: str | Path,
        key_prefix: str = "",
    ):
        """
        Caches Python values as JSON and prunes expired entries.

        :param filename: A file name or :class:`Path` object, relative to the cache directory
        :param key_prefix: Optional prefix for each key to be retrieved from or stored in the cache
        """

        self.key_prefix = key_prefix
        self.filename = CACHE_DIR / Path(filename)

        self._cache: dict[str, dict[str, Any]] = {}

    def _load(self):
        self._cache = {}
        if self.filename.exists():
            with suppress(Exception):
                with self.filename.open("r") as fd:
                    data = json.load(fd)
                    self._cache.update(**data)

    def _prune(self):
        now = time()
        pruned = []

        for key, value in self._cache.items():
            expires = value.get("expires", now)
            if expires <= now:
                pruned.append(key)

        for key in pruned:
            self._cache.pop(key, None)

        return len(pruned) > 0

    def _save(self):
        fd, tempname = tempfile.mkstemp()
        fd = os.fdopen(fd, "w")
        try:
            json.dump(self._cache, fd, indent=2, separators=(",", ": "))
        except Exception:
            raise
        finally:
            fd.close()

        # Silently ignore errors
        try:
            self.filename.parent.mkdir(exist_ok=True, parents=True)
            shutil.move(tempname, str(self.filename))
        except OSError:
            with suppress(Exception):
                os.remove(tempname)

    def set(
        self,
        key: str,
        value: Any,
        expires: float = 60 * 60 * 24 * 7,
        expires_at: datetime | None = None,
    ) -> None:
        """
        Store the given value using the key name and expiration time.

        Prunes the cache of all expired key-value pairs before setting the new key-value pair.

        :param key: A specific key name
        :param value: Any kind of value that can be JSON-serialized
        :param expires: Expiration time in seconds, with the default being one week
        :param expires_at: Optional expiration date, which overrides the expiration time
        """

        self._load()
        self._prune()

        if self.key_prefix:
            key = f"{self.key_prefix}:{key}"

        if expires_at is None:
            expires += time()
        else:
            try:
                expires = expires_at.timestamp()
            except OverflowError:
                expires = 0

        self._cache[key] = dict(value=value, expires=expires)
        self._save()

    def get(
        self,
        key: str,
        default: Any | None = None,
    ) -> Any:
        """
        Attempt to retrieve the given key from the cache.

        Prunes the cache of all expired key-value pairs before retrieving the key's value.

        :param key: A specific key name
        :param default: An optional default value if no key was stored, or if it has expired
        :return: The retrieved value or optional default value
        """

        self._load()

        if self._prune():
            self._save()

        if self.key_prefix:
            key = f"{self.key_prefix}:{key}"

        if key in self._cache and "value" in self._cache[key]:
            return self._cache[key]["value"]
        else:
            return default

    def get_all(self) -> dict[str, Any]:
        """
        Retrieve all cached key-value pairs.

        Prunes the cache of all expired key-value pairs first.

        :return: A dictionary of all cached key-value pairs.
        """

        ret = {}
        self._load()

        if self._prune():
            self._save()

        for key, value in self._cache.items():
            if self.key_prefix:
                prefix = f"{self.key_prefix}:"
            else:
                prefix = ""
            if key.startswith(prefix):
                okey = key[len(prefix) :]
                ret[okey] = value["value"]

        return ret


__all__ = ["Cache"]
