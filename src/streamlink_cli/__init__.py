from signal import SIGINT, SIGTERM, signal
from sys import exit  # noqa: A004


def _exit(*_):
    # don't raise a KeyboardInterrupt until streamlink_cli has been fully initialized
    exit(128 | 2)


# override default SIGINT handler (and set SIGTERM handler) as early as possible
signal(SIGINT, _exit)
signal(SIGTERM, _exit)
