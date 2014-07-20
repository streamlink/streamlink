"""Convert a argparse parser to option directives.

Inspired by sphinxcontrib.autoprogram but with a few differences:

- Instead of relying on private argparse structures uses hooking
  to extract information from a argparse parser.

- Contains some simple pre-processing on the help messages to make
  the Sphinx version a bit prettier.

"""

import argparse
import re

from collections import namedtuple
from textwrap import dedent

from docutils import nodes
from docutils.parsers.rst.directives import unchanged
from docutils.statemachine import ViewList
from sphinx.util.nodes import nested_parse_with_titles
from sphinx.util.compat import Directive


_ArgumentParser = argparse.ArgumentParser
_Argument = namedtuple("Argument", ["args", "options"])

_block_re = re.compile(r":\n{2}\s{2}")
_default_re = re.compile(r"Default is (.+)\.\n")
_note_re = re.compile(r"Note: (.*)\n\n", re.DOTALL)
_option_re = re.compile(r"(--[\w-]+)")


class ArgumentParser(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.groups = []
        self.arguments = []

    def add_argument(self, *args, **options):
        if not options.get("help") == argparse.SUPPRESS:
            self.arguments.append(_Argument(args, options))

    def add_argument_group(self, *args, **options):
        group = ArgumentParser(*args, **options)
        self.groups.append(group)
        return group


def get_parser(module_name, attr):
    argparse.ArgumentParser = ArgumentParser
    module = __import__(module_name, globals(), locals(), [attr])
    argparse.ArgumentParser = _ArgumentParser
    return getattr(module, attr)


def indent(value, length=4):
    space = " " * length
    return "\n".join(space + line for line in value.splitlines())


class ArgparseDirective(Directive):
    has_content = True
    option_spec = {
        "module": unchanged,
        "attr": unchanged,
    }

    def process_help(self, help):
        # Dedent the help to make sure we are always dealing with
        # non-indented text.
        help = dedent(help)

        # Create simple blocks.
        help = _block_re.sub("::\n\n  ", help)

        # Boldify the default value.
        help = _default_re.sub(r"Default is: **\1**.\n", help)

        # Create note directives from "Note: " paragraphs.
        help = _note_re.sub(
            lambda m: ".. note::\n\n" + indent(m.group(1)) + "\n\n",
            help
        )

        # Replace option references with links.
        help = _option_re.sub(
            lambda m: (
                ":option:`{0}`".format(m.group(1))
                if m.group(1) in self._available_options
                else m.group(1)
            ),
            help
        )

        return indent(help)

    def generate_group_rst(self, group):
        for arg in group.arguments:
            help = arg.options.get("help")
            metavar = arg.options.get("metavar")

            if isinstance(metavar, tuple):
                metavar = " ".join(metavar)

            if metavar:
                optional = arg.options.get("nargs") == "?"
                if optional:
                    metavar = "[{0}]".format(metavar)

                options = []
                for a in arg.args:
                    if a.startswith("-"):
                        options.append("{0} {1}".format(a, metavar))
                    else:
                        options.append(metavar)
            else:
                options = arg.args

            yield ".. option:: {0}".format(", ".join(options))
            yield ""
            for line in self.process_help(help).split("\n"):
                yield line
            yield ""

    def generate_parser_rst(self, parser):
        for group in parser.groups:
            title = group.args[0]
            yield ""
            yield title
            yield "^" * len(title)
            for line in self.generate_group_rst(group):
                yield line

    def run(self):
        module = self.options.get("module")
        attr = self.options.get("attr")
        parser = get_parser(module, attr)

        self._available_options = []
        for group in parser.groups:
            for arg in group.arguments:
                self._available_options += arg.args

        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.generate_parser_rst(parser):
            result.append(line, "argparse")

        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    app.add_directive("argparse", ArgparseDirective)
