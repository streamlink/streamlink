import pytest

from streamlink_cli.compat import shlex_quote
import streamlink_cli.compat


@pytest.mark.parametrize("cmd,expected", [
    ("Test", "Test"),
    ('Test "Test"', '"Test \\"Test\\""'),
    ('Test \\""Test"', '"Test \\\\\\"\\"Test\\""')
])
def test_shlex_quote_win32(cmd, expected):
    streamlink_cli.compat.is_win32 = True
    assert shlex_quote(cmd) == expected
