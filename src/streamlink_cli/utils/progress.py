import sys
from collections import deque
from shutil import get_terminal_size
from time import time

from streamlink_cli.compat import is_win32

PROGRESS_FORMATS = (
    "[download][{prefix}] Written {written} ({elapsed} @ {speed}/s)",
    "[download] Written {written} ({elapsed} @ {speed}/s)",
    "[download] {written} ({elapsed} @ {speed}/s)",
    "[download] {written} ({elapsed})",
    "[download] {written}"
)

# widths generated from
# http://www.unicode.org/Public/4.0-Update/EastAsianWidth-4.0.0.txt
widths = [
    (13, 1),    (15, 0),    (126, 1),   (159, 0),   (687, 1),   (710, 0),    # noqa: E241
    (711, 1),   (727, 0),   (733, 1),   (879, 0),   (1154, 1),  (1161, 0),   # noqa: E241
    (4347, 1),  (4447, 2),  (7467, 1),  (7521, 0),  (8369, 1),  (8426, 0),   # noqa: E241
    (9000, 1),  (9002, 2),  (11021, 1), (12350, 2), (12351, 1), (12438, 2),  # noqa: E241
    (12442, 0), (19893, 2), (19967, 1), (55203, 2), (63743, 1), (64106, 2),  # noqa: E241
    (65039, 1), (65059, 0), (65131, 2), (65279, 1), (65376, 2), (65500, 1),  # noqa: E241
    (65510, 2), (120831, 1), (262141, 2), (1114109, 1)                       # noqa: E241
]


def get_width(o):
    """Returns the screen column width for unicode ordinal."""
    for num, wid in widths:
        if o <= num:
            return wid
    return 1


def terminal_width(value):
    """Returns the width of the string it would be when displayed."""
    if isinstance(value, bytes):
        value = value.decode("utf8", "ignore")
    return sum(map(get_width, map(ord, value)))


def get_cut_prefix(value, max_len):
    """Drops Characters by unicode not by bytes."""
    should_convert = isinstance(value, bytes)
    if should_convert:
        value = value.decode("utf8", "ignore")
    for i in range(len(value)):
        if terminal_width(value[i:]) <= max_len:
            break
    return value[i:].encode("utf8", "ignore") if should_convert else value[i:]


def print_inplace(msg):
    """Clears out the previous line and prints a new one."""
    term_width = get_terminal_size().columns
    spacing = term_width - terminal_width(msg)

    # On windows we need one less space or we overflow the line for some reason.
    if is_win32:
        spacing -= 1

    sys.stderr.write("\r{0}".format(msg))
    sys.stderr.write(" " * max(0, spacing))
    sys.stderr.flush()


def format_filesize(size):
    """Formats the file size into a human readable format."""
    for suffix in ("bytes", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            if suffix in ("GB", "TB"):
                return "{0:3.2f} {1}".format(size, suffix)
            else:
                return "{0:3.1f} {1}".format(size, suffix)

        size /= 1024.0


def format_time(elapsed):
    """Formats elapsed seconds into a human readable format."""
    hours = int(elapsed / (60 * 60))
    minutes = int((elapsed % (60 * 60)) / 60)
    seconds = int(elapsed % 60)

    rval = ""
    if hours:
        rval += "{0}h".format(hours)

    if elapsed > 60:
        rval += "{0}m".format(minutes)

    rval += "{0}s".format(seconds)
    return rval


def create_status_line(**params):
    """Creates a status line with appropriate size."""
    max_size = get_terminal_size().columns - 1

    for fmt in PROGRESS_FORMATS:
        status = fmt.format(**params)

        if len(status) <= max_size:
            break

    return status


def progress(iterator, prefix):
    """Progress an iterator and updates a pretty status line to the terminal.

    The status line contains:
     - Amount of data read from the iterator
     - Time elapsed
     - Average speed, based on the last few seconds.
    """
    if terminal_width(prefix) > 25:
        prefix = (".." + get_cut_prefix(prefix, 23))
    speed_updated = start = time()
    speed_written = written = 0
    speed_history = deque(maxlen=5)

    for data in iterator:
        yield data

        now = time()
        elapsed = now - start
        written += len(data)

        speed_elapsed = now - speed_updated
        if speed_elapsed >= 0.5:
            speed_history.appendleft((
                written - speed_written,
                speed_updated,
            ))
            speed_updated = now
            speed_written = written

            speed_history_written = sum(h[0] for h in speed_history)
            speed_history_elapsed = now - speed_history[-1][1]
            speed = speed_history_written / speed_history_elapsed

            status = create_status_line(
                prefix=prefix,
                written=format_filesize(written),
                elapsed=format_time(elapsed),
                speed=format_filesize(speed)
            )
            print_inplace(status)
    sys.stderr.write("\n")
    sys.stderr.flush()
