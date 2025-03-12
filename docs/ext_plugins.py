from __future__ import annotations

import abc
import ast
import pkgutil
import re
import tokenize
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import ViewList
from sphinx.errors import ExtensionError
from sphinx.util.nodes import nested_parse_with_titles

from streamlink import plugins as streamlink_plugins


class IDatalistItem(abc.ABC):
    @abc.abstractmethod
    def generate(self) -> Iterator[str]:
        raise NotImplementedError


class IMetadataItem(IDatalistItem):
    @abc.abstractmethod
    def set(self, value: Any) -> None:
        raise NotImplementedError


class MetadataItem(IMetadataItem):
    def __init__(self, title: str):
        self.title = title
        self.value: str | None = None

    def set(self, value: str) -> None:
        self.value = value

    def generate(self) -> Iterator[str]:
        if self.value is None:
            return
        yield f":{self.title}: {self.value}"


class MetadataList(IMetadataItem):
    def __init__(self, title: str):
        self.title = title
        self.value: list[str] = []

    def set(self, value: str) -> None:
        self.value.append(value)

    def generate(self) -> Iterator[str]:
        if not self.value:
            return
        yield f":{self.title}: - {' '.join(self.get_item(0))}"
        indent = " " * len(f":{self.title}:")
        for idx in range(1, len(self.value)):
            yield f"{indent} - {' '.join(self.get_item(idx))}"

    def get_item(self, idx: int) -> Iterator[str]:
        yield self.value[idx]


class MetadataWebbrowserItem(MetadataItem):
    def __init__(self):
        super().__init__("Web browser")

    def generate(self) -> Iterator[str]:
        if self.value is None:
            return
        yield from super().generate()
        yield " [:ref:`? <cli:Web browser options>`]"


class MetadataMetadataList(MetadataList):
    def __init__(self):
        super().__init__("Metadata")

    def get_item(self, idx: int) -> Iterator[str]:
        variable, *data = str(self.value[idx]).split(" ")
        yield f":ref:`{variable} <cli/metadata:Variables>`"
        if data:
            yield " ".join(["-", *data])


class PluginOnGithub(IDatalistItem):
    url_source = "https://github.com/streamlink/streamlink/blob/master/src/streamlink/plugins/{name}.py"
    url_issues = "https://github.com/streamlink/streamlink/issues?q=is%3Aissue+sort%3Aupdated-desc+plugins.{name}"

    def __init__(self, pluginname: str):
        self.pluginname = pluginname

    def generate(self) -> Iterator[str]:
        source = f"`Source <{self.url_source.format(name=self.pluginname)}>`__"
        issues = f"`Issues <{self.url_issues.format(name=self.pluginname)}>`__"
        yield f":GitHub: {source}, {issues}"


class PluginArguments(ast.NodeVisitor, IDatalistItem):
    def __init__(self, pluginname, pluginast):
        super().__init__()
        self.pluginname = pluginname
        self.arguments = []
        self.visit(pluginast)

    def generate(self) -> Iterator[str]:
        if not self.arguments:
            return
        indent = " " * len(":Arguments: ")
        yield f":Arguments: - :option:`--{self.arguments[0]}`"
        for arg in self.arguments[1:]:
            yield f"{indent} - :option:`--{arg}`"

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for base in node.bases:
            if not isinstance(base, ast.Name):
                continue
            if base.id == "Plugin":
                break
        else:
            return

        for decorator in node.decorator_list:
            if (
                not isinstance(decorator, ast.Call)
                or not isinstance(decorator.func, ast.Name)
                or decorator.func.id != "pluginargument"
                or (len(decorator.args) == 0 and len(decorator.keywords) == 0)
            ):
                continue

            if any(
                True
                for kw in decorator.keywords
                if (
                    kw.arg == "help"
                    and type(kw.value) is ast.Attribute
                    and kw.value.attr == "SUPPRESS"
                    and type(kw.value.value) is ast.Name
                    and kw.value.value.id == "argparse"
                )
            ):
                continue

            custom_name = next(
                (kw.value.value for kw in decorator.keywords if kw.arg == "argument_name" and type(kw.value) is ast.Constant),
                None,
            )
            if custom_name:
                self.arguments.append(custom_name)
                continue

            name = next(
                (kw.value.value for kw in decorator.keywords if kw.arg == "name" and type(kw.value) is ast.Constant),
                None,
            ) or (
                decorator.args
                and type(decorator.args[0]) is ast.Constant
                and decorator.args[0].value
            )  # fmt: skip
            if name:
                self.arguments.append(f"{self.pluginname}-{name}")


