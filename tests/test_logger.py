import logging
from io import StringIO
from unittest.mock import patch

import freezegun
import pytest

from streamlink import logger


class TestLogging:
    @pytest.fixture
    def output(self):
        return StringIO()

    @pytest.fixture
    def log(self, request, output: StringIO):
        params = getattr(request, "param", {})
        params.setdefault("format", "[{name}][{levelname}] {message}")
        params.setdefault("style", "{")
        fakeroot = logging.getLogger("streamlink.test")
        with patch("streamlink.logger.root", fakeroot):
            logger.basicConfig(stream=output, **params)
            yield fakeroot

    @pytest.fixture
    def log_failure(self, request, log: logging.Logger, output: StringIO):
        params = getattr(request, "param", {})
        root = logging.getLogger("streamlink")
        with pytest.raises(Exception) as cm:
            with patch("streamlink.logger.root", root):
                logger.basicConfig(stream=output, **params)
        return cm.value

    @pytest.mark.parametrize("name,level", [
        ("none", logger.NONE),
        ("critical", logger.CRITICAL),
        ("error", logger.ERROR),
        ("warning", logger.WARNING),
        ("info", logger.INFO),
        ("debug", logger.DEBUG),
        ("trace", logger.TRACE),
    ])
    def test_level_names(self, name: str, level: int):
        assert logging.getLevelName(level) == name
        assert logging.getLevelName(name) == level
        assert logging.getLevelName(name.upper()) == level

    def test_levels_list(self):
        assert logger.levels == ["none", "critical", "error", "warning", "info", "debug", "trace"]

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
        assert not output.getvalue()

    def test_output(self, log: logging.Logger, output: StringIO):
        log.setLevel("debug")
        log.debug("test")
        assert output.getvalue() == "[test][debug] test\n"

    def test_trace_output(self, log: logging.Logger, output: StringIO):
        log.setLevel("trace")
        log.trace("test")  # type: ignore[attr-defined]
        assert output.getvalue() == "[test][trace] test\n"

    def test_trace_no_output(self, log: logging.Logger, output: StringIO):
        log.setLevel("debug")
        log.trace("test")  # type: ignore[attr-defined]
        assert output.getvalue() == ""

    # https://github.com/streamlink/streamlink/issues/4862
    def test_trace_module_name(self, caplog: pytest.LogCaptureFixture, log: logging.Logger):
        caplog.set_level(1)
        log = logging.getLogger(self.__class__.__module__)
        log.trace("foo")  # type: ignore[attr-defined]
        log.log(logger.TRACE, "bar")
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("test_logger", "trace", "foo"),
            ("test_logger", "trace", "bar"),
        ]

    def test_debug_out_at_trace(self, log: logging.Logger, output: StringIO):
        log.setLevel("trace")
        log.debug("test")
        assert output.getvalue() == "[test][debug] test\n"

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
        {"format": "[{asctime}][{name}][{levelname}] {message}", "datefmt": "%H:%M:%S.%f"},
    ], indirect=True)
    def test_datefmt_custom(self, log: logging.Logger, output: StringIO):
        log.setLevel("info")
        log.info("test")
        assert output.getvalue() == "[03:04:05.123456][test][info] test\n"
