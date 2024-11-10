from __future__ import annotations

import re
from textwrap import dedent, indent

from streamlink.plugin import HIGH_PRIORITY, LOW_PRIORITY, NO_PRIORITY, NORMAL_PRIORITY, Plugin
from streamlink.session import Streamlink
from streamlink_cli.console import ConsoleOutput
from streamlink_cli.exceptions import StreamlinkCLIError


PRIORITY_NAMES = {
    NO_PRIORITY: "NONE",
    LOW_PRIORITY: "LOW",
    HIGH_PRIORITY: "HIGH",
}

# noinspection PyTypeChecker
PATTERN_FLAG_NAMES: dict[int, str] = {
    flag.value: flag.name
    for flag in (re.IGNORECASE, re.VERBOSE)
    if flag.name
}  # fmt: skip


def show_matchers(session: Streamlink, console: ConsoleOutput, pluginname: str):
    if pluginname not in session.plugins:
        raise StreamlinkCLIError("Plugin not found", code=1)

    plugin = session.plugins[pluginname]

    if console.json:
        console.msg_json(show_matchers_json(plugin))
    else:
        console.msg(show_matchers_text(plugin))


def show_matchers_text(plugin: type[Plugin]) -> str:
    output = []
    indentation = "  "
    for matcher in plugin.matchers or []:
        data = []
        flags = [name for val, name in PATTERN_FLAG_NAMES.items() if matcher.pattern.flags & val]
        if matcher.name:
            data.append(f"name: {matcher.name}")
        if matcher.priority != NORMAL_PRIORITY:
            data.append(f"priority: {PRIORITY_NAMES.get(matcher.priority, matcher.priority)}")
        if flags:
            data.append(f"flags: {' & '.join(flags)}")
        if matcher.pattern.flags & re.VERBOSE:
            data.append(f"pattern:\n{indent(dedent(matcher.pattern.pattern).strip(), indentation)}")
        else:
            data.append(f"pattern: {matcher.pattern.pattern}")
        item = indent("\n".join(data), indentation)
        output.append(f"- {item[2:]}")

    return "\n".join(output)


def show_matchers_json(plugin: type[Plugin]) -> list[dict]:
    return [
        {
            "name": matcher.name,
            "priority": matcher.priority,
            "flags": matcher.pattern.flags & ~re.UNICODE,
            "pattern": (
                dedent(matcher.pattern.pattern).strip()
                if matcher.pattern.flags & re.VERBOSE
                else matcher.pattern.pattern
            ),
        }
        for matcher in plugin.matchers or []
    ]  # fmt: skip
