from io import BytesIO, TextIOWrapper
from textwrap import dedent
from unittest.mock import Mock

import pytest

from streamlink_cli.console import ConsoleOutput


def getvalue(output: TextIOWrapper, size: int = -1):
    output.seek(0)

    return output.read(size)


class TestConsoleOutput:
    @pytest.fixture(autouse=True)
    def _isatty(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        isatty = not request.function.__name__.endswith("_no_tty")
        monkeypatch.setattr("sys.stdin.isatty", lambda: isatty)

    @pytest.fixture()
    def output(self, request: pytest.FixtureRequest):
        params = getattr(request, "param", {})
        params.setdefault("encoding", "utf-8")
        params.setdefault("errors", "backslashreplace")
        output = TextIOWrapper(BytesIO(), **params)

        return output

    @pytest.mark.parametrize(
        ("output", "expected"),
        [
            pytest.param(
                {"encoding": "utf-8"},
                "Bär: 🐻",
                id="utf-8 encoding",
            ),
            pytest.param(
                {"encoding": "ascii"},
                "B\\xe4r: \\U0001f43b",  # Unicode character: "Bear Face" (U+1F43B)
                id="ascii encoding",
            ),
        ],
        indirect=["output"],
    )
    def test_msg(self, output: TextIOWrapper, expected: str):
        console = ConsoleOutput(output)
        console.msg("Bär: 🐻")
        console.msg_json({"test": 1})
        assert getvalue(output) == f"{expected}\n"

    @pytest.mark.parametrize(
        ("output", "expected"),
        [
            pytest.param(
                {"encoding": "utf-8"},
                "Bär: 🐻",
                id="utf-8 encoding",
            ),
            pytest.param(
                {"encoding": "ascii"},
                "B\\u00e4r: \\ud83d\\udc3b",  # Unicode character: "Bear Face" (U+1F43B) - UTF-16: 0xD83D 0xDC3B
                id="ascii encoding",
            ),
        ],
        indirect=["output"],
    )
    def test_msg_json(self, output: TextIOWrapper, expected: str):
        console = ConsoleOutput(output, json=True)
        console.msg("foo")
        console.msg_json({"test": "Bär: 🐻"})
        assert getvalue(output) == f'{{\n  "test": "{expected}"\n}}\n'

    def test_msg_json_object(self, output: TextIOWrapper):
        console = ConsoleOutput(output, json=True)
        console.msg_json(Mock(__json__=lambda: {"test": "Hello world, Γειά σου Κόσμε, こんにちは世界"}))  # noqa: RUF001
        assert getvalue(output) == '{\n  "test": "Hello world, Γειά σου Κόσμε, こんにちは世界"\n}\n'  # noqa: RUF001

    def test_msg_json_list(self, output: TextIOWrapper):
        console = ConsoleOutput(output, json=True)
        test_list = ["Hello world, Γειά σου Κόσμε, こんにちは世界", '"🐻"']  # noqa: RUF001
        console.msg_json(test_list)
        assert getvalue(output) == '[\n  "Hello world, Γειά σου Κόσμε, こんにちは世界",\n  "\\"🐻\\""\n]\n'  # noqa: RUF001

    def test_msg_json_merge_object(self, output: TextIOWrapper):
        console = ConsoleOutput(output, json=True)
        test_obj1 = {"test": 1, "foo": "foo"}
        test_obj2 = Mock(__json__=Mock(return_value={"test": 2}))
        console.msg_json(test_obj1, test_obj2, ["qux"], foo="bar", baz="qux")
        assert (
            getvalue(output)
            == dedent("""
                {
                  "test": 2,
                  "foo": "bar",
                  "baz": "qux"
                }
            """).lstrip()
        )
        assert list(test_obj1.items()) == [("test", 1), ("foo", "foo")]

    def test_msg_json_merge_list(self, output: TextIOWrapper):
        console = ConsoleOutput(output, json=True)
        test_list1 = ["foo", "bar"]
        test_list2 = Mock(__json__=Mock(return_value={"foo": "bar"}))
        console.msg_json(test_list1, ["baz"], test_list2, {"foo": "bar"}, foo="bar", baz="qux")
        assert (
            getvalue(output)
            == dedent("""
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
        )
        assert test_list1 == ["foo", "bar"]

    def test_ask(self, monkeypatch: pytest.MonkeyPatch, output: TextIOWrapper):
        monkeypatch.setattr("builtins.input", Mock(return_value="hello"))

        console = ConsoleOutput(output)
        assert console.ask("test: ") == "hello"
        assert getvalue(output) == "test: "

    def test_ask_no_tty(self, monkeypatch: pytest.MonkeyPatch, output: TextIOWrapper):
        mock_input = Mock()
        monkeypatch.setattr("builtins.input", mock_input)

        console = ConsoleOutput(output)
        assert console.ask("test: ") is None
        assert getvalue(output) == ""
        assert mock_input.call_args_list == []

    def test_ask_no_stdin(self, monkeypatch: pytest.MonkeyPatch, output: TextIOWrapper):
        monkeypatch.setattr("sys.stdin", None)

        console = ConsoleOutput(output)
        assert console.ask("test: ") is None
        assert getvalue(output) == ""

    def test_ask_input_exception(self, monkeypatch: pytest.MonkeyPatch, output: TextIOWrapper):
        monkeypatch.setattr("builtins.input", Mock(side_effect=ValueError))

        console = ConsoleOutput(output)
        assert console.ask("test: ") is None
        assert getvalue(output) == "test: "

    def test_askpass(self, monkeypatch: pytest.MonkeyPatch, output: TextIOWrapper):
        def getpass(prompt, stream):
            stream.write(prompt)
            return "hello"

        monkeypatch.setattr("streamlink_cli.console.getpass", getpass)

        console = ConsoleOutput(output)
        assert console.askpass("test: ") == "hello"
        assert getvalue(output) == "test: "

    def test_askpass_no_tty(self, output: TextIOWrapper):
        console = ConsoleOutput(output)
        assert console.askpass("test: ") is None
        assert getvalue(output) == ""

    def test_askpass_no_stdin(self, monkeypatch: pytest.MonkeyPatch, output: TextIOWrapper):
        monkeypatch.setattr("sys.stdin", None)

        console = ConsoleOutput(output)
        assert console.askpass("test: ") is None
        assert getvalue(output) == ""
