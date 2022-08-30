import unittest
from io import StringIO
from unittest.mock import Mock, patch

from streamlink_cli.console import ConsoleOutput


class TestConsoleOutput(unittest.TestCase):
    def test_msg(self):
        output = StringIO()
        console = ConsoleOutput(output)
        console.msg("foo")
        console.msg_json({"test": 1})
        self.assertEqual("foo\n", output.getvalue())

    def test_msg_json(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        console.msg("foo")
        console.msg_json({"test": 1})
        self.assertEqual('{\n  "test": 1\n}\n', output.getvalue())

    def test_msg_json_object(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        console.msg_json(Mock(__json__=Mock(return_value={"test": 1})))
        self.assertEqual('{\n  "test": 1\n}\n', output.getvalue())

    def test_msg_json_list(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        test_list = ["foo", "bar"]
        console.msg_json(test_list)
        self.assertEqual('[\n  "foo",\n  "bar"\n]\n', output.getvalue())

    def test_msg_json_merge_object(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        test_obj1 = {"test": 1, "foo": "foo"}
        test_obj2 = Mock(__json__=Mock(return_value={"test": 2}))
        console.msg_json(test_obj1, test_obj2, ["qux"], foo="bar", baz="qux")
        self.assertEqual(
            '{\n'
            '  "test": 2,\n'
            '  "foo": "bar",\n'
            '  "baz": "qux"\n'
            '}\n',
            output.getvalue()
        )
        self.assertEqual([("test", 1), ("foo", "foo")], list(test_obj1.items()))

    def test_msg_json_merge_list(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        test_list1 = ["foo", "bar"]
        test_list2 = Mock(__json__=Mock(return_value={"foo": "bar"}))
        console.msg_json(test_list1, ["baz"], test_list2, {"foo": "bar"}, foo="bar", baz="qux")
        self.assertEqual(
            '[\n'
            '  "foo",\n'
            '  "bar",\n'
            '  "baz",\n'
            '  {\n    "foo": "bar"\n  },\n'
            '  {\n    "foo": "bar"\n  },\n'
            '  {\n    "foo": "bar",\n    "baz": "qux"\n  }\n'
            ']\n',
            output.getvalue()
        )
        self.assertEqual(["foo", "bar"], test_list1)

    @patch("streamlink_cli.console.sys.exit")
    def test_msg_json_error(self, mock_exit):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        console.msg_json({"error": "bad"})
        self.assertEqual('{\n  "error": "bad"\n}\n', output.getvalue())
        mock_exit.assert_called_with(1)

    @patch("streamlink_cli.console.sys.exit")
    def test_exit(self, mock_exit: Mock):
        output = StringIO()
        console = ConsoleOutput(output)
        console.exit("error")
        self.assertEqual("error: error\n", output.getvalue())
        mock_exit.assert_called_with(1)

    @patch("streamlink_cli.console.sys.exit")
    def test_exit_json(self, mock_exit: Mock):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        console.exit("error")
        self.assertEqual('{\n  "error": "error"\n}\n', output.getvalue())
        mock_exit.assert_called_with(1)

    @patch("streamlink_cli.console.input", Mock(return_value="hello"))
    @patch("streamlink_cli.console.sys.stdin.isatty", Mock(return_value=True))
    def test_ask(self):
        output = StringIO()
        console = ConsoleOutput(output)
        self.assertEqual("hello", console.ask("test: "))
        self.assertEqual("test: ", output.getvalue())

    @patch("streamlink_cli.console.input")
    @patch("streamlink_cli.console.sys.stdin.isatty", Mock(return_value=False))
    def test_ask_no_tty(self, mock_input: Mock):
        output = StringIO()
        console = ConsoleOutput(output)
        self.assertIsNone(console.ask("test: "))
        self.assertEqual("", output.getvalue())
        mock_input.assert_not_called()

    @patch("streamlink_cli.console.input", Mock(side_effect=ValueError))
    @patch("streamlink_cli.console.sys.stdin.isatty", Mock(return_value=True))
    def test_ask_input_exception(self):
        output = StringIO()
        console = ConsoleOutput(output)
        self.assertIsNone(console.ask("test: "))
        self.assertEqual("test: ", output.getvalue())

    @patch("streamlink_cli.console.getpass")
    @patch("streamlink_cli.console.sys.stdin.isatty", Mock(return_value=True))
    def test_askpass(self, mock_getpass: Mock):
        def getpass(prompt, stream):
            stream.write(prompt)
            return "hello"

        output = StringIO()
        console = ConsoleOutput(output)
        mock_getpass.side_effect = getpass
        self.assertEqual("hello", console.askpass("test: "))
        self.assertEqual("test: ", output.getvalue())

    @patch("streamlink_cli.console.sys.stdin.isatty", Mock(return_value=False))
    def test_askpass_no_tty(self):
        output = StringIO()
        console = ConsoleOutput(output)
        self.assertIsNone(console.askpass("test: "))
