import sys
if sys.version_info[0:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from streamlink.options import Options, Arguments, Argument


class TestOptions(unittest.TestCase):
    def setUp(self):
        self.options = Options({
            "a_default": "default"
        })

    def test_options(self):
        self.assertEqual(self.options.get("a_default"), "default")
        self.assertEqual(self.options.get("non_existing"), None)

        self.options.set("a_option", "option")
        self.assertEqual(self.options.get("a_option"), "option")


class TestArgument(unittest.TestCase):
    def test_name(self):
        self.assertEqual(Argument("test").argument_name("plugin"), "--plugin-test")
        self.assertEqual(Argument("test").option_name("plugin"), "plugin_test")

    def test_name_override(self):
        self.assertEqual(Argument("test", argument_name="override-name").argument_name("plugin"), "--override-name")
        self.assertEqual(Argument("test", argument_name="override-name").option_name("plugin"), "override_name")


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
        test1 = Argument("test1", requires="test2")
        test2 = Argument("test2", requires="test3")
        test3 = Argument("test3", requires="test1")

        args = Arguments(test1, test2, test3)

        self.assertRaises(RuntimeError, lambda: list(args.requires("test1")))

    def test_requires_cycle_self(self):
        test1 = Argument("test1", requires="test1")

        args = Arguments(test1)

        self.assertRaises(RuntimeError, lambda: list(args.requires("test1")))


if __name__ == "__main__":
    unittest.main()
