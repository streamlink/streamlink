import unittest

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

from tests.mock import Mock, patch
from streamlink_cli.console import ConsoleOutput


class _TestObj(object):
    def __json__(self):
        return {"test": 1}


class TestConsole(unittest.TestCase):
    def test_msg_format(self):
        output = StringIO()
        console = ConsoleOutput(output, Mock())
        console.msg("{0} - {1}", 1, 2)

        self.assertEqual("1 - 2\n", output.getvalue())

    def test_msg_format_kw(self):
        output = StringIO()
        console = ConsoleOutput(output, Mock())
        console.msg("{test} - {what}", test=1, what=2)

        self.assertEqual("1 - 2\n", output.getvalue())

    def test_msg_json_not_set(self):
        output = StringIO()
        console = ConsoleOutput(output, Mock())
        self.assertEqual(None, console.msg_json({"test": 1}))
        self.assertEqual("", output.getvalue())

    def test_msg_json(self):
        output = StringIO()
        console = ConsoleOutput(output, Mock(), json=True)
        console.msg_json({"test": 1})
        self.assertEqual('''{\n  "test": 1\n}\n''', output.getvalue())

    def test_msg_json_object(self):
        output = StringIO()
        test_obj = _TestObj()
        console = ConsoleOutput(output, Mock(), json=True)
        console.msg_json(test_obj)
        self.assertEqual('''{\n  "test": 1\n}\n''', output.getvalue())

    @patch('streamlink_cli.console.sys.exit')
    def test_msg_json_error(self, mock_exit):
        output = StringIO()
        console = ConsoleOutput(output, Mock(), json=True)
        console.msg_json({"error": "bad"})
        self.assertEqual('''{\n  "error": "bad"\n}\n''', output.getvalue())
        mock_exit.assert_called_with(1)

    @patch('streamlink_cli.console.sys.exit')
    def test_exit(self, mock_exit):
        output = StringIO()
        console = ConsoleOutput(output, Mock())
        console.exit("error")
        self.assertEqual("error: error\n", output.getvalue())
        mock_exit.assert_called_with(1)

    @patch('streamlink_cli.console.sys.exit')
    def test_exit_json(self, mock_exit):
        output = StringIO()
        console = ConsoleOutput(output, Mock(), json=True)
        console.exit("error")
        self.assertEqual('''{\n  "error": "error"\n}\n''', output.getvalue())
        mock_exit.assert_called_with(1)

    def test_set_level(self):
        session = Mock()
        console = ConsoleOutput(Mock(), session)
        console.set_level("debug")
        session.set_loglevel.assert_called_with("debug")

    @patch('streamlink_cli.console.sys.stderr')
    @patch('streamlink_cli.console.input')
    @patch('streamlink_cli.console.sys.stdin.isatty')
    def test_ask(self, isatty, input, stderr):
        input.return_value = "hello"
        isatty.return_value = True
        self.assertEqual("hello", ConsoleOutput.ask("test: "))
        stderr.write.assert_called_with("test: ")

    @patch('streamlink_cli.console.sys.stderr')
    @patch('streamlink_cli.console.input')
    @patch('streamlink_cli.console.sys.stdin.isatty')
    def test_ask_no_tty(self, isatty, input, stderr):
        isatty.return_value = False
        self.assertEqual("", ConsoleOutput.ask("test: "))
        input.assert_not_called()
        stderr.write.assert_not_called()

    @patch('streamlink_cli.console.sys.stderr')
    @patch('streamlink_cli.console.input')
    @patch('streamlink_cli.console.sys.stdin.isatty')
    def test_ask_input_exception(self, isatty, input, stderr):
        isatty.return_value = True
        input.side_effect = ValueError
        self.assertEqual("", ConsoleOutput.ask("test: "))
        stderr.write.assert_called_with("test: ")

    @patch('streamlink_cli.console.getpass')
    @patch('streamlink_cli.console.sys.stdin.isatty')
    def test_askpass(self, isatty, getpass):
        isatty.return_value = True
        getpass.return_value = "hello"
        self.assertEqual("hello", ConsoleOutput.askpass("test: "))

    @patch('streamlink_cli.console.sys.stdin.isatty')
    def test_askpass_no_tty(self, isatty):
        isatty.return_value = False
        self.assertEqual("", ConsoleOutput.askpass("test: "))
