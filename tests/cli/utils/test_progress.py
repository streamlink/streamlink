import sys
from io import StringIO
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from time import time
from unittest.mock import Mock

import freezegun
import pytest

from streamlink_cli.utils.progress import Progress, ProgressFormatter
from tests.testutils.handshake import Handshake


class TestProgressFormatter:
    @pytest.fixture(scope="class")
    def params(self):
        return dict(
            written="WRITTEN",
            elapsed="ELAPSED",
            speed="SPEED",
            path=lambda *_: "PATH",
        )

    @pytest.fixture(autouse=True)
    def term_width(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        width = getattr(request, "param", 99)
        monkeypatch.setattr("streamlink_cli.utils.progress.ProgressFormatter.term_width", lambda: width)

    @pytest.mark.parametrize(
        ("term_width", "expected"),
        [
            (99, "[download] Written WRITTEN to PATH (ELAPSED @ SPEED)"),
            (63, "[download] Written WRITTEN to PATH (ELAPSED @ SPEED)"),
            (62, "[download] Written WRITTEN (ELAPSED @ SPEED)"),
            (44, "[download] Written WRITTEN (ELAPSED @ SPEED)"),
            (43, "[download] WRITTEN (ELAPSED @ SPEED)"),
            (36, "[download] WRITTEN (ELAPSED @ SPEED)"),
            (35, "[download] WRITTEN (ELAPSED)"),
            (28, "[download] WRITTEN (ELAPSED)"),
            (27, "[download] WRITTEN"),
            (1, "[download] WRITTEN"),
        ],
        indirect=["term_width"],
    )
    def test_format(self, params, term_width, expected):
        assert ProgressFormatter.format(ProgressFormatter.FORMATS, params) == expected

    @pytest.mark.parametrize(
        ("term_width", "expected"),
        [
            (99, "[download] Written WRITTEN to PATH (ELAPSED)"),
            (55, "[download] Written WRITTEN to PATH (ELAPSED)"),
            (54, "[download] Written WRITTEN (ELAPSED)"),
            (36, "[download] Written WRITTEN (ELAPSED)"),
            (35, "[download] WRITTEN (ELAPSED)"),
            (28, "[download] WRITTEN (ELAPSED)"),
            (27, "[download] WRITTEN"),
            (1, "[download] WRITTEN"),
        ],
        indirect=["term_width"],
    )
    def test_format_nospeed(self, params, term_width, expected):
        assert ProgressFormatter.format(ProgressFormatter.FORMATS_NOSPEED, params) == expected

    def test_format_missing(self, params):
        assert ProgressFormatter.format(ProgressFormatter.FORMATS, {"written": "0"}) == "[download] 0"

    def test_format_error(self, params):
        params = dict(**params)
        params["path"] = Mock(side_effect=ValueError("fail"))
        assert ProgressFormatter.format(ProgressFormatter.FORMATS, params) == "[download] Written WRITTEN (ELAPSED @ SPEED)"

    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            (0, "0 bytes"),
            (2**10 - 1, "1023 bytes"),
            (2**10, "1.00 KiB"),
            (2**20 - 1, "1023.99 KiB"),
            (2**20, "1.00 MiB"),
            (2**30 - 1, "1023.99 MiB"),
            (2**30, "1.00 GiB"),
            (2**40 - 1, "1023.99 GiB"),
            (2**40, "1.00 TiB"),
            (2**50 - 1, "1023.99 TiB"),
            (2**50, "1024.00 TiB"),
        ],
    )
    def test_format_filesize(self, size, expected):
        assert ProgressFormatter.format_filesize(size) == expected
        assert ProgressFormatter.format_filesize(float(size)) == expected
        assert ProgressFormatter.format_filesize(size, "/s") == f"{expected}/s"

    @pytest.mark.parametrize(
        ("elapsed", "expected"),
        [
            (-1, "0s"),
            (0, "0s"),
            (9, "9s"),
            (10, "10s"),
            (59, "59s"),
            (60, "1m00s"),
            (69, "1m09s"),
            (70, "1m10s"),
            (119, "1m59s"),
            (120, "2m00s"),
            (3599, "59m59s"),
            (3600, "1h00m00s"),
            (3659, "1h00m59s"),
            (3660, "1h01m00s"),
            (3661, "1h01m01s"),
            (86399, "23h59m59s"),
            (86400, "24h00m00s"),
            (172800, "48h00m00s"),
        ],
    )
    def test_format_time(self, elapsed, expected):
        assert ProgressFormatter.format_time(elapsed) == expected


