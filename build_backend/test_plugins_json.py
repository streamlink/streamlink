from __future__ import annotations

import ast
import re
from contextlib import nullcontext, suppress
from pathlib import Path
from textwrap import dedent
from typing import Any

import pytest

from build_backend.plugins_json import (
    PLUGINSJSON_COMMENTS,
    ParseConstantOrSequenceOfConstants,
    ParseMappingOfConstants,
    ParseSequenceOfConstants,
    PluginArgument,
    PluginMatcher,
    PluginVisitor,
    build,
    to_json,
)


does_not_raise = nullcontext()


class ConstantOrSequenceOfConstants(ParseConstantOrSequenceOfConstants):
    TYPE = bool, int, float, str
    REQUIRED = False


class SequenceOfConstants(ParseSequenceOfConstants):
    TYPE = bool, int, float, str
    REQUIRED = False


class MappingOfConstants(ParseMappingOfConstants):
    TYPE = bool, int, float, str
    REQUIRED = False


@pytest.mark.parametrize(
    ("parser", "code", "expected", "raises"),
    [
        pytest.param(
            SequenceOfConstants,
            """None""",
            None,
            does_not_raise,
            id="soc-optional",
        ),
        pytest.param(
            SequenceOfConstants,
            """[None,True,False,1,2,3.14,"a"]""",
            [None, True, False, 1, 2, 3.14, "a"],
            does_not_raise,
            id="soc-sequence",
        ),
        pytest.param(
            SequenceOfConstants,
            """1""",
            None,
            pytest.raises(ValueError, match=r"^Invalid constant type$"),
            id="soc-not-a-sequence",
        ),
        pytest.param(
            SequenceOfConstants,
            """[1,2,[]]""",
            None,
            pytest.raises(ValueError, match=r"^Invalid constant type$"),
            id="soc-no-nested-sequences",
        ),
        pytest.param(
            ConstantOrSequenceOfConstants,
            """None""",
            None,
            does_not_raise,
            id="cosoc-optional",
        ),
        pytest.param(
            ConstantOrSequenceOfConstants,
            """True""",
            True,
            does_not_raise,
            id="cosoc-constant",
        ),
        pytest.param(
            ConstantOrSequenceOfConstants,
            """[None,True,False,1,2,3.14,"a"]""",
            [None, True, False, 1, 2, 3.14, "a"],
            does_not_raise,
            id="cosoc-sequence",
        ),
        pytest.param(
            ConstantOrSequenceOfConstants,
            """[1,2,[]]""",
            None,
            pytest.raises(ValueError, match=r"^Invalid constant type$"),
            id="cosoc-no-nested-sequences",
        ),
        pytest.param(
            MappingOfConstants,
            """None""",
            None,
            does_not_raise,
            id="moc-optional",
        ),
        pytest.param(
            MappingOfConstants,
            """{"a": True, "b": 1, "c": 3.14, "d": "d", "e": [False, 2, 0.1, "x"]}""",
            {"a": True, "b": 1, "c": 3.14, "d": "d", "e": [False, 2, 0.1, "x"]},
            does_not_raise,
            id="moc-mapping",
        ),
        pytest.param(
            MappingOfConstants,
            """1""",
            None,
            pytest.raises(ValueError, match=r"^Invalid constant type$"),
            id="moc-not-a-mapping",
        ),
        pytest.param(
            MappingOfConstants,
            """[1]""",
            None,
            pytest.raises(ValueError, match=r"^Invalid constant type$"),
            id="moc-no-sequences",
        ),
        pytest.param(
            MappingOfConstants,
            """{"a": {}}""",
            None,
            pytest.raises(ValueError, match=r"^Invalid constant type$"),
            id="moc-no-nested-mappings",
        ),
    ],
)
def test_parse_sequence_or_mapping(parser: type[ast.NodeVisitor], code: str, expected: Any, raises: nullcontext):
    tree = ast.parse(code)
    item: ast.AST = tree.body[0].value  # type: ignore
    with raises:
        assert parser().visit(item) == expected


