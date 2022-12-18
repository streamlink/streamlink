import pytest

from streamlink.options import Argument, Arguments, Options


class TestOptions:
    @pytest.fixture()
    def options(self):
        return Options({
            "a_default": "default",
            "another-default": "default2",
        })

    def test_empty(self):
        options = Options()
        assert not options.defaults
        assert not options.options

    def test_set(self, options: Options):
        assert options.get("a_default") == "default"
        assert options.get("non_existing") is None

        options.set("an_option", "option")
        assert options.get("an_option") == "option"

    def test_update(self, options: Options):
        assert options.get("a_default") == "default"
        assert options.get("non_existing") is None

        options.update({"an_option": "option"})
        assert options.get("an_option") == "option"

    def test_name_normalised(self, options: Options):
        assert options.get("a_default") == "default"
        assert options.get("a-default") == "default"
        assert options.get("another-default") == "default2"
        assert options.get("another_default") == "default2"

    def test_clear(self, options: Options):
        assert options.get("a_default") == "default"
        options.set("a_default", "other")
        assert options.get("a_default") == "other"
        options.clear()
        assert options.get("a_default") == "default"


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

    @pytest.mark.parametrize("args", [
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
    ])
    def test_requires_cycle(self, args: Arguments):
        with pytest.raises(RuntimeError) as cm:
            list(args.requires("test1"))
        assert cm.value.args[0] == "cycle detected in plugin argument config"
