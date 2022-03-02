import abc
import ast
import pkgutil
import re
import tokenize
from pathlib import Path
from sys import version_info
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional

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


class MetadataItem(IDatalistItem):
    def __init__(self, title: str):
        self.title = title
        self.value: Optional[str] = None

    def set(self, value: str) -> None:
        self.value = value

    def generate(self) -> Iterator[str]:
        if self.value is None:
            return
        yield f":{self.title}: {self.value}"


class MetadataList(MetadataItem):
    def __init__(self, title: str):
        super().__init__(title)
        self.value: List[str] = []

    def set(self, value: str) -> None:
        self.value.append(value)

    def generate(self) -> Iterator[str]:
        if not self.value:
            return
        indent = " " * len(f":{self.title}:")
        yield f":{self.title}: - {self.value[0]}"
        for val in self.value[1:]:
            yield f"{indent} - {val}"


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
        self.found = False
        self.visit(pluginast)

    def generate(self) -> Iterator[str]:
        if not self.arguments:
            return
        indent = " " * len(":Arguments: ")
        yield f":Arguments: - :option:`--{self.arguments[0]}`"
        for arg in self.arguments[1:]:
            yield f"{indent} - :option:`--{arg}`"

    @staticmethod
    def _get_constant(iterable, condition, getval, ast_type, ast_attr) -> Iterator[Optional[Any]]:
        for item in iterable:
            if condition(item) and type(getval(item)) is ast_type:
                yield getattr(getval(item), ast_attr)

    if version_info[:2] < (3, 8):
        def get_bool(self, iterable: Iterable, condition: Callable, getval: Callable):
            return self._get_constant(iterable, condition, getval, ast.NameConstant, "value")

        def get_string(self, iterable: Iterable, condition: Callable, getval: Callable):
            return self._get_constant(iterable, condition, getval, ast.Str, "s")

    else:
        def get_bool(self, iterable: Iterable, condition: Callable, getval: Callable):
            return self._get_constant(iterable, condition, getval, ast.Constant, "value")

        get_string = get_bool

    # loosely find all PluginArgument() calls inside the args list of the first PluginArguments() call
    # and assume that no plugin is defining arguments incorrectly
    def visit_Call(self, node: ast.Call) -> None:
        if getattr(node.func, "id", None) != "PluginArguments" or self.found:
            return
        self.found = True
        for arg in node.args:
            if type(arg) is not ast.Call or getattr(arg.func, "id", None) != "PluginArgument":
                continue

            if any(self.get_bool(arg.keywords, lambda kw: kw.arg == "is_global", lambda kw: kw.value)):
                continue

            custom_name: Optional[str] = next(
                self.get_string(arg.keywords, lambda kw: kw.arg == "argument_name", lambda kw: kw.value),
                None
            )
            if custom_name:
                self.arguments.append(custom_name)
                continue

            name: Optional[str] = next(
                self.get_string(arg.keywords, lambda kw: kw.arg == "name", lambda kw: kw.value),
                None
            ) or next(
                self.get_string(arg.args[:1], lambda a: True, lambda a: a),
                None
            )
            if name:
                self.arguments.append(f"{self.pluginname}-{name}")


class PluginMetadata:
    def __init__(self, name: str, pluginast):
        self.name: str = name
        self.items: Dict[str, MetadataItem] = dict(
            description=MetadataItem("Description"),
            url=MetadataList("URL(s)"),
            type=MetadataItem("Type"),
            region=MetadataItem("Region"),
            account=MetadataItem("Account"),
            notes=MetadataItem("Notes"),
        )
        self.additional: List[IDatalistItem] = [
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

    def _parse_plugin(self, pluginname: str, pluginfile: Path) -> Optional[PluginMetadata]:
        with pluginfile.open() as handle:
            # read until the first token has been parsed
            for tokeninfo in tokenize.generate_tokens(handle.readline):
                # the very first token needs to be a string / block comment with the metadata
                if tokeninfo.type != tokenize.STRING or not self._re_metadata_item.search(tokeninfo.string):
                    return
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
                raise ExtensionError(f"Error while parsing plugin file {pluginfile.name}", err)


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
