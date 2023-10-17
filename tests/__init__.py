import signal

import freezegun.config
import pytest

# import streamlink_cli as early as possible to execute its default signal overrides
# noinspection PyUnresolvedReferences
import streamlink_cli


# immediately restore default signal handlers for the test runner
signal.signal(signal.SIGINT, signal.default_int_handler)
signal.signal(signal.SIGTERM, signal.default_int_handler)


# make freezegun ignore the following pytest modules, so it doesn't mess with pytest's --duration=N report
# when freezing time in fixtures, even though ["_pytest.runner.", "_pytest.terminal."] is already included
# in freezegun's default module ignore list (notice the trailing dots).
freezegun.config.configure(extend_ignore_list=["_pytest.runner", "_pytest.terminal"])


# make pytest rewrite assertions in dynamically parametrized plugin tests
# https://docs.pytest.org/en/stable/how-to/writing_plugins.html#assertion-rewriting
pytest.register_assert_rewrite("tests.plugins")
