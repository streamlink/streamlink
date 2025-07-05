from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from atexit import register as _atexit_register
from contextlib import suppress
from copy import deepcopy
from datetime import datetime
from functools import wraps
from pathlib import Path
from threading import RLock, Timer
from time import time
from typing import Any

from streamlink.compat import is_win32


if is_win32:
    xdg_cache = os.environ.get("APPDATA", os.path.expanduser("~"))
else:
    xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))

# TODO: fix macOS path and deprecate old one (with fallback logic)
CACHE_DIR = Path(xdg_cache) / "streamlink"

WRITE_DEBOUNCE_TIME = 3.0


log = logging.getLogger(__name__)


def _atomic(fn):
    @wraps(fn)
    def inner(self, *args, **kwargs):
        with self._lock:
            return fn(self, *args, **kwargs)

    return inner


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
        disabled: bool = False,
    ):
        """
        Caches Python values as JSON and prunes expired entries.

        :param filename: A file name or :class:`Path` object, relative to the cache directory
        :param key_prefix: Optional prefix for each key to be retrieved from or stored in the cache
        """

        self.key_prefix = key_prefix
        self.filename = CACHE_DIR / Path(filename)

        self._cache_orig: dict[str, dict[str, Any]] = {}
        self._cache: dict[str, dict[str, Any]] = {}

        self._loaded = self._disabled = bool(disabled)
        self._lock = RLock()
        self._timer: Timer | None = None

        _atexit_register(self._save)

    @property
    def _dirty(self):
        return self._cache != self._cache_orig

    def _load(self):
        if self._loaded:
            return

        self._loaded = True
        self._cache_orig.clear()
        self._cache.clear()

        # noinspection PyUnresolvedReferences
        log.trace(f"Loading cache file: {self.filename}")

        try:
            with self.filename.open("r", encoding="utf-8") as fd:
                data = json.load(fd)
                self._cache_orig.update(**data)
                self._cache.update(**data)
        except FileNotFoundError:
            pass
        except Exception as err:
            log.warning(f"Failed loading cache file, continuing without cache: {err}")

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

    def _schedule_save(self):
        if self._timer:
            self._timer.cancel()
        if self._disabled or not self._dirty:
            return

        # noinspection PyUnresolvedReferences
        log.trace(f"Scheduling write to cache file: {WRITE_DEBOUNCE_TIME:.1f}s")
        self._timer = Timer(WRITE_DEBOUNCE_TIME, self._save)
        self._timer.daemon = True
        self._timer.name = "CacheSaveThread"
        self._timer.start()

    @_atomic
    def _save(self):
        if self._timer:
            self._timer.cancel()
        if self._disabled or not self._dirty:
            return

        # noinspection PyUnresolvedReferences
        log.trace(f"Writing to cache file: {self.filename}")

        fd = None
        try:
            self.filename.parent.mkdir(exist_ok=True, parents=True)
            # TODO: py311 support end: set delete_on_close=False and move file in the context manager
            with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", delete=False) as fd:
                json.dump(self._cache, fd, indent=2, separators=(",", ": "))
                fd.flush()
            shutil.move(fd.name, self.filename)
        except Exception as err:
            if fd:
                with suppress(OSError):
                    os.unlink(fd.name)
            log.error(f"Error while writing to cache file: {err}")
        else:
            self._cache_orig.clear()
            self._cache_orig.update(**deepcopy(self._cache))

    @_atomic
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
        self._schedule_save()

    @_atomic
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
        self._prune()
        self._schedule_save()

        if self.key_prefix:
            key = f"{self.key_prefix}:{key}"

        if key in self._cache and "value" in self._cache[key]:
            return self._cache[key]["value"]
        else:
            return default

    @_atomic
    def get_all(self) -> dict[str, Any]:
        """
        Retrieve all cached key-value pairs.

        Prunes the cache of all expired key-value pairs first.

        :return: A dictionary of all cached key-value pairs.
        """

        ret = {}

        self._load()
        self._prune()
        self._schedule_save()

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
