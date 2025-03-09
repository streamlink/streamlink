from __future__ import annotations

from io import BytesIO, TextIOWrapper
from textwrap import dedent
from unittest.mock import Mock

import pytest

from streamlink_cli.console import ConsoleOutput, ConsoleUserInputRequester


def getvalue(output: TextIOWrapper | None, size: int = -1):
    if output is None:
        return None

    output.seek(0)

    return output.read(size)


def build_textiowrapper(params):
    if not params.pop("exists", True):
        return None

    isatty = params.pop("isatty", True)
    params.setdefault("encoding", "utf-8")
    params.setdefault("errors", "backslashreplace")
    stream = TextIOWrapper(BytesIO(), **params)
    stream.isatty = lambda: isatty

    return stream


@pytest.fixture(autouse=True)
def stdin(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    params = getattr(request, "param", {})
    stdin = build_textiowrapper(params)
    monkeypatch.setattr("sys.stdin", stdin)

    return stdin


@pytest.fixture()
def console_output(request: pytest.FixtureRequest):
    return build_textiowrapper(getattr(request, "param", {}))


@pytest.fixture()
def file_output(request: pytest.FixtureRequest):
    return build_textiowrapper(getattr(request, "param", {}))


@pytest.mark.parametrize(
    ("console_output", "file_output", "has_file_output", "expected_console_output", "expected_file_output"),
    [
        pytest.param(
            {"exists": False},
            {"exists": False},
            False,
            None,
            None,
            id="no-output-streams",
        ),
        pytest.param(
            {"isatty": True},
            {"exists": False},
            False,
            'foo\n{\n  "foo": "bar"\n}\n',
            None,
            id="console-output-is-a-tty",
        ),
        pytest.param(
            {"isatty": False},
            {"exists": False},
            False,
            'foo\n{\n  "foo": "bar"\n}\n',
            None,
            id="console-output-is-not-a-tty",
        ),
        pytest.param(
            {},
            {"isatty": True},
            False,
            'foo\n{\n  "foo": "bar"\n}\n',
            "",
            id="file-output-is-a-tty",
        ),
        pytest.param(
            {},
            {"isatty": False},
            True,
            'foo\n{\n  "foo": "bar"\n}\n',
            'foo\n{\n  "foo": "bar"\n}\n',
            id="file-output-is-not-a-tty",
        ),
    ],
    indirect=["console_output", "file_output"],
)
def test_streams(
    console_output: TextIOWrapper | None,
    file_output: TextIOWrapper | None,
    has_file_output: bool,
    expected_console_output: str,
    expected_file_output: str,
):
    console = ConsoleOutput()
    assert console.console_output is None
    assert console.file_output is None

    console.console_output = console_output
    console.file_output = file_output
    assert console.console_output is console_output
    assert console.file_output is (file_output if has_file_output else None)

    console.msg("foo")
    console.json = True
    console.msg_json(foo="bar")
    assert getvalue(console_output) == expected_console_output
    assert getvalue(file_output) == expected_file_output


@pytest.mark.parametrize("method_raises", ["write", "flush"])
def test_broken_stream(monkeypatch: pytest.MonkeyPatch, console_output: TextIOWrapper, method_raises: str):
    monkeypatch.setattr(console_output, method_raises, Mock(side_effect=BrokenPipeError))
    console = ConsoleOutput(console_output=console_output)
    console.msg("foo")
    console.msg("bar")


class TestMessages:
    @pytest.mark.parametrize(
        ("console_output", "expected_console_output", "expected_file_output"),
        [
            pytest.param(
                {"encoding": "utf-8"},
                "Bär: 🐻\n",
                "Bär: 🐻\n",
                id="utf-8 encoding",
            ),
            pytest.param(
                {"encoding": "ascii"},
                "B\\xe4r: \\U0001f43b\n",  # Unicode character: "Bear Face" (U+1F43B)
                "Bär: 🐻\n",
                id="ascii encoding",
            ),
        ],
        indirect=["console_output"],
    )
    def test_no_json(
        self,
        console_output: TextIOWrapper,
        file_output: TextIOWrapper,
        expected_console_output: str,
        expected_file_output: str,
    ):
        console = ConsoleOutput(console_output=console_output, file_output=file_output)
        console.msg("Bär: 🐻")
        console.msg_json({"test": 1})
        assert getvalue(console_output) == expected_console_output
        assert getvalue(file_output) == expected_file_output

    @pytest.mark.parametrize(
        ("console_output", "expected_console_output", "expected_file_output"),
        [
            pytest.param(
                {"encoding": "utf-8"},
                '{\n  "test": "Bär: 🐻"\n}\n',
                '{\n  "test": "Bär: 🐻"\n}\n',
                id="utf-8 encoding",
            ),
            pytest.param(
                {"encoding": "ascii"},
                '{\n  "test": "B\\u00e4r: \\ud83d\\udc3b"\n}\n',  # Unicode character: "Bear Face" (U+1F43B)
                '{\n  "test": "Bär: 🐻"\n}\n',
                id="ascii encoding",
            ),
        ],
        indirect=["console_output"],
    )
    def test_json(
        self,
        console_output: TextIOWrapper,
        file_output: TextIOWrapper,
        expected_console_output: str,
        expected_file_output: str,
    ):
        console = ConsoleOutput(console_output=console_output, file_output=file_output, json=True)
        console.msg("foo")
        console.msg_json({"test": "Bär: 🐻"})
        assert getvalue(console_output) == expected_console_output
        assert getvalue(file_output) == expected_file_output

    def test_msg_json_object(self, console_output: TextIOWrapper):
        console = ConsoleOutput(console_output=console_output, json=True)
        console.msg_json(Mock(__json__=lambda: {"test": "Hello world, Γειά σου Κόσμε, こんにちは世界"}))  # noqa: RUF001
        assert getvalue(console_output) == '{\n  "test": "Hello world, Γειά σου Κόσμε, こんにちは世界"\n}\n'  # noqa: RUF001

    def test_msg_json_list(self, console_output: TextIOWrapper):
        console = ConsoleOutput(console_output=console_output, json=True)
        test_list = ["Hello world, Γειά σου Κόσμε, こんにちは世界", '"🐻"']  # noqa: RUF001
        console.msg_json(test_list)
        assert getvalue(console_output) == '[\n  "Hello world, Γειά σου Κόσμε, こんにちは世界",\n  "\\"🐻\\""\n]\n'  # noqa: RUF001

    def test_msg_json_merge_object(self, console_output: TextIOWrapper):
        console = ConsoleOutput(console_output=console_output, json=True)
        test_obj1 = {"test": 1, "foo": "foo"}
        test_obj2 = Mock(__json__=Mock(return_value={"test": 2}))
        console.msg_json(test_obj1, test_obj2, ["qux"], foo="bar", baz="qux")
        assert (
            getvalue(console_output)
            == dedent("""
                {
                  "test": 2,
                  "foo": "bar",
                  "baz": "qux"
                }
            """).lstrip()
        )
        assert list(test_obj1.items()) == [("test", 1), ("foo", "foo")]

    def test_msg_json_merge_list(self, console_output: TextIOWrapper):
        console = ConsoleOutput(console_output=console_output, json=True)
        test_list1 = ["foo", "bar"]
        test_list2 = Mock(__json__=Mock(return_value={"foo": "bar"}))
        console.msg_json(test_list1, ["baz"], test_list2, {"foo": "bar"}, foo="bar", baz="qux")
        assert (
            getvalue(console_output)
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


class TestPrompts:
    def test_prompt_exception(self, console_output: TextIOWrapper):
        console = ConsoleOutput(console_output=console_output)
        with pytest.raises(BaseException) as exc_info:  # noqa: PT011
            with console._prompt():
                raise EOFError
        assert isinstance(exc_info.value, OSError)
        assert isinstance(exc_info.value.__cause__, EOFError)

    @pytest.mark.parametrize("exception", [OSError, KeyboardInterrupt])
    def test_prompt_exception_passthrough(self, console_output: TextIOWrapper, exception: type[Exception]):
        console = ConsoleOutput(console_output=console_output)
        with pytest.raises(BaseException) as exc_info:  # noqa: PT011
            with console._prompt():
                raise exception
        assert isinstance(exc_info.value, exception)

    def test_ask(self, monkeypatch: pytest.MonkeyPatch, console_output: TextIOWrapper, file_output: TextIOWrapper):
        monkeypatch.setattr("builtins.input", Mock(return_value="hello"))

        console = ConsoleOutput(console_output=console_output, file_output=file_output)
        user_input = ConsoleUserInputRequester(console)
        assert user_input.ask("test") == "hello"
        assert getvalue(console_output) == "test: "
        assert getvalue(file_output) == ""

    @pytest.mark.parametrize(
        ("stdin", "console_output", "expected"),
        [
            pytest.param({"exists": False}, {}, "^No input TTY available$", id="no-stdin"),
            pytest.param({"isatty": False}, {}, "^No input TTY available$", id="stdin-no-tty"),
            pytest.param({}, {"exists": False}, "^No output TTY available$", id="no-output"),
            pytest.param({}, {"isatty": False}, "^No output TTY available$", id="output-no-tty"),
        ],
        indirect=["stdin", "console_output"],
    )
    def test_ask_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stdin: TextIOWrapper,
        console_output: TextIOWrapper,
        expected: str,
    ):
        mock_input = Mock()
        monkeypatch.setattr("builtins.input", mock_input)

        console = ConsoleOutput(console_output=console_output)
        user_input = ConsoleUserInputRequester(console)
        with pytest.raises(OSError, match=expected):
            user_input.ask("test")
        assert mock_input.call_args_list == []

    def test_ask_password(self, monkeypatch: pytest.MonkeyPatch, console_output: TextIOWrapper):
        def getpass(prompt, stream):
            stream.write(prompt)
            return "hello"

        monkeypatch.setattr("streamlink_cli.console.getpass", getpass)

        console = ConsoleOutput(console_output=console_output)
        user_input = ConsoleUserInputRequester(console)
        assert user_input.ask_password("test") == "hello"
        assert getvalue(console_output) == "test: "

    @pytest.mark.parametrize(
        ("stdin", "console_output", "expected"),
        [
            pytest.param({"exists": False}, {}, "^No input TTY available$", id="no-stdin"),
            pytest.param({"isatty": False}, {}, "^No input TTY available$", id="stdin-no-tty"),
            pytest.param({}, {"exists": False}, "^No output TTY available$", id="no-output"),
            pytest.param({}, {"isatty": False}, "^No output TTY available$", id="output-no-tty"),
        ],
        indirect=["stdin", "console_output"],
    )
    def test_ask_password_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stdin: TextIOWrapper,
        console_output: TextIOWrapper,
        expected: str,
    ):
        mock_getpass = Mock()
        monkeypatch.setattr("streamlink_cli.console.getpass", mock_getpass)

        console = ConsoleOutput(console_output=console_output)
        user_input = ConsoleUserInputRequester(console)
        with pytest.raises(OSError, match=expected):
            user_input.ask_password("test")
        assert mock_getpass.call_args_list == []