@pytest.mark.parametrize(
    ("code", "expected", "raises"),
    [
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"foo"))
                class NotAPlugin: pass
            """),
            [],
            does_not_raise,
            id="no-plugin-subclass",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"foo"))
                class NotAPlugin(GetBaseClass(), SomethingElse): pass
            """),
            [],
            does_not_raise,
            id="no-plugin-subclass2",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher
                class TestPlugin(Plugin): pass
            """),
            [],
            does_not_raise,
            id="no-decorator-call",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"foo"))
                @pluginmatcher(re.compile(pattern=r"foo"))
                @pluginmatcher(pattern=re.compile(r"foo"))
                @pluginmatcher(pattern=re.compile(pattern=r"foo"))
                @pluginmatcher(re.compile(r"bar", re.IGNORECASE))
                @pluginmatcher(re.compile(r"bar", flags=re.IGNORECASE))
                @pluginmatcher(pattern=re.compile(r"bar", re.IGNORECASE))
                @pluginmatcher(pattern=re.compile(r"bar", flags=re.IGNORECASE))
                @pluginmatcher(re.compile(r"baz", re.I | re.S | re.X))
                @pluginmatcher(re.compile(r"baz", flags=re.I | re.S | re.X))
                class TestPlugin(Plugin): pass
            """),
            [
                PluginMatcher(pattern="foo", flags=None, priority=None, name=None),
                PluginMatcher(pattern="foo", flags=None, priority=None, name=None),
                PluginMatcher(pattern="foo", flags=None, priority=None, name=None),
                PluginMatcher(pattern="foo", flags=None, priority=None, name=None),
                PluginMatcher(pattern="bar", flags=re.IGNORECASE, priority=None, name=None),
                PluginMatcher(pattern="bar", flags=re.IGNORECASE, priority=None, name=None),
                PluginMatcher(pattern="bar", flags=re.IGNORECASE, priority=None, name=None),
                PluginMatcher(pattern="bar", flags=re.IGNORECASE, priority=None, name=None),
                PluginMatcher(pattern="baz", flags=re.I | re.S | re.X, priority=None, name=None),
                PluginMatcher(pattern="baz", flags=re.I | re.S | re.X, priority=None, name=None),
            ],
            does_not_raise,
            id="pattern",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher()
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Missing @pluginmatcher pattern$"),
            id="pattern-missing",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(invalid)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginmatcher pattern: unknown AST node$"),
            id="pattern-invalid",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(get_pattern_object())
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginmatcher pattern: not a compiled regex$"),
            id="pattern-invalid-regex",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r'''  not a verbose regex pattern  '''))
                @pluginmatcher(re.compile(r'''
                    a\\sverbose[ ]+
                    regex\\ pattern
                ''', flags=re.VERBOSE))
                class TestPlugin(Plugin): pass
            """),
            [
                PluginMatcher(
                    pattern="  not a verbose regex pattern  ",
                    flags=None,
                    priority=None,
                    name=None,
                ),
                PluginMatcher(
                    pattern="a\\sverbose[ ]+regex\\ pattern",
                    flags=re.VERBOSE,
                    priority=None,
                    name=None,
                ),
            ],
            does_not_raise,
            id="pattern-pattern-verbose",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile())
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginmatcher pattern: missing pattern$"),
            id="pattern-pattern-missing",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(foo()))
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginmatcher pattern: unknown AST node$"),
            id="pattern-pattern-invalid-arg",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(pattern=foo()))
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginmatcher pattern: unknown AST node$"),
            id="pattern-pattern-invalid-kwarg",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"foo", 123))
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Unsupported node type$"),
            id="pattern-flag-invalid-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"foo", re.MULTILINE))
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid attribute$"),
            id="pattern-flag-invalid-attribute",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"foo", re.IGNORECASE & re.VERBOSE))
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Unsupported binary operator$"),
            id="pattern-flag-invalid-binary-operator",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"empty"))
                @pluginmatcher(re.compile(r"0"), 0)
                @pluginmatcher(re.compile(r"123"), priority=123)
                @pluginmatcher(re.compile(r"NO"), priority=NO_PRIORITY)
                @pluginmatcher(re.compile(r"LOW"), priority=LOW_PRIORITY)
                @pluginmatcher(re.compile(r"NORMAL"), priority=NORMAL_PRIORITY)
                @pluginmatcher(re.compile(r"HIGH"), priority=HIGH_PRIORITY)
                class TestPlugin(Plugin): pass
            """),
            [
                PluginMatcher(pattern="empty", flags=None, priority=None, name=None),
                PluginMatcher(pattern="0", flags=None, priority=0, name=None),
                PluginMatcher(pattern="123", flags=None, priority=123, name=None),
                PluginMatcher(pattern="NO", flags=None, priority=PluginMatcher.NO_PRIORITY, name=None),
                PluginMatcher(pattern="LOW", flags=None, priority=PluginMatcher.LOW_PRIORITY, name=None),
                PluginMatcher(pattern="NORMAL", flags=None, priority=PluginMatcher.NORMAL_PRIORITY, name=None),
                PluginMatcher(pattern="HIGH", flags=None, priority=PluginMatcher.HIGH_PRIORITY, name=None),
            ],
            does_not_raise,
            id="priority",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"unknown"), priority=foo())
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginmatcher priority: unknown AST node$"),
            id="priority-invalid-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"unknown"), priority=123.456)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginmatcher priority type$"),
            id="priority-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"unknown"), priority=UNKNOWN)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Unknown @pluginmatcher priority name$"),
            id="priority-unknown-name",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"one"), NORMAL_PRIORITY, "one")
                @pluginmatcher(re.compile(r"two"), NORMAL_PRIORITY, None)
                @pluginmatcher(re.compile(r"three"), name="three")
                @pluginmatcher(re.compile(r"four"), name=None)
                @pluginmatcher(name="five", pattern=re.compile(r"five"))
                class TestPlugin(Plugin): pass
            """),
            [
                PluginMatcher(pattern="one", flags=None, priority=PluginMatcher.NORMAL_PRIORITY, name="one"),
                PluginMatcher(pattern="two", flags=None, priority=PluginMatcher.NORMAL_PRIORITY, name=None),
                PluginMatcher(pattern="three", flags=None, priority=None, name="three"),
                PluginMatcher(pattern="four", flags=None, priority=None, name=None),
                PluginMatcher(pattern="five", flags=None, priority=None, name="five"),
            ],
            does_not_raise,
            id="name",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"."), name=NAME)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginmatcher name: unknown AST node$"),
            id="name-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"."), name=123)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginmatcher name type$"),
            id="name-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"."), NORMAL_PRIORITY, "name", 123)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid number of arguments$"),
            id="invalid-arguments-number",
        ),
        pytest.param(
            dedent("""
                @pluginmatcher(re.compile(r"."), invalid=123)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid keyword argument$"),
            id="invalid-keyword",
        ),
    ],
)
def test_pluginmatcher(code: str, expected: list, raises: nullcontext):
    tree = ast.parse(code)
    pluginvisitor = PluginVisitor()
    with raises:
        pluginvisitor.visit(tree)
        assert pluginvisitor.matchers == expected


