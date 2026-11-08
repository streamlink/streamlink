from __future__ import annotations

import sys
from contextlib import suppress
from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING

from streamlink.logger import getLogger
from streamlink_cli.exceptions import StreamlinkCLIError


if TYPE_CHECKING:
    from streamlink_cli.argparser import ArgumentParser


log = getLogger("streamlink.cli")


def setup_args_from_stdin(
    parser: ArgumentParser,
    args_from_stdin: bool = False,
    timeout: float = 4.0,
    max_line_length: int = 65536,
    max_queue_size: int = 32,
) -> list[str]:
    if not args_from_stdin or not sys.stdin or sys.stdin.closed:
        return []

    if sys.stdin.isatty():
        log.warning("Can't process arguments from a TTY stdin stream")
        return []

    res = []
    queue: Queue[str | Exception | None] = Queue(maxsize=max_queue_size)

    def worker():
        try:  # ruff: ignore[too-many-statements-in-try-clause]
            while sys.stdin is not None and not sys.stdin.closed:
                line = sys.stdin.readline(max_line_length)
                if not line or line == "\n":
                    queue.put(None, block=True)
                elif line.endswith("\n"):
                    queue.put(line, block=True)
                else:
                    raise RuntimeError("Missing argument line terminator in stdin input")
        except Exception as err:
            queue.put(err)

    thread = Thread(target=worker, daemon=True, name="stdin-args-reader")
    thread.start()

    try:
        while True:
            try:
                item = queue.get(block=True, timeout=timeout)
            except Empty:
                raise StreamlinkCLIError("Timeout while reading arguments from stdin") from None
            if item is None:
                break
            elif isinstance(item, Exception):
                raise StreamlinkCLIError from item
            else:
                res.extend(parser.convert_arg_line_to_args(item))
    finally:
        with suppress(OSError):
            sys.stdin.close()
        # prevent the worker thread from blocking infinitely
        with queue.mutex:
            if queue._qsize():
                queue._get()
            queue.not_full.notify_all()
        thread.join(1)

    return res
