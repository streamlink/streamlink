import logging
import warnings
from datetime import timezone
from inspect import currentframe, getframeinfo
from io import StringIO
from pathlib import Path
from typing import Iterable, Tuple, Type
from unittest.mock import patch

import freezegun
import pytest

from streamlink import logger
from streamlink.exceptions import StreamlinkDeprecationWarning, StreamlinkWarning


@pytest.fixture()
def output():
    return StringIO()


@pytest.fixture()
def log(request, output: StringIO):
    params = getattr(request, "param", {})
    params.setdefault("format", "[{name}][{levelname}] {message}")
    params.setdefault("style", "{")
    fakeroot = logging.getLogger("streamlink.test")
    with patch("streamlink.logger.root", fakeroot), \
         patch("streamlink.utils.times.LOCAL", timezone.utc):
        logger.basicConfig(stream=output, **params)
        yield fakeroot
        logger.capturewarnings(False)


class TestLogging:
    @pytest.fixture()
    def log_failure(self, request, log: logging.Logger, output: StringIO):
        params = getattr(request, "param", {})
        root = logging.getLogger("streamlink")
        with patch("streamlink.logger.root", root):
            with pytest.raises(Exception) as cm:  # noqa: PT011
                logger.basicConfig(stream=output, **params)
        return cm.value

    @pytest.mark.parametrize(("name", "level"), [
        ("none", logger.NONE),
        ("critical", logger.CRITICAL),
        ("error", logger.ERROR),
        ("warning", logger.WARNING),
        ("info", logger.INFO),
        ("debug", logger.DEBUG),
        ("trace", logger.TRACE),
        ("all", logger.ALL),
    ])
    def test_level_names(self, name: str, level: int):
        assert logging.getLevelName(level) == name
        assert logging.getLevelName(name) == level
        assert logging.getLevelName(name.upper()) == level

    def test_levels_list(self):
        assert logger.levels == ["none", "critical", "error", "warning", "info", "debug", "trace", "all"]

    def test_default_level(self):
        assert logging.getLogger("streamlink").level == logger.WARNING

    def test_level(self, log: logging.Logger, output: StringIO):
        log.setLevel("info")
        log.debug("test")
        output.seek(0)
        assert output.tell() == 0

        log.setLevel("debug")
        log.debug("test")
        assert output.tell() != 0

    def test_level_none(self, log: logging.Logger, output: StringIO):
        log.setLevel("none")
        log.critical("test")
        log.error("test")
        log.warning("test")
        log.info("test")
        log.debug("test")
        log.trace("test")  # type: ignore[attr-defined]
        log.trace("paranoid")  # type: ignore[attr-defined]
        assert not output.getvalue()

    def test_output(self, log: logging.Logger, output: StringIO):
        log.setLevel("debug")
        log.debug("test")
        assert output.getvalue() == "[test][debug] test\n"

    @pytest.mark.parametrize(("loglevel", "calllevel", "expected"), [
        (logger.DEBUG, logger.TRACE, ""),
        (logger.TRACE, logger.TRACE, "[test][trace] test\n"),
        (logger.TRACE, logger.DEBUG, "[test][debug] test\n"),
        (logger.TRACE, logger.ALL, ""),
        (logger.ALL, logger.ALL, "[test][all] test\n"),
        (logger.ALL, logger.TRACE, "[test][trace] test\n"),
    ])
    def test_custom_output(self, log: logging.Logger, output: StringIO, loglevel: int, calllevel: int, expected: str):
        log.setLevel(loglevel)
        log.log(calllevel, "test")
        assert output.getvalue() == expected

    # https://github.com/streamlink/streamlink/issues/4862
    @pytest.mark.parametrize(("level", "levelname"), [
        (logger.TRACE, "trace"),
        (logger.ALL, "all"),
    ])
    def test_custom_module_name(self, caplog: pytest.LogCaptureFixture, log: logging.Logger, level: int, levelname: str):
        caplog.set_level(1)
        log = logging.getLogger(self.__class__.__module__)
        getattr(log, levelname)("foo")
        log.log(level, "bar")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("test_logger", levelname, "foo"),
            ("test_logger", levelname, "bar"),
        ]

    @pytest.mark.parametrize(("level", "expected"), [
        (logger.DEBUG, ""),
        (logger.INFO, "[test][info] foo\n[test][info] bar\n"),
    ])
    def test_iter(self, log: logger.StreamlinkLogger, output: StringIO, level: int, expected: str):
        def iterator():
            yield "foo"
            yield "bar"

        log.setLevel(logger.INFO)
        assert list(log.iter(level, iterator())) == ["foo", "bar"]
        assert output.getvalue() == expected

    @pytest.mark.parametrize("log", [
        {"style": "%", "format": "[%(name)s][%(levelname)s] %(message)s"},
    ], indirect=True)
    def test_style_percent(self, log: logging.Logger, output: StringIO):
        log.setLevel("info")
        log.info("test")
        assert output.getvalue() == "[test][info] test\n"

    @pytest.mark.parametrize("log_failure", [{"style": "invalid"}], indirect=True)
    def test_style_invalid(self, log_failure):
        assert type(log_failure) is ValueError
        assert str(log_failure) == "Only {} and % formatting styles are supported"

    @freezegun.freeze_time("2000-01-02T03:04:05.123456Z")
    @pytest.mark.parametrize("log", [
        {"format": "[{asctime}][{name}][{levelname}] {message}"},
    ], indirect=True)
    def test_datefmt_default(self, log: logging.Logger, output: StringIO):
        log.setLevel("info")
        log.info("test")
        assert output.getvalue() == "[03:04:05][test][info] test\n"

    @freezegun.freeze_time("2000-01-02T03:04:05.123456Z")
    @pytest.mark.parametrize("log", [
        {"format": "[{asctime}][{name}][{levelname}] {message}", "datefmt": "%H:%M:%S.%f%z"},
    ], indirect=True)
    def test_datefmt_custom(self, log: logging.Logger, output: StringIO):
        log.setLevel("info")
        log.info("test")
        assert output.getvalue() == "[03:04:05.123456+0000][test][info] test\n"


