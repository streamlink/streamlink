from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TextIO, TypeVar


if TYPE_CHECKING:
    from typing_extensions import TypeAlias


DEFAULT_PLUGINSPATH = Path(__file__).parents[1] / "src" / "streamlink" / "plugins"

PLUGINSJSON_COMMENTS = [
    "DO NOT MODIFY!",
    "This file was auto-generated and its checksum is validated before loading.",
    "If you want to modify existing plugins, then please see the plugin-sideloading or developing docs:",
    "https://streamlink.github.io/",
]

TListOfConstants: TypeAlias = "list[bool | int | float | str | None]"
TConstantOrListOfConstants: TypeAlias = "bool | int | float | str | TListOfConstants | None"
TMappingOfConstantOrListOfConstants: TypeAlias = "dict[str, TConstantOrListOfConstants]"


class ParseError(ValueError):
    def __init__(self, message: str, node: ast.AST):
        super().__init__(message)
        self.lineno = getattr(node, "lineno", None)
        self.col_offset = getattr(node, "col_offset", None)


@dataclass
class PluginMatcher:
    NO_PRIORITY: ClassVar[int] = 0
    LOW_PRIORITY: ClassVar[int] = 10
    NORMAL_PRIORITY: ClassVar[int] = 20
    HIGH_PRIORITY: ClassVar[int] = 30

    pattern: str
    flags: int | None = None
    priority: int | None = None
    name: str | None = None


@dataclass
class PluginArgument:
    name: str
    action: str | None = None
    nargs: int | str | None = None
    const: TConstantOrListOfConstants = None
    default: TConstantOrListOfConstants = None
    type: str | None = None
    type_args: TListOfConstants | None = None
    type_kwargs: TMappingOfConstantOrListOfConstants | None = None
    choices: TListOfConstants | None = None
    required: bool | None = None
    help: str | None = None
    metavar: str | list[str] | None = None
    dest: str | None = None
    requires: str | list[str] | None = None
    prompt: str | None = None
    sensitive: bool | None = None
    argument_name: str | None = None


@dataclass
class Plugin:
    matchers: list[PluginMatcher]
    arguments: list[PluginArgument]


_TParseResult = TypeVar("_TParseResult")


class Parser(ast.NodeVisitor, Generic[_TParseResult]):
    def visit(self, node: ast.AST) -> _TParseResult:
        return super().visit(node)


class ParseCall(ast.NodeVisitor):
    _PARSERS: ClassVar[dict[str, type[ast.NodeVisitor]]] = {}

    def visit_Call(self, node: ast.Call) -> dict[str, Any]:
        parsers = self._PARSERS

        data = {}
        parsers_list = list(parsers.items())

        for idx, arg in enumerate(node.args or []):
            if idx >= len(parsers_list):
                raise ParseError("Invalid number of arguments", arg)
            key, parser = parsers_list[idx]
            data[key] = parser().visit(arg)

        for kw in node.keywords:
            if kw.arg not in parsers:
                raise ParseError("Invalid keyword argument", kw)
            parser = parsers[kw.arg]
            data[kw.arg] = parser().visit(kw.value)

        return data


class ParseConstant(ast.NodeVisitor):
    NAME: str = "constant"
    TYPE: type | tuple[type, ...] = str
    REQUIRED: bool = False

    def generic_visit(self, node: ast.AST):
        raise ParseError(f"Invalid {self.NAME}: unknown AST node", node)

    def visit_Constant(self, node: ast.Constant):
        if (self.REQUIRED or node.value is not None) and not isinstance(node.value, self.TYPE):
            raise ParseError(f"Invalid {self.NAME} type", node)

        return node.value


class ParseConstantOrSequenceOfConstants(ParseConstant):
    def __init__(self):
        super().__init__()
        self._sequence = False

    def _visit_sequence(self, node: ast.List | ast.Tuple):
        if self._sequence:
            raise ParseError(f"Invalid {self.NAME} type", node)

        self._sequence = True

        return [self.visit(item) for item in node.elts]

    def visit_List(self, node: ast.List):
        return self._visit_sequence(node)

    def visit_Tuple(self, node: ast.Tuple):
        return self._visit_sequence(node)


