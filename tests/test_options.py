from __future__ import annotations

import argparse

import pytest

from streamlink.options import Argument, Arguments, Options
from streamlink.utils.args import comma_list_filter


class TestOptions:
    @pytest.fixture()
    def options(self):
        return Options({
            "foo-bar": "1",
            "baz_qux": "2",
        })

    def test_defaults(self, options: Options):
        empty = Options()
        assert empty == {}
        assert empty.defaults == {}

        assert options.defaults == {
            "foo-bar": "1",
            "baz-qux": "2",
        }
        assert options == options.defaults

    def test_get_set(self, options: Options):
        assert options.get("foo-bar") == "1"
        assert options["foo-bar"] == "1"
        assert options.get("baz_qux") == "2"
        assert options["baz_qux"] == "2"

        assert options.get("non_existing") is None
        assert options["non_existing"] is None

        options.set("abc-def", 3.14)
        assert options.get("abc-def") == 3.14
        assert options.get("abc-def") == 3.14

        obj = object()
        options["foo_bar"] = obj
        assert options.get("foo-bar") is obj
        assert options.get("foo_bar") is obj

        assert list(options.items()) == [
            ("foo-bar", obj),
            ("baz-qux", "2"),
            ("abc-def", 3.14),
        ]

    def test_update(self, options: Options):
        assert options.get("foo-bar") == "1"
        assert options.get("non_existing") is None

        options.update({"foo-bar": "value"})
        assert options.get("foo-bar") == "value"

        other = Options({"foo-bar": "VALUE"})
        other.set("abc", "def")
        options.update(other)

        assert list(options.items()) == [
            ("foo-bar", "VALUE"),
            ("baz-qux", "2"),
            ("abc", "def"),
        ]

    def test_clear(self, options: Options):
        assert options.get("foo-bar") == "1"
        options.set("foo-bar", "other")
        assert options.get("foo-bar") == "other"
        options.clear()
        assert options.get("foo-bar") == "1"


class TestMappedOptions:
    class MappedOptions(Options):
        def _get_uppercase(self, key):
            return self.get_explicit(key.upper())

        def _get_add(self, key):
            return int(self.get_explicit(key)) + 1

        def _set_uppercase(self, key, value):
            self.set_explicit(key.upper(), value)

        def _set_add(self, key, value):
            self.set_explicit(key, int(value) + 1)

        _MAP_GETTERS = {
            "foo-bar": _get_uppercase,
            "baz": _get_add,
        }

        _MAP_SETTERS = {
            "foo-bar": _set_uppercase,
            "baz": _set_add,
        }

    @pytest.fixture()
    def options(self):
        return self.MappedOptions({"foo-bar": 123, "baz": 100})

    def test_mapped_key(self, options: MappedOptions):
        assert options.get("foo-bar") is None
        assert options.get("foo_bar") is None
        assert options.get_explicit("foo-bar") == 123
        assert options.get_explicit("foo_bar") == 123
        assert options.get_explicit("FOO-BAR") is None
        assert options.get_explicit("FOO_BAR") is None

        options.set("foo-bar", 321)
        assert options.get("foo-bar") == 321
        assert options.get("foo_bar") == 321
        assert options.get_explicit("foo-bar") == 123
        assert options.get_explicit("foo_bar") == 123
        assert options.get_explicit("FOO-BAR") == 321
        assert options.get_explicit("FOO_BAR") == 321

    def test_mapped_value(self, options: MappedOptions):
        assert options.get("baz") == 101
        assert options.get_explicit("baz") == 100

        options.set("baz", 0)
        assert options.get("baz") == 2
        assert options.get_explicit("baz") == 1

    def test_mutablemapping_methods(self, options: MappedOptions):
        options["key"] = "value"
        assert options["key"] == "value"

        assert options["foo-bar"] is None

        options["baz"] = 0
        assert options["baz"] == 2

        assert "foo-bar" in options
        assert "qux" not in options

        assert len(options) == 3

        assert list(iter(options)) == ["foo-bar", "baz", "key"]
        assert list(options.keys()) == ["foo-bar", "baz", "key"]
        assert list(options.values()) == [123, 1, "value"]
        assert list(options.items()) == [("foo-bar", 123), ("baz", 1), ("key", "value")]