@pytest.mark.parametrize(
    ("code", "expected", "raises"),
    [
        pytest.param(
            dedent("""
                @pluginargument("foo")
                @pluginargument(name="bar")
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo"),
                PluginArgument(name="bar"),
            ],
            does_not_raise,
            id="name",
        ),
        pytest.param(
            dedent("""
                @pluginargument()
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Missing @pluginargument name$"),
            id="name-missing",
        ),
        pytest.param(
            dedent("""
                @pluginargument(name=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument name: unknown AST node$"),
            id="name-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument(name=123)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument name type$"),
            id="name-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", action=None)
                @pluginargument("bar", action="store_true")
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", action=None),
                PluginArgument(name="bar", action="store_true"),
            ],
            does_not_raise,
            id="action",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", action=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument action: unknown AST node$"),
            id="action-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", action=123)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument action type$"),
            id="action-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", nargs=None)
                @pluginargument("bar", nargs=2)
                @pluginargument("baz", nargs="?")
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", nargs=None),
                PluginArgument(name="bar", nargs=2),
                PluginArgument(name="baz", nargs="?"),
            ],
            does_not_raise,
            id="nargs",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", nargs=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument nargs: unknown AST node$"),
            id="nargs-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", nargs=123.456)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument nargs type$"),
            id="nargs-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", const=None)
                @pluginargument("bar", const=1)
                @pluginargument("baz", const=["a", 2, 3.14, True])
                @pluginargument("qux", const=("a", 2, 3.14, True))
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", const=None),
                PluginArgument(name="bar", const=1),
                PluginArgument(name="baz", const=["a", 2, 3.14, True]),
                PluginArgument(name="qux", const=["a", 2, 3.14, True]),
            ],
            does_not_raise,
            id="const",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", const=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument const: unknown AST node$"),
            id="const-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", const=[[]])
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument const type$"),
            id="const-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", default=None)
                @pluginargument("bar", default=1)
                @pluginargument("baz", default=["a", 2, 3.14, True])
                @pluginargument("qux", default=("a", 2, 3.14, True))
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", default=None),
                PluginArgument(name="bar", default=1),
                PluginArgument(name="baz", default=["a", 2, 3.14, True]),
                PluginArgument(name="qux", default=["a", 2, 3.14, True]),
            ],
            does_not_raise,
            id="default",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", default=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument default: unknown AST node$"),
            id="default-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", default=[[]])
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument default type$"),
            id="default-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", type=None)
                @pluginargument("bar", type="comma_list")
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", type=None),
                PluginArgument(name="bar", type="comma_list"),
            ],
            does_not_raise,
            id="type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", type=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument type: unknown AST node$"),
            id="type-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", type=123)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument type type$"),
            id="type-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", type_args=None)
                @pluginargument("bar", type_args=["a", 2, 3.14, True])
                @pluginargument("baz", type_args=("a", 2, 3.14, True))
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", type_args=None),
                PluginArgument(name="bar", type_args=["a", 2, 3.14, True]),
                PluginArgument(name="baz", type_args=["a", 2, 3.14, True]),
            ],
            does_not_raise,
            id="type-args",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", type_args=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument type_args: unknown AST node$"),
            id="type-args-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", type_args=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument type_args type$"),
            id="type-args-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", type_kwargs=None)
                @pluginargument("bar", type_kwargs={"a": True, "b": 1, "c": 3.14, "d": "d", "e": [False, 2, 0.1, "x"]})
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", type_kwargs=None),
                PluginArgument(name="bar", type_kwargs={"a": True, "b": 1, "c": 3.14, "d": "d", "e": [False, 2, 0.1, "x"]}),
            ],
            does_not_raise,
            id="type-kwargs",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", type_kwargs=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument type_kwargs: unknown AST node$"),
            id="type-kwargs-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", type_kwargs=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument type_kwargs type$"),
            id="type-kwargs-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", choices=None)
                @pluginargument("bar", choices=["a", 2, 3.14, True])
                @pluginargument("baz", choices=("a", 2, 3.14, True))
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", choices=None),
                PluginArgument(name="bar", choices=["a", 2, 3.14, True]),
                PluginArgument(name="baz", choices=["a", 2, 3.14, True]),
            ],
            does_not_raise,
            id="choices",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", choices=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument choices: unknown AST node$"),
            id="choices-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", choices=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument choices type$"),
            id="choices-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", required=None)
                @pluginargument("bar", required=True)
                @pluginargument("baz", required=False)
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", required=None),
                PluginArgument(name="bar", required=True),
                PluginArgument(name="baz", required=False),
            ],
            does_not_raise,
            id="required",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", required=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument required: unknown AST node$"),
            id="required-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", required=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument required type$"),
            id="required-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", help=argparse.SUPPRESS)
                @pluginargument("bar", help="==SUPPRESS==")
                @pluginargument("baz", help="help")
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", help="==SUPPRESS=="),
                PluginArgument(name="bar", help="==SUPPRESS=="),
                PluginArgument(name="baz", help="help"),
            ],
            does_not_raise,
            id="help",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", help=other.SUPPRESS)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument help type$"),
            id="help-not-argparse-suppress",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", help=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument help: unknown AST node$"),
            id="help-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", help=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument help type$"),
            id="help-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", metavar=None)
                @pluginargument("bar", metavar="bar")
                @pluginargument("baz", metavar=["foo", "bar"])
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", metavar=None),
                PluginArgument(name="bar", metavar="bar"),
                PluginArgument(name="baz", metavar=["foo", "bar"]),
            ],
            does_not_raise,
            id="metavar",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", metavar=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument metavar: unknown AST node$"),
            id="metavar-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", metavar=[1])
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument metavar type$"),
            id="metavar-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", dest=None)
                @pluginargument("bar", dest="bar")
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", dest=None),
                PluginArgument(name="bar", dest="bar"),
            ],
            does_not_raise,
            id="dest",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", dest=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument dest: unknown AST node$"),
            id="dest-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", dest=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument dest type$"),
            id="dest-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", requires=None)
                @pluginargument("bar", requires="foo")
                @pluginargument("baz", requires=["foo", "bar"])
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", requires=None),
                PluginArgument(name="bar", requires="foo"),
                PluginArgument(name="baz", requires=["foo", "bar"]),
            ],
            does_not_raise,
            id="requires",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", requires=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument requires: unknown AST node$"),
            id="requires-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", requires=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument requires type$"),
            id="requires-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", prompt=None)
                @pluginargument("bar", prompt="bar")
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", prompt=None),
                PluginArgument(name="bar", prompt="bar"),
            ],
            does_not_raise,
            id="prompt",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", prompt=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument prompt: unknown AST node$"),
            id="prompt-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", prompt=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument prompt type$"),
            id="prompt-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", sensitive=None)
                @pluginargument("bar", sensitive=True)
                @pluginargument("baz", sensitive=False)
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", sensitive=None),
                PluginArgument(name="bar", sensitive=True),
                PluginArgument(name="baz", sensitive=False),
            ],
            does_not_raise,
            id="sensitive",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", sensitive=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument sensitive: unknown AST node$"),
            id="sensitive-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", sensitive=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument sensitive type$"),
            id="sensitive-invalid-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", argument_name=None)
                @pluginargument("bar", argument_name="bar")
                class TestPlugin(Plugin): pass
            """),
            [
                PluginArgument(name="foo", argument_name=None),
                PluginArgument(name="bar", argument_name="bar"),
            ],
            does_not_raise,
            id="argument-name",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", argument_name=INVALID)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument argument_name: unknown AST node$"),
            id="argument-name-unknown-node-type",
        ),
        pytest.param(
            dedent("""
                @pluginargument("foo", argument_name=1)
                class TestPlugin(Plugin): pass
            """),
            None,
            pytest.raises(ValueError, match=r"^Invalid @pluginargument argument_name type$"),
            id="argument-name-invalid-type",
        ),
    ],
)
def test_pluginargument(code: str, expected: list, raises: nullcontext):
    tree = ast.parse(code)
    pluginvisitor = PluginVisitor()
    with raises:
        pluginvisitor.visit(tree)
        assert pluginvisitor.arguments == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        pytest.param(
            dedent("""
                class TestPlugin(Plugin): pass
            """),
            False,
            id="does-not-export",
        ),
        pytest.param(
            dedent("""
                class TestPlugin(Plugin): pass
                __plugin__ = TestPlugin
            """),
            True,
            id="exports",
        ),
    ],
)
def test_exports(code: str, expected: bool):
    tree = ast.parse(code)
    pluginvisitor = PluginVisitor()
    pluginvisitor.visit(tree)
    assert pluginvisitor.exports == expected


