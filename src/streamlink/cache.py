import json
import os
import shutil
import tempfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from time import time
from typing import Any, Dict, Optional, Union

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
    """Caches Python values as JSON and prunes expired entries."""

    def __init__(self, filename: Union[str, Path], key_prefix: str = ""):
        self.key_prefix = key_prefix
        self.filename = CACHE_DIR / Path(filename)

        self._cache: Dict[str, Dict[str, Any]] = {}

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

    def set(self, key: str, value: Any, expires: float = 60 * 60 * 24 * 7, expires_at: Optional[datetime] = None):
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

    def get(self, key: str, default: Optional[Any] = None):
        self._load()

        if self._prune():
            self._save()

        if self.key_prefix:
            key = f"{self.key_prefix}:{key}"

        if key in self._cache and "value" in self._cache[key]:
            return self._cache[key]["value"]
        else:
            return default

    def get_all(self):
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
                okey = key[len(prefix):]
                ret[okey] = value["value"]

        return ret


__all__ = ["Cache"]
