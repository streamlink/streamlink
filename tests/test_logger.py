from __future__ import annotations

import logging
import os
import sys
import warnings
from collections.abc import Iterable
from datetime import timezone
from errno import EINVAL, EPIPE
from inspect import currentframe, getframeinfo
from io import BytesIO, TextIOWrapper
from pathlib import Path

import freezegun
import pytest

from streamlink import logger
from streamlink.exceptions import StreamlinkDeprecationWarning, StreamlinkWarning


def getvalue(output: TextIOWrapper, size: int = -1):
    output.seek(0)

    return output.read(size)


@pytest.fixture()
def output(request: pytest.FixtureRequest):
    params = getattr(request, "param", {})
    params.setdefault("encoding", "utf-8")
    output = TextIOWrapper(BytesIO(), **params)

    return output


@pytest.fixture()
def logfile(tmp_path: Path) -> str:
    return str(tmp_path / "log.txt")


@pytest.fixture()
def log(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, output: TextIOWrapper):
    params = getattr(request, "param", {})
    params.setdefault("format", "[{name}][{levelname}] {message}")
    params.setdefault("style", "{")

    if "logfile" in request.fixturenames:
        params["filename"] = request.getfixturevalue("logfile")

    stream: TextIOWrapper | None = output
    if not params.pop("stdout", True):
        stream = None
    if not params.pop("stderr", True):
        monkeypatch.setattr("sys.stderr", None)

    fakeroot = logging.getLogger("streamlink.test")

    monkeypatch.setattr("streamlink.logger.root", fakeroot)
    monkeypatch.setattr("streamlink.utils.times.LOCAL", timezone.utc)

    handler = logger.basicConfig(stream=stream, **params)
    assert isinstance(handler, logging.StreamHandler)

    yield fakeroot

    logger.capturewarnings(False)

    handler.close()
    fakeroot.removeHandler(handler)
    assert not fakeroot.handlers