@pytest.fixture()
def test_plugin_code(request: pytest.FixtureRequest):
    faulty = getattr(request, "param", {}).get("faulty", False)

    return dedent(f"""
        import argparse
        import re

        from streamlink.plugin import LOW_PRIORITY, Plugin, pluginargument, pluginmatcher


        @pluginmatcher(re.compile("https://a"))
        @pluginmatcher(name="b", pattern=re.compile("https://b", re.IGNORECASE), priority=LOW_PRIORITY)
        @pluginmatcher(name="c", pattern=re.compile("https://c", re.I | re.X), priority=20)
        @pluginargument(
            "a",
            type="comma_list_filter",
            type_kwargs={{"acceptable": ["a", "b"]}},
            default=["a"],
            help="a",
        )
        @pluginargument(
            "b",
            requires="a",
            sensitive={"True" if not faulty else "INVALID"},
            help=argparse.SUPPRESS,
        )
        class TestPlugin(Plugin):
            def _get_streams(self):
                return None

        __plugin__ = TestPlugin
    """).strip()


@pytest.fixture()
def test_plugins_dir(tmp_path: Path, test_plugin_code: str):
    file_path = tmp_path / "testplugin.py"
    try:
        with file_path.open("w", encoding="utf-8") as fp:
            fp.write(test_plugin_code)
        yield tmp_path
    finally:
        with suppress(FileNotFoundError):
            file_path.unlink()


