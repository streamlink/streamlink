from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from itertools import count
from threading import Event, RLock, Thread
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator
    from concurrent.futures import Future

    from typing_extensions import Unpack


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


def wait_for_all_events(*events: Unpack[tuple[Event]], timeout: int | None = None) -> bool:
    with ThreadPoolExecutor(max_workers=len(events)) as executor:
        futures: list[Future[bool]] = [executor.submit(event.wait, timeout) for event in events]
        # future result blocks until event is set or times out
        results = [future.result(timeout=None) for future in futures]

    return all(results)