class TestCaptureWarnings:
    @staticmethod
    def _warn(messages: Iterable[Tuple[str, Type[Warning]]], filterwarnings=None):
        frame = currentframe()
        assert frame
        assert frame.f_back
        lineno = getframeinfo(frame.f_back).lineno

        with warnings.catch_warnings():
            warnings.filterwarnings(filterwarnings or "always")
            for message, warningclass in messages:
                warnings.warn(message, warningclass, stacklevel=2)

        return lineno

    def test_no_capture(self, log: logging.Logger, output: StringIO):
        with pytest.warns(UserWarning, match=r"^Test warning$"):
            self._warn([("Test warning", UserWarning)])
        assert output.getvalue() == ""

    @pytest.mark.parametrize("log", [{"capture_warnings": True}], indirect=["log"])
    @pytest.mark.parametrize(("warning", "expected", "origin"), [
        (("Test warning", UserWarning), "[warnings][userwarning] Test warning\n", True),
        (("Test warning", DeprecationWarning), "[warnings][deprecationwarning] Test warning\n", True),
        (("Test warning", FutureWarning), "[warnings][futurewarning] Test warning\n", True),
        (("Test warning", StreamlinkWarning), "[warnings][streamlinkwarning] Test warning\n", False),
        (("Test warning", StreamlinkDeprecationWarning), "[warnings][streamlinkdeprecation] Test warning\n", False),
    ])
    def test_capture(
        self,
        recwarn: pytest.WarningsRecorder,
        log: logging.Logger,
        output: StringIO,
        warning: Tuple[str, Type[Warning]],
        expected: str,
        origin: bool,
    ):
        lineno = self._warn([warning])
        expected += f"  {__file__}:{lineno}\n" if origin else ""
        assert recwarn.list == []
        assert output.getvalue() == expected

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
        output: StringIO,
    ):
        lineno = self._warn([("foo", DeprecationWarning), ("bar", FutureWarning)])
        assert recwarn.list == []
        assert output.getvalue() == (
            f"[warnings][deprecationwarning] foo\n  {__file__}:{lineno}\n"
            + f"[warnings][futurewarning] bar\n  {__file__}:{lineno}\n"
        )

    @pytest.mark.parametrize("log", [{"capture_warnings": True}], indirect=["log"])
    def test_capture_consecutive_once(
        self,
        recwarn: pytest.WarningsRecorder,
        log: logging.Logger,
        output: StringIO,
    ):
        lineno = self._warn([("foo", UserWarning), ("foo", UserWarning)], "once")
        assert recwarn.list == []
        assert output.getvalue() == f"[warnings][userwarning] foo\n  {__file__}:{lineno}\n"

    @pytest.mark.parametrize("log", [{"capture_warnings": True}], indirect=["log"])
    @pytest.mark.parametrize("warning", [
        ("Test warning", UserWarning),
        ("Test warning", DeprecationWarning),
        ("Test warning", FutureWarning),
    ])
    def test_ignored(
        self,
        recwarn: pytest.WarningsRecorder,
        log: logging.Logger,
        output: StringIO,
        warning: Tuple[str, Type[Warning]],
    ):
        self._warn([warning], filterwarnings="ignore")
        assert recwarn.list == []
        assert output.getvalue() == ""