def test_plugin(test_plugin_code: str):
    tree = ast.parse(test_plugin_code)
    pluginvisitor = PluginVisitor()
    pluginvisitor.visit(tree)

    assert pluginvisitor.exports
    assert pluginvisitor.matchers == [
        PluginMatcher(pattern="https://a", flags=None, priority=None, name=None),
        PluginMatcher(pattern="https://b", flags=re.IGNORECASE, priority=PluginMatcher.LOW_PRIORITY, name="b"),
        PluginMatcher(pattern="https://c", flags=re.I | re.X, priority=20, name="c"),
    ]
    assert pluginvisitor.arguments == [
        PluginArgument(name="a", type="comma_list_filter", type_kwargs={"acceptable": ["a", "b"]}, default=["a"], help="a"),
        PluginArgument(name="b", requires="a", sensitive=True, help="==SUPPRESS=="),
    ]


@pytest.mark.parametrize(
    ("comments", "expected_comments"),
    [
        pytest.param(
            None,
            PLUGINSJSON_COMMENTS,
            id="default",
        ),
        pytest.param(
            ["foo", "bar"],
            ["foo", "bar"],
            id="custom",
        ),
        pytest.param(
            [],
            [],
            id="empty",
        ),
    ],
)
def test_build(
    capsys: pytest.CaptureFixture,
    test_plugins_dir: Path,
    comments: list[str] | None,
    expected_comments: list[str],
):
    data = build(test_plugins_dir)
    to_json(data, comments=comments, pretty=True)
    out, _err = capsys.readouterr()
    assert (
        out
        == "".join(f"// {comment}\n" for comment in expected_comments)
        + dedent(
            """
                {
                  "testplugin": {
                    "matchers": [
                      {
                        "pattern": "https://a"
                      },
                      {
                        "pattern": "https://b",
                        "flags": 2,
                        "priority": 10,
                        "name": "b"
                      },
                      {
                        "pattern": "https://c",
                        "flags": 66,
                        "priority": 20,
                        "name": "c"
                      }
                    ],
                    "arguments": [
                      {
                        "name": "a",
                        "default": [
                          "a"
                        ],
                        "type": "comma_list_filter",
                        "type_kwargs": {
                          "acceptable": [
                            "a",
                            "b"
                          ]
                        },
                        "help": "a"
                      },
                      {
                        "name": "b",
                        "help": "==SUPPRESS==",
                        "requires": "a",
                        "sensitive": true
                      }
                    ]
                  }
                }
            """,
        ).strip()
    )


@pytest.mark.parametrize("test_plugin_code", [{"faulty": True}], indirect=True)
def test_build_faulty(capsys: pytest.CaptureFixture, test_plugins_dir: Path, test_plugin_code: str):
    with pytest.raises(SyntaxError) as cm:
        build(test_plugins_dir)
    out, err = capsys.readouterr()
    assert not out
    assert not err

    assert cm.value
    msg, (filename, lineno, column, line) = cm.value.args
    assert msg == "Invalid @pluginargument sensitive: unknown AST node"
    assert filename == "testplugin.py"
    assert lineno == 20
    assert column == 15
    assert line == "    sensitive=INVALID,"
    assert cm.value.__cause__ is None