class PluginMetadata:
    def __init__(self, name: str, pluginast):
        self.name: str = name
        self.items: dict[str, IMetadataItem] = dict(
            description=MetadataItem("Description"),
            url=MetadataList("URL(s)"),
            type=MetadataItem("Type"),
            webbrowser=MetadataWebbrowserItem(),
            metadata=MetadataMetadataList(),
            region=MetadataItem("Region"),
            account=MetadataItem("Account"),
            notes=MetadataList("Notes"),
        )
        self.additional: list[IDatalistItem] = [
            PluginArguments(name, pluginast),
            PluginOnGithub(name),
        ]

    def set(self, key: str, value: str) -> None:
        if key not in self.items:
            raise KeyError(f"Invalid plugin metadata key '{key}' in plugin '{self.name}'")
        self.items[key].set(value)

    def generate(self) -> Iterator[str]:
        yield self.name
        yield "-" * len(self.name)
        yield ""
        for metadata in self.items.values():
            yield from metadata.generate()
        for item in self.additional:
            yield from item.generate()
        yield ""
        yield ""


class PluginFinder:
    _re_metadata_item = re.compile(r"\n\$(\w+) (.+)(?=\n\$|$)", re.MULTILINE)

    protocol_plugins = [
        "http",
        "hls",
        "dash",
    ]

    def __init__(self):
        plugins_path = Path(streamlink_plugins.__path__[0])
        self.plugins = [
            (pname, plugins_path / f"{pname}.py")
            for finder, pname, ispkg in pkgutil.iter_modules([str(plugins_path)])
            if not pname.startswith("common_") and pname not in self.protocol_plugins
        ]

    def get_plugins(self):
        for pluginname, pluginfile in self.plugins:
            pluginmetadata = self._parse_plugin(pluginname, pluginfile)
            if pluginmetadata:
                yield pluginmetadata

    def _parse_plugin(self, pluginname: str, pluginfile: Path) -> PluginMetadata | None:
        with pluginfile.open() as handle:
            # read until the first token has been parsed
            for tokeninfo in tokenize.generate_tokens(handle.readline):
                # the very first token needs to be a string / block comment with the metadata
                if tokeninfo.type != tokenize.STRING or not self._re_metadata_item.search(tokeninfo.string):
                    return None
                metadata = tokeninfo.string.strip()
                break

            try:
                # continue reading the plugin file with the same handle
                pluginsource = handle.read()
                # build AST from plugin source for finding the used plugin arguments
                pluginast = ast.parse(pluginsource, str(pluginfile))

                pluginmetadata = PluginMetadata(pluginname, pluginast)
                for item in self._re_metadata_item.finditer(metadata):
                    key, value = item.groups()
                    pluginmetadata.set(key, value)

                return pluginmetadata

            except Exception as err:
                raise ExtensionError(f"Error while parsing plugin file {pluginfile.name}", err) from err


class PluginsDirective(Directive):
    def run(self):
        pluginfinder = PluginFinder()

        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for pluginmetadata in pluginfinder.get_plugins():
            for line in pluginmetadata.generate():
                result.append(line, "plugins")

        nested_parse_with_titles(self.state, result, node)
        return node.children


def setup(app):
    app.add_directive("plugins", PluginsDirective)
