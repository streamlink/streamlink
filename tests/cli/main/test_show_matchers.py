from __future__ import annotations

import re
from textwrap import dedent

import pytest

import streamlink_cli.main
from streamlink.plugin import HIGH_PRIORITY, NORMAL_PRIORITY, Plugin, pluginmatcher
from streamlink.session import Streamlink


@pytest.fixture(autouse=True)
def session(session: Streamlink):
    @pluginmatcher(re.compile(r"foo", re.IGNORECASE))
    @pluginmatcher(name="asdf", pattern=re.compile(r"bar"), priority=HIGH_PRIORITY)
    @pluginmatcher(re.compile(rf"baz{chr(0x0A)}qux", re.IGNORECASE | re.VERBOSE), priority=100)
    class MyPlugin(Plugin):
        def _get_streams(self):  # pragma: no cover
            pass

    session.plugins.update({"plugin": MyPlugin})

    return session


@pytest.mark.parametrize(
    ("argv", "output"),
    [
        pytest.param(
            ["--show-matchers", "doesnotexist"],
            "error: Plugin not found\n",
            id="no-json",
        ),
        pytest.param(
            ["--show-matchers", "doesnotexist", "--json"],
            """{\n  "error": "Plugin not found"\n}\n""",
            id="json",
        ),
    ],
    indirect=["argv"],
)
def test_plugin_not_found(capsys: pytest.CaptureFixture[str], argv: list[str], output: str):
    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 1
    stdout, stderr = capsys.readouterr()
    assert stdout == output
    assert stderr == ""


@pytest.mark.parametrize(
    ("argv", "output"),
    [
        pytest.param(
            ["--show-matchers", "plugin"],
            dedent("""
                - flags: IGNORECASE
                  pattern: foo
                - name: asdf
                  priority: HIGH
                  pattern: bar
                - priority: 100
                  flags: IGNORECASE & VERBOSE
                  pattern:
                    baz
                    qux
            """).lstrip(),
            id="no-json",
        ),
        pytest.param(
            ["--show-matchers", "plugin", "--json"],
            dedent(f"""
                [
                  {{
                    "name": null,
                    "priority": {NORMAL_PRIORITY},
                    "flags": {int(re.IGNORECASE)},
                    "pattern": "foo"
                  }},
                  {{
                    "name": "asdf",
                    "priority": {HIGH_PRIORITY},
                    "flags": 0,
                    "pattern": "bar"
                  }},
                  {{
                    "name": null,
                    "priority": 100,
                    "flags": {int(re.IGNORECASE + re.VERBOSE)},
                    "pattern": "baz\\nqux"
                  }}
                ]
            """).lstrip(),
            id="json",
        ),
    ],
    indirect=["argv"],
)
def test_show_matchers(capsys: pytest.CaptureFixture[str], argv: list[str], output: str):
    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == 0
    stdout, stderr = capsys.readouterr()
    assert stdout == output
    assert stderr == ""