class TestLogging:
    @pytest.fixture()
    def log_failure(
        self,
        request: pytest.FixtureRequest,
        monkeypatch: pytest.MonkeyPatch,
        log: logging.Logger,
        output: TextIOWrapper,
    ):
        params = getattr(request, "param", {})

        root = logging.getLogger("streamlink")
        monkeypatch.setattr("streamlink.logger.root", root)

        with pytest.raises(Exception) as cm:  # noqa: PT011
            logger.basicConfig(stream=output, **params)

        return cm.value

    @pytest.mark.parametrize(
        ("name", "level"),
        [
            ("none", logger.NONE),
            ("critical", logger.CRITICAL),
            ("error", logger.ERROR),
            ("warning", logger.WARNING),
            ("info", logger.INFO),
            ("debug", logger.DEBUG),
            ("trace", logger.TRACE),
            ("all", logger.ALL),
        ],
    )
    def test_level_names(self, name: str, level: int):
        assert logging.getLevelName(level) == name
        assert logging.getLevelName(name) == level
        assert logging.getLevelName(name.upper()) == level

    def test_levels_list(self):
        assert logger.levels == ["none", "critical", "error", "warning", "info", "debug", "trace", "all"]

    def test_default_level(self):
        assert logging.getLogger("streamlink").level == logger.WARNING

    def test_level(self, log: logging.Logger, output: TextIOWrapper):
        log.setLevel("info")
        log.debug("test")
        output.seek(0)
        assert output.tell() == 0

        log.setLevel("debug")
        log.debug("test")
        assert output.tell() != 0

    def test_level_none(self, log: logging.Logger, output: TextIOWrapper):
        log.setLevel("none")
        log.critical("test")
        log.error("test")
        log.warning("test")
        log.info("test")
        log.debug("test")
        log.trace("test")  # type: ignore[attr-defined]
        log.trace("paranoid")  # type: ignore[attr-defined]
        assert not getvalue(output)

    def test_output(self, log: logging.Logger, output: TextIOWrapper):
        log.setLevel("debug")
        log.debug("test")
        assert getvalue(output) == "[test][debug] test\n"

    @pytest.mark.parametrize(
        ("loglevel", "calllevel", "expected"),
        [
            (logger.DEBUG, logger.TRACE, ""),
            (logger.TRACE, logger.TRACE, "[test][trace] test\n"),
            (logger.TRACE, logger.DEBUG, "[test][debug] test\n"),
            (logger.TRACE, logger.ALL, ""),
            (logger.ALL, logger.ALL, "[test][all] test\n"),
            (logger.ALL, logger.TRACE, "[test][trace] test\n"),
        ],
    )
    def test_custom_output(self, log: logging.Logger, output: TextIOWrapper, loglevel: int, calllevel: int, expected: str):
        log.setLevel(loglevel)
        log.log(calllevel, "test")
        assert getvalue(output) == expected

    # https://github.com/streamlink/streamlink/issues/4862
    @pytest.mark.parametrize(
        ("level", "levelname"),
        [
            (logger.TRACE, "trace"),
            (logger.ALL, "all"),
        ],
    )
    def test_custom_module_name(self, caplog: pytest.LogCaptureFixture, log: logging.Logger, level: int, levelname: str):
        caplog.set_level(1)
        log = logging.getLogger(self.__class__.__module__)
        getattr(log, levelname)("foo")
        log.log(level, "bar")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("test_logger", levelname, "foo"),
            ("test_logger", levelname, "bar"),
        ]

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            (logger.DEBUG, ""),
            (logger.INFO, "[test][info] foo\n[test][info] bar\n"),
        ],
    )
    def test_iter(self, log: logger.StreamlinkLogger, output: TextIOWrapper, level: int, expected: str):
        def iterator():
            yield "foo"
            yield "bar"

        log.setLevel(logger.INFO)
        assert list(log.iter(level, iterator())) == ["foo", "bar"]
        assert getvalue(output) == expected

    @pytest.mark.parametrize(
        "log",
        [
            {"style": "%", "format": "[%(name)s][%(levelname)s] %(message)s"},
        ],
        indirect=True,
    )
    def test_style_percent(self, log: logging.Logger, output: TextIOWrapper):
        log.setLevel("info")
        log.info("test")
        assert getvalue(output) == "[test][info] test\n"

    @pytest.mark.parametrize("log_failure", [{"style": "invalid"}], indirect=True)
    def test_style_invalid(self, log_failure):
        assert type(log_failure) is ValueError
        assert str(log_failure) == "Style must be one of: %,{,$"

    @freezegun.freeze_time("2000-01-02T03:04:05.123456Z")
    @pytest.mark.parametrize(
        "log",
        [
            {"format": "[{asctime}][{name}][{levelname}] {message}"},
        ],
        indirect=True,
    )
    def test_datefmt_default(self, log: logging.Logger, output: TextIOWrapper):
        log.setLevel("info")
        log.info("test")
        assert getvalue(output) == "[03:04:05][test][info] test\n"

    @freezegun.freeze_time("2000-01-02T03:04:05.123456Z")
    @pytest.mark.parametrize(
        "log",
        [
            {"format": "[{asctime}][{name}][{levelname}] {message}", "datefmt": "%H:%M:%S.%f%z"},
        ],
        indirect=True,
    )
    def test_datefmt_custom(self, log: logging.Logger, output: TextIOWrapper):
        log.setLevel("info")
        log.info("test")
        assert getvalue(output) == "[03:04:05.123456+0000][test][info] test\n"

    @pytest.mark.parametrize(
        ("output", "expected"),
        [
            pytest.param(
                {"encoding": "utf-8"},
                "Bär: 🐻",
                id="utf-8",
            ),
            pytest.param(
                {"encoding": "ascii"},
                "B\\xe4r: \\U0001f43b",
                id="ascii",
            ),
            pytest.param(
                {"encoding": "iso-8859-1"},
                "Bär: \\U0001f43b",
                id="iso-8859-1",
            ),
            pytest.param(
                {"encoding": "shift_jis"},
                "B\\xe4r: \\U0001f43b",
                id="shift_jis",
            ),
        ],
        indirect=["output"],
    )
    def test_logstream_encoding(self, log: logging.Logger, output: TextIOWrapper, expected: str):
        log.setLevel("info")
        log.info("Bär: 🐻")
        assert getvalue(output) == f"[test][info] {expected}\n"

    def test_logstream_switch(self, log: logging.Logger, output: TextIOWrapper):
        output_ascii = TextIOWrapper(BytesIO(), encoding="ascii", errors="strict")
        log.setLevel("info")

        log.info("Bär: 🐻")
        assert getvalue(output) == "[test][info] Bär: 🐻\n"
        assert getvalue(output_ascii) == ""

        assert isinstance(log.handlers[0], logging.StreamHandler)
        # noinspection PyUnresolvedReferences
        log.handlers[0].setStream(output_ascii)

        log.info("Bär: 🐻")
        assert getvalue(output) == "[test][info] Bär: 🐻\n"
        assert getvalue(output_ascii) == "[test][info] B\\xe4r: \\U0001f43b\n"

    @pytest.mark.parametrize(
        "log",
        [pytest.param({"stdout": False}, id="no-stdout")],
        indirect=["log"],
    )
    def test_no_stdout(self, log: logging.Logger):
        assert log.handlers
        handler = log.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr

    @pytest.mark.parametrize(
        "log",
        [pytest.param({"stdout": False, "stderr": False}, id="no-stdout-no-stderr")],
        indirect=["log"],
    )
    def test_no_stdout_no_stderr(self, log: logging.Logger):
        assert log.handlers
        handler = log.handlers[0]
        assert isinstance(handler, logging.FileHandler)
        assert handler.stream.name.endswith(os.devnull)

    @pytest.mark.parametrize(
        "errno",
        [
            pytest.param(EPIPE, id="EPIPE", marks=pytest.mark.posix_only),
            pytest.param(EINVAL, id="EINVAL", marks=pytest.mark.windows_only),
        ],
    )
    def test_brokenpipeerror(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        log: logging.Logger,
        errno: int,
    ):
        def flush(*_, **__):
            exception = OSError()
            exception.errno = errno
            raise exception

        streamhandler = log.handlers[0]
        assert isinstance(streamhandler, logging.StreamHandler)
        monkeypatch.setattr(streamhandler.stream, "flush", flush)

        log.setLevel("info")
        log.info("foo")

        # logging.StreamHandler will write emit()/flush() errors to stderr via handleError()
        out, err = capsys.readouterr()
        assert not out
        assert not err

    def test_logfile(self, logfile: str, log: logging.Logger, output: TextIOWrapper):
        log.setLevel("info")
        log.info("Hello world, Γειά σου Κόσμε, こんにちは世界")  # noqa: RUF001
        log.handlers[0].flush()
        with open(logfile, "r", encoding="utf-8") as fh:
            assert fh.read() == "[test][info] Hello world, Γειά σου Κόσμε, こんにちは世界\n"  # noqa: RUF001