class ParseSequenceOfConstants(ParseConstantOrSequenceOfConstants):
    def visit_Constant(self, node: ast.Constant):
        if (self.REQUIRED or node.value is not None) and not self._sequence:
            raise ParseError(f"Invalid {self.NAME} type", node)

        return super().visit_Constant(node)


class ParseMappingOfConstants(ParseConstantOrSequenceOfConstants):
    def __init__(self):
        super().__init__()
        self._mapping = False

    def _visit_sequence(self, node: ast.List | ast.Tuple):
        if not self._mapping:
            raise ParseError(f"Invalid {self.NAME} type", node)

        return super()._visit_sequence(node)

    def visit_Constant(self, node: ast.Constant):
        if (self.REQUIRED or node.value is not None) and not self._mapping:
            raise ParseError(f"Invalid {self.NAME} type", node)

        return super().visit_Constant(node)

    def visit_Dict(self, node: ast.Dict):
        if self._mapping:
            raise ParseError(f"Invalid {self.NAME} type", node)

        self._mapping = True

        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values) if k}


class ParseBinOpOr(ast.NodeVisitor):
    def generic_visit(self, node: ast.AST):
        raise ParseError("Unsupported node type", node)

    def visit_BinOp(self, node: ast.BinOp) -> int:
        if not isinstance(node.op, ast.BitOr):
            raise ParseError("Unsupported binary operator", node)

        return self.visit(node.left) | self.visit(node.right)


class ParsePluginMatcher(ParseCall, Parser[PluginMatcher]):
    class ParseReCompile(ParseCall):
        _RE_VERBOSE_PATTERN = re.compile(r"\n+\s{2,}")

        class ParsePattern(ParseConstant):
            NAME = "@pluginmatcher pattern"
            REQUIRED = True

        class ParseFlags(ParseBinOpOr):
            _ATTRIBUTES: ClassVar[dict[str, int]] = {
                "I": re.RegexFlag.IGNORECASE,
                "IGNORECASE": re.RegexFlag.IGNORECASE,
                "S": re.RegexFlag.DOTALL,
                "DOTALL": re.RegexFlag.DOTALL,
                "X": re.RegexFlag.VERBOSE,
                "VERBOSE": re.RegexFlag.VERBOSE,
            }

            def visit_Attribute(self, node: ast.Attribute) -> int:
                if not isinstance(node.value, ast.Name) or node.value.id != "re" or node.attr not in self._ATTRIBUTES:
                    raise ParseError("Invalid attribute", node)

                return self._ATTRIBUTES[node.attr]

        _PARSERS: ClassVar[dict[str, type[ast.NodeVisitor]]] = {
            "pattern": ParsePattern,
            "flags": ParseFlags,
        }

        def generic_visit(self, node: ast.AST):
            raise ParseError("Invalid @pluginmatcher pattern: unknown AST node", node)

        def visit_Call(self, node: ast.Call):
            func = node.func
            if (
                not isinstance(func, ast.Attribute)
                or func.attr != "compile"
                or not isinstance(func.value, ast.Name)
                or func.value.id != "re"
            ):
                raise ParseError("Invalid @pluginmatcher pattern: not a compiled regex", func)

            data = super().visit_Call(node)
            pattern = data.get("pattern", "")
            flags = data.get("flags", 0)

            if not pattern:
                raise ParseError("Invalid @pluginmatcher pattern: missing pattern", node)

            if flags & re.RegexFlag.VERBOSE:
                pattern = self._RE_VERBOSE_PATTERN.sub("", pattern.strip())

            return pattern, flags

    class ParsePriority(ParseConstant, ParseBinOpOr):
        NAME = "@pluginmatcher priority"
        TYPE = int

        _ATTRIBUTES: ClassVar[dict[str, int]] = {
            "NO_PRIORITY": PluginMatcher.NO_PRIORITY,
            "LOW_PRIORITY": PluginMatcher.LOW_PRIORITY,
            "NORMAL_PRIORITY": PluginMatcher.NORMAL_PRIORITY,
            "HIGH_PRIORITY": PluginMatcher.HIGH_PRIORITY,
        }

        def visit_Name(self, node: ast.Name) -> int:
            if node.id not in self._ATTRIBUTES:
                raise ParseError("Unknown @pluginmatcher priority name", node)

            return self._ATTRIBUTES[node.id]

    class ParseName(ParseConstant):
        NAME = "@pluginmatcher name"

    _PARSERS: ClassVar[dict[str, type[ast.NodeVisitor]]] = {
        "pattern": ParseReCompile,
        "priority": ParsePriority,
        "name": ParseName,
    }

    def visit_Call(self, node: ast.Call):
        data = super().visit_Call(node)
        pattern, flags = data.get("pattern", ("", 0))
        priority = data.get("priority", PluginMatcher.priority)
        name = data.get("name", PluginMatcher.name)

        if not pattern:
            raise ParseError("Missing @pluginmatcher pattern", node)

        return PluginMatcher(
            pattern=pattern,
            flags=(None if flags == 0 else flags),
            priority=priority,
            name=name,
        )


