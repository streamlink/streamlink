from __future__ import annotations

from collections import defaultdict
from itertools import count
from threading import RLock, Thread
from typing import Iterator


_threadname_lock = RLock()
_threadname_counters: defaultdict[str, Iterator[int]] = defaultdict(count)


class NamedThread(Thread):
    def __init__(self, *args, name: str | None = None, **kwargs):
        with _threadname_lock:
            newname = self.__class__.__name__
            if name:
                newname += f"-{name}"

            # noinspection PyUnresolvedReferences
            kwargs["name"] = f"{newname}-{next(_threadname_counters[newname])}"

        super().__init__(*args, **kwargs)
