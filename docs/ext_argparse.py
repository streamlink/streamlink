"""
Convert an argparse parser to option directives.

Inspired by sphinxcontrib.autoprogram but with a few differences:

- Contains some simple pre-processing on the help messages to make
  the Sphinx version a bit prettier.
"""

import argparse
import re
from importlib import import_module
from textwrap import dedent

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import unchanged
from docutils.statemachine import ViewList
from sphinx.errors import ExtensionError
from sphinx.util.nodes import nested_parse_with_titles


_block_re = re.compile(r":\n{2}\s{2}")
_default_re = re.compile(r"Default is (.+)\.\n")
_note_re = re.compile(r"Note: (.*?)(?:\n\n|\n*$)", re.DOTALL)
_option_line_re = re.compile(r"^(?!\s{2,}%\(prog\)s|\s{2,}--\w[\w-]*\w\b|Example: )(.+)$", re.MULTILINE)
_option_re = re.compile(r"(?:^|(?<=\s))(?P<arg>--\w[\w-]*\w)(?P<val>=\w+)?\b")
_prog_re = re.compile(r"%\(prog\)s")
_percent_re = re.compile(r"%%")
_inline_code_block_re = re.compile(r"(?<!`)`([^`]+?)`")
_example_inline_code_block_re = re.compile(r"(?<=^Example: )(.+)$", re.MULTILINE)


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

    _DEFAULT_MODULE = "streamlink_cli._parser"
    _DEFAULT_ATTR = "get_parser"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._available_options = []

    @staticmethod
    def get_parser(module: str, attr: str) -> argparse.ArgumentParser:
        try:
            mod = import_module(module)
            obj = getattr(mod, attr)
        except Exception as err:
            raise ExtensionError("Invalid ext_argparse module or attr value") from err

        return obj() if callable(obj) else obj

    def process_help(self, helptext):
        # Dedent the help to make sure we are always dealing with
        # non-indented text.
        helptext = dedent(helptext)

        helptext = _inline_code_block_re.sub(
            lambda m: ":code:`{0}`".format(m.group(1).replace("\\", "\\\\")),
            helptext,
        )

        helptext = _example_inline_code_block_re.sub(r":code:`\1`", helptext)

        # Replace option references with links.
        # Do this before indenting blocks and notes.
        helptext = _option_line_re.sub(
            lambda m: _option_re.sub(
                lambda m2: f":option:`{m2['arg']}{m2['val'] or ''}`" if m2["arg"] in self._available_options else m2[0],
                m[1],
            ),
            helptext,
        )

        # Create simple blocks.
        helptext = _block_re.sub("::\n\n  ", helptext)

        # Boldify the default value.
        helptext = _default_re.sub(r"Default is: **\1**.\n", helptext)

        # Create note directives from "Note: " paragraphs.
        helptext = _note_re.sub(
            lambda m: ".. note::\n\n" + indent(m.group(1)) + "\n\n",
            helptext,
        )

        # workaround to replace %(prog)s with streamlink
        helptext = _prog_re.sub("streamlink", helptext)

        # fix escaped chars for percent-formatted argparse help strings
        helptext = _percent_re.sub("%", helptext)

        # create cross-links for the "Metadata variables" and "Plugins" sections
        helptext = re.sub(
            r"the \"Metadata variables\" section",
            'the ":ref:`Metadata variables <cli/metadata:Variables>`" section',
            helptext,
        )
        helptext = re.sub(
            r"the \"Plugins\" section",
            'the ":ref:`Plugins <plugins:Plugins>`" section',
            helptext,
        )

        return indent(helptext)

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

    def generate_parser_rst(self, parser, parent=None, depth=0):
        if depth >= len(self._headlines):
            return
        for group in parser.NESTED_ARGUMENT_GROUPS[parent]:
            is_parent = group in parser.NESTED_ARGUMENT_GROUPS
            # Exclude empty groups
            if not is_parent and not any(action.help != argparse.SUPPRESS for action in group._group_actions or []):
                continue
            title = group.title
            yield ""
            yield title
            yield self._headlines[depth] * len(title)
            yield from self.generate_group_rst(group)
            if is_parent:
                yield ""
                yield from self.generate_parser_rst(parser, group, depth + 1)

    def run(self):
        module = self.options.get("module", self._DEFAULT_MODULE)
        attr = self.options.get("attr", self._DEFAULT_ATTR)
        parser = self.get_parser(module, attr)

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