class ParsePluginArgument(ParseCall, Parser[PluginArgument]):
    class ParseName(ParseConstant):
        NAME = "@pluginargument name"
        REQUIRED = True

    class ParseAction(ParseConstant):
        NAME = "@pluginargument action"

    class ParseNArgs(ParseConstant):
        NAME = "@pluginargument nargs"
        TYPE = int, str

    class ParseConst(ParseConstantOrSequenceOfConstants):
        NAME = "@pluginargument const"
        TYPE = bool, int, float, str

    class ParseDefault(ParseConstantOrSequenceOfConstants):
        NAME = "@pluginargument default"
        TYPE = bool, int, float, str

    class ParseType(ParseConstant):
        NAME = "@pluginargument type"

    class ParseTypeArgs(ParseSequenceOfConstants):
        NAME = "@pluginargument type_args"
        TYPE = bool, int, float, str

    class ParseTypeKwargs(ParseMappingOfConstants):
        NAME = "@pluginargument type_kwargs"
        TYPE = bool, int, float, str

    class ParseChoices(ParseSequenceOfConstants):
        NAME = "@pluginargument choices"
        TYPE = bool, int, float, str

    class ParseRequired(ParseConstant):
        NAME = "@pluginargument required"
        TYPE = bool

    class ParseHelp(ParseConstant):
        NAME = "@pluginargument help"
        REQUIRED = True

        def visit_Attribute(self, node: ast.Attribute):
            if node.value.id != "argparse" or node.attr != "SUPPRESS":  # type: ignore
                raise ParseError("Invalid @pluginargument help type", node)

            return argparse.SUPPRESS

        def visit_Constant(self, node: ast.Constant):
            return dedent(super().visit_Constant(node)).strip()

    class ParseMetavar(ParseConstantOrSequenceOfConstants):
        NAME = "@pluginargument metavar"

    class ParseDest(ParseConstant):
        NAME = "@pluginargument dest"

    class ParseRequires(ParseConstantOrSequenceOfConstants):
        NAME = "@pluginargument requires"

    class ParsePrompt(ParseConstant):
        NAME = "@pluginargument prompt"

    class ParseSensitive(ParseConstant):
        NAME = "@pluginargument sensitive"
        TYPE = bool

    class ParseArgumentName(ParseConstant):
        NAME = "@pluginargument argument_name"

    _PARSERS: ClassVar[dict[str, type[ast.NodeVisitor]]] = {
        "name": ParseName,
        "action": ParseAction,
        "nargs": ParseNArgs,
        "const": ParseConst,
        "default": ParseDefault,
        "type": ParseType,
        "type_args": ParseTypeArgs,
        "type_kwargs": ParseTypeKwargs,
        "choices": ParseChoices,
        "required": ParseRequired,
        "help": ParseHelp,
        "metavar": ParseMetavar,
        "dest": ParseDest,
        "requires": ParseRequires,
        "prompt": ParsePrompt,
        "sensitive": ParseSensitive,
        "argument_name": ParseArgumentName,
    }

    def visit_Call(self, node: ast.Call):
        data = super().visit_Call(node)

        if not data.get("name"):
            raise ParseError("Missing @pluginargument name", node)

        return PluginArgument(**data)


class PluginVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.name: str | None = None
        self.matchers: list[PluginMatcher] = []
        self.arguments: list[PluginArgument] = []
        self.exports: bool = False

    def generic_visit(self, node: ast.AST):
        pass

    def visit_Module(self, node: ast.Module):
        for body in node.body:
            self.visit(body)

    def visit_Assign(self, node: ast.Assign):
        if (  # pragma: no branch
            isinstance(node.value, ast.Name)
            and node.value.id == self.name
            and self.name is not None
        ):  # fmt: skip
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__plugin__":  # pragma: no branch
                    self.exports = True

    def visit_ClassDef(self, node: ast.ClassDef):
        for base in node.bases:
            if not isinstance(base, ast.Name):
                continue
            if base.id == "Plugin":
                break
        else:
            return

        self.name = node.name
        for decorator in node.decorator_list:
            if (
                not isinstance(decorator, ast.Call)
                or not isinstance(decorator.func, ast.Name)
            ):  # fmt: skip
                continue

            if decorator.func.id == "pluginmatcher":
                matcher = ParsePluginMatcher().visit(decorator)
                self.matchers.append(matcher)
            elif decorator.func.id == "pluginargument":  # pragma: no branch
                argument = ParsePluginArgument().visit(decorator)
                self.arguments.append(argument)


Output: TypeAlias = "dict[str, Plugin]"


class JSONEncoder(json.JSONEncoder):  # pragma: no cover
    @staticmethod
    def _filter_dataclass_none_value(items: list[tuple[str, Any]]) -> dict[str, Any]:
        return {key: val for key, val in items if val is not None}

    def default(self, o: Any) -> Any:
        # https://github.com/python/mypy/issues/17550
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o, dict_factory=self._filter_dataclass_none_value)

        return super().default(o)


def build(pluginsdir: Path = DEFAULT_PLUGINSPATH) -> Output:
    data: Output = {}
    for file in pluginsdir.glob("*.py"):
        name = file.name
        plugin = re.sub(r"\.py$", "", name)
        source = file.read_text(encoding="utf-8")

        tree = ast.parse(source, str(file))
        visitor = PluginVisitor()
        try:
            visitor.visit(tree)
        except ParseError as err:
            raise SyntaxError(
                err.args[0],
                (
                    name,
                    (err.lineno or 1),
                    (err.col_offset or 0) + 1,
                    source.split("\n")[(err.lineno or 1) - 1],
                ),
            ) from None

        if not visitor.exports or not visitor.matchers:  # pragma: no cover
            continue

        data[plugin] = Plugin(visitor.matchers, visitor.arguments)

    # noinspection PyTypeChecker
    return dict(sorted(data.items()))


def to_json(data: Output, fd: TextIO | None = None, comments: list[str] | None = None, pretty: bool = False) -> None:
    outputformat = {"separators": (",", ": "), "indent": 2} if pretty else {"separators": (",", ":")}
    textio: TextIO = fd or sys.stdout
    for line in PLUGINSJSON_COMMENTS if comments is None else comments:
        textio.write(f"// {line}\n")
    json.dump(data, textio, cls=JSONEncoder, **outputformat)  # type: ignore[arg-type]


if __name__ == "__main__":  # pragma: no cover

    def main():
        parser = argparse.ArgumentParser()
        parser.add_argument("dir", nargs="?", type=Path, default=DEFAULT_PLUGINSPATH)
        parser.add_argument("--no-comments", action="store_true")
        parser.add_argument("--pretty", action="store_true")
        parser.add_argument("-o", "--output", default="-", help="Output file")

        args = parser.parse_args()
        data = build(args.dir)

        options = {"pretty": args.pretty}
        if args.no_comments:
            options["comments"] = []

        if args.output == "-":
            to_json(data, **options)
        else:
            with open(args.output, "w", encoding="utf-8") as fd:
                to_json(data, fd, **options)

    main()