_PATH_POSIX = PurePosixPath("/foobar/baz/some file name")
_PATH_WIN_ABS = PureWindowsPath("C:\\foobar\\baz\\some file name")
_PATH_WIN_REL = PureWindowsPath("foobar\\baz\\some file name")
_PATH_WIN_UNC = PureWindowsPath("\\\\?\\foobar\\baz\\some file name")


class _TestFormatPath:
    # noinspection PyMethodMayBeStatic
    def test_format_path(self, monkeypatch: pytest.MonkeyPatch, path: PurePath, max_width: int, expected: str):
        monkeypatch.setattr("os.path.sep", "\\" if type(path) is PureWindowsPath else "/")
        assert ProgressFormatter.format_path(path, max_width) == expected


@pytest.mark.parametrize(
    ("path", "max_width", "expected"),
    [
        pytest.param(_PATH_POSIX, 26, "/foobar/baz/some file name", id="full path"),
        pytest.param(_PATH_POSIX, 25, "…oobar/baz/some file name", id="truncated by 1"),
        pytest.param(_PATH_POSIX, 24, "…obar/baz/some file name", id="truncated by 2"),
        pytest.param(_PATH_POSIX, 23, "…bar/baz/some file name", id="truncated by 3"),
        pytest.param(_PATH_POSIX, 22, "…ar/baz/some file name", id="truncated by 4"),
        pytest.param(_PATH_POSIX, 21, "…r/baz/some file name", id="truncated by 5"),
        pytest.param(_PATH_POSIX, 20, "…/baz/some file name", id="truncated by 6"),
        pytest.param(_PATH_POSIX, 19, "…baz/some file name", id="truncated by 7 (cuts off separator)"),
        pytest.param(_PATH_POSIX, 16, "…/some file name", id="truncated (all parts except name)"),
        pytest.param(_PATH_POSIX, 15, "…some file name", id="truncated (name without separator)"),
        pytest.param(_PATH_POSIX, 14, "…ome file name", id="truncated name"),
    ],
)
class TestFormatPathPOSIX(_TestFormatPath):
    pass


@pytest.mark.parametrize(
    ("path", "max_width", "expected"),
    [
        pytest.param(_PATH_WIN_ABS, 28, "C:\\foobar\\baz\\some file name", id="full path"),
        pytest.param(_PATH_WIN_ABS, 27, "C:…oobar\\baz\\some file name", id="truncated by 1"),
        pytest.param(_PATH_WIN_ABS, 26, "C:…obar\\baz\\some file name", id="truncated by 2"),
        pytest.param(_PATH_WIN_ABS, 25, "C:…bar\\baz\\some file name", id="truncated by 3"),
        pytest.param(_PATH_WIN_ABS, 24, "C:…ar\\baz\\some file name", id="truncated by 4"),
        pytest.param(_PATH_WIN_ABS, 23, "C:…r\\baz\\some file name", id="truncated by 5"),
        pytest.param(_PATH_WIN_ABS, 22, "C:…\\baz\\some file name", id="truncated by 6"),
        pytest.param(_PATH_WIN_ABS, 21, "C:…baz\\some file name", id="truncated by 7 (cuts off separator)"),
        pytest.param(_PATH_WIN_ABS, 18, "C:…\\some file name", id="truncated (all parts except name)"),
        pytest.param(_PATH_WIN_ABS, 17, "C:…some file name", id="truncated (name without separator)"),
        pytest.param(_PATH_WIN_ABS, 16, "C:…ome file name", id="truncated name"),
    ],
)
class TestFormatPathWindowsAbsolute(_TestFormatPath):
    pass


