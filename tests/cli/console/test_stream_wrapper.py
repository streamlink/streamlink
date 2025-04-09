import sys
from io import BytesIO, TextIOWrapper

import pytest

from streamlink_cli.console.stream import ConsoleOutputStream


@pytest.fixture(autouse=True)
def _console_output_stream(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ConsoleOutputStream, "__new__", lambda *_, **__: object.__new__(ConsoleOutputStream))


def test_wrap_error():
    with pytest.raises(AttributeError):
        ConsoleOutputStream.wrap(sys, "version")


def test_wrap(capsys: pytest.CaptureFixture[str]):
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr

    streamwrapper = ConsoleOutputStream.wrap(sys, "stdout")
    assert streamwrapper is not orig_stdout
    assert sys.stdout is streamwrapper
    assert sys.stderr is orig_stderr
    assert sys.__stdout__ is not streamwrapper
    assert sys.__stderr__ is not streamwrapper

    streamwrapper.write("foo")
    streamwrapper.write("bar")
    streamwrapper.writelines(["abc", "def"])
    print("123", end="456")  # noqa: T201
    streamwrapper.flush()

    out, err = capsys.readouterr()
    assert out == "foobarabcdef123456"
    assert err == ""

    streamwrapper.restore()
    assert sys.stdout is orig_stdout
    assert sys.stderr is orig_stderr
    assert sys.__stdout__ is not streamwrapper
    assert sys.__stderr__ is not streamwrapper


def test_destruct():
    stream = TextIOWrapper(BytesIO(), encoding="utf-8")
    wrapper = ConsoleOutputStream(stream)
    assert wrapper.buffer is stream.buffer
    assert not wrapper.closed
    assert not wrapper.buffer.closed
    assert not stream.closed
    assert not stream.buffer.closed

    del wrapper
    assert not stream.closed
    assert not stream.buffer.closed