class TestCaptureWarnings:
    @staticmethod
    def _warn(messages: Iterable[tuple[str, type[Warning]]], filterwarnings=None):
        frame = currentframe()
        assert frame
        assert frame.f_back
        lineno = getframeinfo(frame.f_back).lineno

        with warnings.catch_warnings():
            warnings.filterwarnings(filterwarnings or "always")
            for message, warningclass in messages:
                warnings.warn(message, warningclass, stacklevel=2)

        return lineno

    def test_no_capture(self, log: logging.Logger, output: TextIOWrapper):
        with pytest.warns(UserWarning, match=r"^Test warning$"):
            self._warn([("Test warning", UserWarning)])
        assert getvalue(output) == ""

    @pytest.mark.parametrize("log", [{"capture_warnings": True}], indirect=["log"])
    @pytest.mark.parametrize(
        ("warning", "expected", "origin"),
        [
            (("Test warning", UserWarning), "[warnings][userwarning] Test warning\n", True),
            (("Test warning", DeprecationWarning), "[warnings][deprecationwarning] Test warning\n", True),
            (("Test warning", FutureWarning), "[warnings][futurewarning] Test warning\n", True),
            (("Test warning", StreamlinkWarning), "[warnings][streamlinkwarning] Test warning\n", False),
            (("Test warning", StreamlinkDeprecationWarning), "[warnings][streamlinkdeprecation] Test warning\n", False),
        ],
    )
    def test_capture(
        self,
        recwarn: pytest.WarningsRecorder,
        log: logging.Logger,
        output: TextIOWrapper,
        warning: tuple[str, type[Warning]],
        expected: str,
        origin: bool,
    ):
        lineno = self._warn([warning])
        expected += f"  {__file__}:{lineno}\n" if origin else ""
        assert recwarn.list == []
        assert getvalue(output) == expected

    @pytest.mark.parametrize("log", [{"capture_warnings": True}], indirect=["log"])
    def test_capture_logrecord(
        self,
        recwarn: pytest.WarningsRecorder,
        caplog: pytest.LogCaptureFixture,
        log: logging.Logger,
    ):
        lineno = self._warn([("Test warning", UserWarning)])
        path = Path(__file__)
        assert recwarn.list == []
        assert [(r.name, r.levelname, r.pathname, r.filename, r.module, r.lineno, r.message) for r in caplog.records] == [
            ("warnings", "userwarning", __file__, path.name, path.stem, lineno, f"Test warning\n  {__file__}:{lineno}"),
        ]

    @pytest.mark.parametrize("log", [{"capture_warnings": True}], indirect=["log"])
    def test_capture_consecutive(
        self,
        recwarn: pytest.WarningsRecorder,
        log: logging.Logger,
        output: TextIOWrapper,
    ):
        lineno = self._warn([("foo", DeprecationWarning), ("bar", FutureWarning)])
        assert recwarn.list == []
        assert getvalue(output) == (
            f"[warnings][deprecationwarning] foo\n  {__file__}:{lineno}\n"
            + f"[warnings][futurewarning] bar\n  {__file__}:{lineno}\n"
        )

    @pytest.mark.parametrize("log", [{"capture_warnings": True}], indirect=["log"])
    def test_capture_consecutive_once(
        self,
        recwarn: pytest.WarningsRecorder,
        log: logging.Logger,
        output: TextIOWrapper,
    ):
        lineno = self._warn([("foo", UserWarning), ("foo", UserWarning)], "once")
        assert recwarn.list == []
        assert getvalue(output) == f"[warnings][userwarning] foo\n  {__file__}:{lineno}\n"

    @pytest.mark.parametrize("log", [{"capture_warnings": True}], indirect=["log"])
    @pytest.mark.parametrize(
        "warning",
        [
            ("Test warning", UserWarning),
            ("Test warning", DeprecationWarning),
            ("Test warning", FutureWarning),
        ],
    )
    def test_ignored(
        self,
        recwarn: pytest.WarningsRecorder,
        log: logging.Logger,
        output: TextIOWrapper,
        warning: tuple[str, type[Warning]],
    ):
        self._warn([warning], filterwarnings="ignore")
        assert recwarn.list == []
        assert getvalue(output) == ""
