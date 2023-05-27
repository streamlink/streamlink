from io import StringIO
from textwrap import dedent
from unittest.mock import Mock

import pytest

from streamlink_cli.console import ConsoleOutput


class TestConsoleOutput:
    @pytest.fixture(autouse=True)
    def _isatty(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        isatty = not request.function.__name__.endswith("_no_tty")
        monkeypatch.setattr("sys.stdin.isatty", lambda: isatty)

    def test_msg(self):
        output = StringIO()
        console = ConsoleOutput(output)
        console.msg("foo")
        console.msg_json({"test": 1})
        assert output.getvalue() == "foo\n"

    def test_msg_json(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        console.msg("foo")
        console.msg_json({"test": 1})
        assert output.getvalue() == '{\n  "test": 1\n}\n'

    def test_msg_json_object(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        console.msg_json(Mock(__json__=Mock(return_value={"test": 1})))
        assert output.getvalue() == '{\n  "test": 1\n}\n'

    def test_msg_json_list(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        test_list = ["foo", "bar"]
        console.msg_json(test_list)
        assert output.getvalue() == '[\n  "foo",\n  "bar"\n]\n'

    def test_msg_json_merge_object(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        test_obj1 = {"test": 1, "foo": "foo"}
        test_obj2 = Mock(__json__=Mock(return_value={"test": 2}))
        console.msg_json(test_obj1, test_obj2, ["qux"], foo="bar", baz="qux")
        assert output.getvalue() == dedent("""
            {
              "test": 2,
              "foo": "bar",
              "baz": "qux"
            }
        """).lstrip()
        assert list(test_obj1.items()) == [("test", 1), ("foo", "foo")]

    def test_msg_json_merge_list(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        test_list1 = ["foo", "bar"]
        test_list2 = Mock(__json__=Mock(return_value={"foo": "bar"}))
        console.msg_json(test_list1, ["baz"], test_list2, {"foo": "bar"}, foo="bar", baz="qux")
        assert output.getvalue() == dedent("""
            [
              "foo",
              "bar",
              "baz",
              {
                "foo": "bar"
              },
              {
                "foo": "bar"
              },
              {
                "foo": "bar",
                "baz": "qux"
              }
            ]
        """).lstrip()
        assert test_list1 == ["foo", "bar"]

    def test_msg_json_error(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        with pytest.raises(SystemExit) as cm:
            console.msg_json({"error": "bad"})
        assert cm.value.code == 1
        assert output.getvalue() == '{\n  "error": "bad"\n}\n'

    def test_exit(self):
        output = StringIO()
        console = ConsoleOutput(output)
        with pytest.raises(SystemExit) as cm:
            console.exit("error")
        assert cm.value.code == 1
        assert output.getvalue() == "error: error\n"

    def test_exit_json(self):
        output = StringIO()
        console = ConsoleOutput(output, json=True)
        with pytest.raises(SystemExit) as cm:
            console.exit("error")
        assert cm.value.code == 1
        assert output.getvalue() == '{\n  "error": "error"\n}\n'

    def test_ask(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("builtins.input", Mock(return_value="hello"))

        output = StringIO()
        console = ConsoleOutput(output)
        assert console.ask("test: ") == "hello"
        assert output.getvalue() == "test: "

    def test_ask_no_tty(self, monkeypatch: pytest.MonkeyPatch):
        mock_input = Mock()
        monkeypatch.setattr("builtins.input", mock_input)

        output = StringIO()
        console = ConsoleOutput(output)
        assert console.ask("test: ") is None
        assert output.getvalue() == ""
        assert mock_input.call_args_list == []

    def test_ask_input_exception(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("builtins.input", Mock(side_effect=ValueError))

        output = StringIO()
        console = ConsoleOutput(output)
        assert console.ask("test: ") is None
        assert output.getvalue() == "test: "

    def test_askpass(self, monkeypatch: pytest.MonkeyPatch):
        def getpass(prompt, stream):
            stream.write(prompt)
            return "hello"

        monkeypatch.setattr("streamlink_cli.console.getpass", getpass)

        output = StringIO()
        console = ConsoleOutput(output)
        assert console.askpass("test: ") == "hello"
        assert output.getvalue() == "test: "

    def test_askpass_no_tty(self):
        output = StringIO()
        console = ConsoleOutput(output)
        assert console.askpass("test: ") is None
