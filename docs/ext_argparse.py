"""Convert a argparse parser to option directives.

Inspired by sphinxcontrib.autoprogram but with a few differences:

- Contains some simple pre-processing on the help messages to make
  the Sphinx version a bit prettier.

"""

import argparse
import re

from textwrap import dedent

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import unchanged
from docutils.statemachine import ViewList
from sphinx.util.nodes import nested_parse_with_titles


_block_re = re.compile(r":\n{2}\s{2}")
_default_re = re.compile(r"Default is (.+)\.\n")
_note_re = re.compile(r"Note: (.*)(?:\n\n|\n*$)", re.DOTALL)
_option_line_re = re.compile(r"^(?!\s{2}|Example: )(.+)$", re.MULTILINE)
_option_re = re.compile(r"(?:^|(?<=\s))(--\w[\w-]*\w)\b")
_prog_re = re.compile(r"%\(prog\)s")
_percent_re = re.compile(r"%%")


def get_parser(module_name, attr):
    module = __import__(module_name, globals(), locals(), [attr])
    parser = getattr(module, attr)
    return parser if not(callable(parser)) else parser.__call__()


def indent(value, length=4):
    space = " " * length
    return "\n".join(space + line for line in value.splitlines())


class ArgparseDirective(Directive):
    has_content = True
    option_spec = {
        "module": unchanged,
        "attr": unchanged,
    }

    _headlines = ["^", "~"]

    def process_help(self, help):
        # Dedent the help to make sure we are always dealing with
        # non-indented text.
        help = dedent(help)

        # Replace option references with links.
        # Do this before indenting blocks and notes.
        help = _option_line_re.sub(
            lambda m: (
                _option_re.sub(
                    lambda m2: (
                        ":option:`{0}`".format(m2.group(1))
                        if m2.group(1) in self._available_options
                        else m2.group(0)
                    ),
                    m.group(1)
                )
            ),
            help
        )

        # Create simple blocks.
        help = _block_re.sub("::\n\n  ", help)

        # Boldify the default value.
        help = _default_re.sub(r"Default is: **\1**.\n", help)

        # Create note directives from "Note: " paragraphs.
        help = _note_re.sub(
            lambda m: ".. note::\n\n" + indent(m.group(1)) + "\n\n",
            help
        )

        # workaround to replace %(prog)s with streamlink
        help = _prog_re.sub("streamlink", help)

        # fix escaped chars for percent-formatted argparse help strings
        help = _percent_re.sub("%", help)

        return indent(help)

    def generate_group_rst(self, group):
        for action in group._group_actions:
            # don't document suppressed parameters
            if action.help == argparse.SUPPRESS:
                continue

            metavar = action.metavar
            if isinstance(metavar, tuple):
                metavar = " ".join(metavar)

            options = []
            # parameter(s) with metavar
            if action.option_strings and metavar:
                for arg in action.option_strings:
                    # optional parameter value
                    if action.nargs == "?":
                        metavar = f"[{metavar}]"
                    options.append(f"{arg} {metavar}")
            # positional parameter
            elif metavar:
                options.append(metavar)
            # parameter(s) without metavar
            else:
                options += action.option_strings

            directive = ".. option:: "
            options = f"\n{' ' * len(directive)}".join(options)
            yield f"{directive}{options}"
            yield ""
            for line in self.process_help(action.help).split("\n"):
                yield line
            yield ""
            if hasattr(action, "plugins") and len(action.plugins) > 0:
                yield f"    **Supported plugins:** {', '.join(action.plugins)}"
                yield ""

    def generate_parser_rst(self, parser, depth=0):
        if depth >= len(self._headlines):
            return
        for group in parser._action_groups:
            # Exclude empty groups
            if not group._group_actions and not group._action_groups:
                continue
            title = group.title
            yield ""
            yield title
            yield self._headlines[depth] * len(title)
            yield from self.generate_group_rst(group)
            if group._action_groups:
                yield ""
                yield from self.generate_parser_rst(group, depth + 1)

    def run(self):
        module = self.options.get("module")
        attr = self.options.get("attr")
        parser = get_parser(module, attr)

        self._available_options = []
        for action in parser._actions:
            # positional parameters have an empty option_strings list
            self._available_options += action.option_strings or [action.dest]

        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.generate_parser_rst(parser):
            result.append(line, "argparse")

        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    app.add_directive("argparse", ArgparseDirective)
