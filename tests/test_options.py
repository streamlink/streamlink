import unittest
from tests.mock import Mock

from streamlink_cli.main import setup_plugin_args
from streamlink.options import Options, Arguments, Argument


class TestOptions(unittest.TestCase):
    def setUp(self):
        self.options = Options({
            "a_default": "default",
            "another-default": "default2"
        })

    def test_options(self):
        self.assertEqual(self.options.get("a_default"), "default")
        self.assertEqual(self.options.get("non_existing"), None)

        self.options.set("a_option", "option")
        self.assertEqual(self.options.get("a_option"), "option")

    def test_options_update(self):
        self.assertEqual(self.options.get("a_default"), "default")
        self.assertEqual(self.options.get("non_existing"), None)

        self.options.update({"a_option": "option"})
        self.assertEqual(self.options.get("a_option"), "option")

    def test_options_name_normalised(self):
        self.assertEqual(self.options.get("a_default"), "default")
        self.assertEqual(self.options.get("a-default"), "default")
        self.assertEqual(self.options.get("another-default"), "default2")
        self.assertEqual(self.options.get("another_default"), "default2")


class TestArgument(unittest.TestCase):
    def test_name(self):
        self.assertEqual(Argument("test-arg").argument_name("plugin"), "--plugin-test-arg")
        self.assertEqual(Argument("test-arg").namespace_dest("plugin"), "plugin_test_arg")
        self.assertEqual(Argument("test-arg").dest, "test_arg")

    def test_name_plugin(self):
        self.assertEqual(Argument("test-arg").argument_name("test_plugin"), "--test-plugin-test-arg")
        self.assertEqual(Argument("test-arg").namespace_dest("test_plugin"), "test_plugin_test_arg")
        self.assertEqual(Argument("test-arg").dest, "test_arg")

    def test_name_override(self):
        self.assertEqual(Argument("test", argument_name="override-name").argument_name("plugin"), "--override-name")
        self.assertEqual(Argument("test", argument_name="override-name").namespace_dest("plugin"), "override_name")
        self.assertEqual(Argument("test", argument_name="override-name").dest, "test")


class TestArguments(unittest.TestCase):
    def test_getter(self):
        test1 = Argument("test1")
        test2 = Argument("test2")
        args = Arguments(test1, test2)

        self.assertEqual(args.get("test1"), test1)
        self.assertEqual(args.get("test2"), test2)
        self.assertEqual(args.get("test3"), None)

    def test_iter(self):
        test1 = Argument("test1")
        test2 = Argument("test2")
        args = Arguments(test1, test2)

        i_args = iter(args)

        self.assertEqual(next(i_args), test1)
        self.assertEqual(next(i_args), test2)

    def test_requires(self):
        test1 = Argument("test1", requires="test2")
        test2 = Argument("test2", requires="test3")
        test3 = Argument("test3")

        args = Arguments(test1, test2, test3)

        self.assertEqual(list(args.requires("test1")), [test2, test3])

    def test_requires_invalid(self):
        test1 = Argument("test1", requires="test2")

        args = Arguments(test1)

        self.assertRaises(KeyError, lambda: list(args.requires("test1")))

    def test_requires_cycle(self):
        test1 = Argument("test1", requires="test2")
        test2 = Argument("test2", requires="test1")

        args = Arguments(test1, test2)

        self.assertRaises(RuntimeError, lambda: list(args.requires("test1")))

    def test_requires_cycle_deep(self):
        test1 = Argument("test1", requires="test-2")
        test2 = Argument("test-2", requires="test3")
        test3 = Argument("test3", requires="test1")

        args = Arguments(test1, test2, test3)

        self.assertRaises(RuntimeError, lambda: list(args.requires("test1")))

    def test_requires_cycle_self(self):
        test1 = Argument("test1", requires="test1")

        args = Arguments(test1)

        self.assertRaises(RuntimeError, lambda: list(args.requires("test1")))


class TestSetupOptions(unittest.TestCase):
    def test_set_defaults(self):
        session = Mock()
        plugin = Mock()
        parser = Mock()

        session.plugins = {"mock": plugin}
        plugin.arguments = Arguments(
            Argument("test1", default="default1"),
            Argument("test2", default="default2"),
            Argument("test3")
        )

        setup_plugin_args(session, parser)

        self.assertEqual(plugin.options.get("test1"), "default1")
        self.assertEqual(plugin.options.get("test2"), "default2")
        self.assertEqual(plugin.options.get("test3"), None)