@pytest.mark.parametrize(
    ("path", "max_width", "expected"),
    [
        pytest.param(_PATH_WIN_REL, 25, "foobar\\baz\\some file name", id="full path"),
        pytest.param(_PATH_WIN_REL, 24, "…obar\\baz\\some file name", id="truncated by 1"),
        pytest.param(_PATH_WIN_REL, 23, "…bar\\baz\\some file name", id="truncated by 2"),
        pytest.param(_PATH_WIN_REL, 22, "…ar\\baz\\some file name", id="truncated by 3"),
        pytest.param(_PATH_WIN_REL, 21, "…r\\baz\\some file name", id="truncated by 4"),
        pytest.param(_PATH_WIN_REL, 20, "…\\baz\\some file name", id="truncated by 5"),
        pytest.param(_PATH_WIN_REL, 19, "…baz\\some file name", id="truncated by 6 (cuts off separator)"),
        pytest.param(_PATH_WIN_REL, 16, "…\\some file name", id="truncated (all parts except name)"),
        pytest.param(_PATH_WIN_REL, 15, "…some file name", id="truncated (name without separator)"),
        pytest.param(_PATH_WIN_REL, 14, "…ome file name", id="truncated name"),
    ],
)
class TestFormatPathWindowsRelative(_TestFormatPath):
    pass


@pytest.mark.parametrize(
    ("path", "max_width", "expected"),
    [
        # <py312: server/host name is not part of the path's drive, so it'll get truncated
        pytest.param(_PATH_WIN_UNC, 29, "\\\\?\\foobar\\baz\\some file name", id="full path"),
        pytest.param(_PATH_WIN_UNC, 28, "\\\\?\\…obar\\baz\\some file name", id="truncated by 1"),
        pytest.param(_PATH_WIN_UNC, 20, "\\\\?\\…\\some file name", id="truncated (all parts except name)"),
        pytest.param(_PATH_WIN_UNC, 19, "\\\\?\\…some file name", id="truncated (name without separator)"),
        pytest.param(_PATH_WIN_UNC, 18, "\\\\?\\…ome file name", id="truncated name"),
    ]
    if sys.version_info < (3, 12)
    else [
        # >=py312: server/host name is part of the path's drive, so it won't get truncated
        pytest.param(_PATH_WIN_UNC, 29, "\\\\?\\foobar\\baz\\some file name", id="full path"),
        pytest.param(_PATH_WIN_UNC, 28, "\\\\?\\foobar…az\\some file name", id="truncated by 1"),
        pytest.param(_PATH_WIN_UNC, 26, "\\\\?\\foobar…\\some file name", id="truncated (all parts except name)"),
        pytest.param(_PATH_WIN_UNC, 25, "\\\\?\\foobar…some file name", id="truncated (name without separator)"),
        pytest.param(_PATH_WIN_UNC, 24, "\\\\?\\foobar…ome file name", id="truncated name"),
    ],
)
class TestFormatPathWindowsUniversalNamingConvention(_TestFormatPath):
    pass


class TestWidth:
    @pytest.mark.parametrize(
        ("chars", "expected"),
        [
            ("ABCDEFGHIJ", 10),
            ("A你好世界こんにちは안녕하세요B", 30),
            ("·「」『』【】-=！@#￥%……&×（）", 30),  # noqa: RUF001
        ],
    )
    def test_width(self, chars, expected):
        assert ProgressFormatter.width(chars) == expected

    @pytest.mark.parametrize(
        ("prefix", "max_len", "expected"),
        [
            ("你好世界こんにちは안녕하세요CD", 10, "녕하세요CD"),
            ("你好世界こんにちは안녕하세요CD", 9, "하세요CD"),
            ("你好世界こんにちは안녕하세요CD", 23, "こんにちは안녕하세요CD"),
        ],
    )
    def test_cut(self, prefix, max_len, expected):
        assert ProgressFormatter.cut(prefix, max_len) == expected


class TestPrint:
    @pytest.fixture(autouse=True)
    def _get_terminal_size(self, monkeypatch: pytest.MonkeyPatch):
        mock_get_terminal_size = Mock(return_value=Mock(columns=10))
        monkeypatch.setattr("streamlink_cli.utils.progress.get_terminal_size", mock_get_terminal_size)

    @pytest.fixture()
    def stream(self):
        return StringIO()

    @pytest.fixture()
    def progress(self, stream: StringIO):
        return Progress(stream, Mock())

    @pytest.mark.posix_only()
    def test_print_posix(self, progress: Progress, stream: StringIO):
        progress.print_inplace("foo")
        progress.print_inplace("barbaz")
        progress.print_inplace("0123456789")
        progress.print_inplace("abcdefghijk")
        progress.print_end()
        assert stream.getvalue() == "\rfoo       \rbarbaz    \r0123456789\rabcdefghijk\n"

    @pytest.mark.windows_only()
    def test_print_windows(self, progress: Progress, stream: StringIO):
        progress.print_inplace("foo")
        progress.print_inplace("barbaz")
        progress.print_inplace("0123456789")
        progress.print_inplace("abcdefghijk")
        progress.print_end()
        assert stream.getvalue() == "\rfoo      \rbarbaz   \r0123456789\rabcdefghijk\n"


