import os
import signal

import pytest

# import streamlink_cli as early as possible to execute its default signal overrides
# noinspection PyUnresolvedReferences
import streamlink_cli  # noqa: F401


# immediately restore default signal handlers for the test runner
signal.signal(signal.SIGINT, signal.default_int_handler)
signal.signal(signal.SIGTERM, signal.default_int_handler)


# make pytest rewrite assertions in dynamically parametrized plugin tests
# https://docs.pytest.org/en/stable/how-to/writing_plugins.html#assertion-rewriting
pytest.register_assert_rewrite("tests.plugins")


windows_only = pytest.mark.skipif(os.name != "nt", reason="test only applicable on Windows")
posix_only = pytest.mark.skipif(os.name != "posix", reason="test only applicable on a POSIX OS")


__all__ = ["windows_only", "posix_only"]