class TestArgument:
    def test_name(self):
        assert Argument("test-arg").argument_name("plugin") == "--plugin-test-arg"
        assert Argument("test-arg").namespace_dest("plugin") == "plugin_test_arg"
        assert Argument("test-arg").dest == "test_arg"

    def test_name_plugin(self):
        assert Argument("test-arg").argument_name("test_plugin") == "--test-plugin-test-arg"
        assert Argument("test-arg").namespace_dest("test_plugin") == "test_plugin_test_arg"
        assert Argument("test-arg").dest == "test_arg"

    def test_name_override(self):
        assert Argument("test", argument_name="override-name").argument_name("plugin") == "--override-name"
        assert Argument("test", argument_name="override-name").namespace_dest("plugin") == "override_name"
        assert Argument("test", argument_name="override-name").dest == "test"

    def test_default(self):
        arg = Argument("test", default=123)
        assert arg.default == 123
        with pytest.raises(AttributeError):
            # noinspection PyPropertyAccess
            arg.default = 456

    def test_help_suppress(self):
        argA = Argument("test", help="test")
        argB = Argument("test", help=argparse.SUPPRESS)
        argC = Argument("test", help=f"{argparse.SUPPRESS[:1]}{argparse.SUPPRESS[1:]}")
        assert argA.help is not argparse.SUPPRESS
        assert id(argB.help) == id(argparse.SUPPRESS)
        assert id(argC.help) == id(argparse.SUPPRESS)

    def test_options(self):
        arg = Argument(
            "test",
            action="append",
            nargs=2,
            default=(0, 0),
            type=int,
            choices=[1, 2, 3],
            required=True,
            help=argparse.SUPPRESS,
            metavar=("ONE", "TWO"),
            dest="dest",
            requires=["other"],
            prompt="Test!",
            sensitive=False,
            argument_name=None,
        )
        assert arg.options == {
            "action": "append",
            "nargs": 2,
            "default": (0, 0),
            "type": int,
            "choices": (1, 2, 3),
            "help": argparse.SUPPRESS,
            "metavar": ("ONE", "TWO"),
            "dest": "dest",
        }

        arg = Argument(
            "test",
            action="store_const",
            const=123,
        )
        assert arg.options == {
            "action": "store_const",
            "const": 123,
        }

        # doesn't include the const keyword if action is store_true or store_false
        assert Argument("test", action="store_true").options == {"action": "store_true", "default": False}
        assert Argument("test", action="store_true", default=123).options == {"action": "store_true", "default": 123}
        assert Argument("test", action="store_false").options == {"action": "store_false", "default": True}
        assert Argument("test", action="store_false", default=123).options == {"action": "store_false", "default": 123}

    def test_equality(self):
        a1 = Argument(
            "test",
            action="append",
            nargs=2,
            default=("0", "0"),
            type=comma_list_filter(["1", "2", "3"], unique=True),
            choices=["1", "2", "3"],
            required=True,
            help=argparse.SUPPRESS,
            metavar=("ONE", "TWO"),
            dest="dest",
            requires=["other"],
            prompt="Test!",
            sensitive=False,
            argument_name="custom-name",
        )
        a2 = Argument(
            "test",
            action="append",
            nargs=2,
            default=("0", "0"),
            type=comma_list_filter(["1", "2", "3"], unique=True),
            choices=["1", "2", "3"],
            required=True,
            help=argparse.SUPPRESS,
            metavar=("ONE", "TWO"),
            dest="dest",
            requires=["other"],
            prompt="Test!",
            sensitive=False,
            argument_name="custom-name",
        )
        a3 = Argument("foo")
        assert a1 is not a2
        assert a1 == a2
        assert a1 != a3
        assert a2 != a3

    @pytest.mark.parametrize(
        ("action", "default", "expected_const", "expected_default"),
        [
            pytest.param("store_true", None, True, False, id="store_true-no-default"),
            pytest.param("store_true", "default", True, "default", id="store_true-with-default"),
            pytest.param("store_false", None, False, True, id="store_false-no-default"),
            pytest.param("store_false", "default", False, "default", id="store_false-with-default"),
        ],
    )
    def test_store_true_false(self, action: str, default: str | None, expected_const: bool, expected_default: str | None):
        arg = Argument("foo", action=action, default=default)
        assert arg.const is expected_const
        assert arg.default is expected_default


class TestArguments:
    def test_getter(self):
        test1 = Argument("test1")
        test2 = Argument("test2")
        args = Arguments(test1, test2)

        assert args.get("test1") == test1
        assert args.get("test2") == test2
        assert args.get("test3") is None

    def test_iter(self):
        test1 = Argument("test1")
        test2 = Argument("test2")
        args = Arguments(test1, test2)

        i_args = iter(args)
        assert next(i_args) == test1
        assert next(i_args) == test2

    def test_add(self):
        test1 = Argument("test1")
        test2 = Argument("test2")
        test3 = Argument("test3")
        args = Arguments(test1, test2)

        assert list(iter(args)) == [test1, test2]
        args.add(test3)
        assert list(iter(args)) == [test3, test1, test2]

    def test_equality(self):
        test1 = Arguments()
        test1.add(Argument("testA"))
        test1.add(Argument("testB"))
        test2 = Arguments(Argument("testB"), Argument("testA"))
        test3 = Arguments(Argument("testA"), Argument("testB"))
        assert test1 == test2
        assert test1 != test3
        assert test2 != test3

    def test_requires(self):
        test1 = Argument("test1", requires="test2")
        test2 = Argument("test2", requires="test3")
        test3 = Argument("test3")
        args = Arguments(test1, test2, test3)

        assert list(args.requires("test1")) == [test2, test3]

    def test_requires_invalid(self):
        test1 = Argument("test1", requires="test2")
        args = Arguments(test1)

        with pytest.raises(KeyError) as cm:
            list(args.requires("test1"))
        assert cm.value.args[0] == "test2 is not a valid argument for this plugin"

    @pytest.mark.parametrize(
        "args",
        [
            pytest.param(
                Arguments(
                    Argument("test1", requires="test2"),
                    Argument("test2", requires="test1"),
                ),
                id="Cycle",
            ),
            pytest.param(
                Arguments(
                    Argument("test1", requires="test2"),
                    Argument("test2", requires="test3"),
                    Argument("test3", requires="test1"),
                ),
                id="Cycle deep",
            ),
            pytest.param(
                Arguments(
                    Argument("test1", requires="test1"),
                ),
                id="Cycle self",
            ),
        ],
    )
    def test_requires_cycle(self, args: Arguments):
        with pytest.raises(RuntimeError) as cm:
            list(args.requires("test1"))
        assert cm.value.args[0] == "cycle detected in plugin argument config"