class TestProgress:
    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("os.path.sep", "/")

    @pytest.fixture(autouse=True)
    def mock_width(self, monkeypatch: pytest.MonkeyPatch):
        mock = Mock(return_value=70)
        monkeypatch.setattr("streamlink_cli.utils.progress.ProgressFormatter.term_width", mock)
        return mock

    @pytest.fixture()
    def frozen_time(self):
        with freezegun.freeze_time("2000-01-01T00:00:00Z") as frozen_time:
            yield frozen_time

    def test_download_speed(self, mock_width: Mock, frozen_time):
        kib = b"\x00" * 1024
        stream = StringIO()
        progress = Progress(
            stream=stream,
            path=PurePosixPath("../../the/path/where/we/write/to"),
            interval=1,
            history=3,
            threshold=2,
        )

        progress.started = time()
        assert stream.getvalue() == ""

        progress.update()
        assert stream.getvalue().split("\r")[-1] == "[download] Written 0 bytes to ../../the/path/where/we/write/to (0s)   "

        frozen_time.tick()
        progress.write(kib * 1)
        progress.update()
        assert stream.getvalue().split("\r")[-1] == "[download] Written 1.00 KiB to …th/where/we/write/to (1s @ 1.00 KiB/s)"

        frozen_time.tick()
        mock_width.return_value = 65
        progress.write(kib * 3)
        progress.update()
        assert stream.getvalue().split("\r")[-1] == "[download] Written 4.00 KiB to …ere/we/write/to (2s @ 2.00 KiB/s)"

        frozen_time.tick()
        mock_width.return_value = 60
        progress.write(kib * 5)
        progress.update()
        assert stream.getvalue().split("\r")[-1] == "[download] Written 9.00 KiB (3s @ 4.50 KiB/s)               "

        frozen_time.tick()
        progress.write(kib * 7)
        progress.update()
        assert stream.getvalue().split("\r")[-1] == "[download] Written 16.00 KiB (4s @ 7.50 KiB/s)              "

        frozen_time.tick()
        progress.write(kib * 5)
        progress.update()
        assert stream.getvalue().split("\r")[-1] == "[download] Written 21.00 KiB (5s @ 8.50 KiB/s)              "

        frozen_time.tick()
        progress.update()
        assert stream.getvalue().split("\r")[-1] == "[download] Written 21.00 KiB (6s @ 6.00 KiB/s)              "

    def test_update(self):
        handshake = Handshake()

        class _Progress(Progress):
            def update(self):
                with handshake():
                    return super().update()

        stream = StringIO()
        thread = _Progress(stream=stream, path=PurePath())
        # override the thread's polling time after initializing the deque of the rolling average download speed:
        # the interval constructor keyword is used to set the deque size
        thread.interval = 0
        thread.start()

        # first tick
        assert handshake.wait_ready(1)
        thread.write(b"123")
        assert handshake.step(1)
        assert stream.getvalue().split("\r")[-1].startswith("[download] Written 3 bytes")

        # second tick
        assert handshake.wait_ready(1)
        thread.write(b"465")
        assert handshake.step(1)
        assert stream.getvalue().split("\r")[-1].startswith("[download] Written 6 bytes")

        # close progress thread
        assert handshake.wait_ready(1)
        thread.close()
        assert handshake.step(1)
        assert stream.getvalue().split("\r")[-1].startswith("[download] Written 6 bytes")

        # write data right after closing the thread, but before it has halted
        thread.write(b"789")
        handshake.go()
        thread.join(1)
        assert not thread.is_alive()
        assert stream.getvalue().split("\r")[-1].startswith("[download] Written 9 bytes")
