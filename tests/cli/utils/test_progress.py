from io import StringIO
from pathlib import PurePosixPath, PureWindowsPath
from time import time
from unittest.mock import Mock, call, patch

import freezegun
import pytest

from streamlink_cli.utils.progress import Progress, ProgressFormatter
from tests import posix_only, windows_only


class TestProgressFormatter:
    @pytest.fixture(scope="class")
    def params(self):
        return dict(
            written="WRITTEN",
            elapsed="ELAPSED",
            speed="SPEED",
            path=lambda *_: "PATH",
        )

    @pytest.mark.parametrize(("term_width", "expected"), [
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
    ])
    def test_format(self, params, term_width, expected):
        with patch("streamlink_cli.utils.progress.ProgressFormatter.term_width", lambda: term_width):
            assert ProgressFormatter.format(ProgressFormatter.FORMATS, params) == expected

    @pytest.mark.parametrize(("term_width", "expected"), [
        (99, "[download] Written WRITTEN to PATH (ELAPSED)"),
        (55, "[download] Written WRITTEN to PATH (ELAPSED)"),
        (54, "[download] Written WRITTEN (ELAPSED)"),
        (36, "[download] Written WRITTEN (ELAPSED)"),
        (35, "[download] WRITTEN (ELAPSED)"),
        (28, "[download] WRITTEN (ELAPSED)"),
        (27, "[download] WRITTEN"),
        (1, "[download] WRITTEN"),
    ])
    def test_format_nospeed(self, params, term_width, expected):
        with patch("streamlink_cli.utils.progress.ProgressFormatter.term_width", lambda: term_width):
            assert ProgressFormatter.format(ProgressFormatter.FORMATS_NOSPEED, params) == expected

    def test_format_missing(self, params):
        with patch("streamlink_cli.utils.progress.ProgressFormatter.term_width", lambda: 99):
            assert ProgressFormatter.format(ProgressFormatter.FORMATS, {"written": "0"}) == "[download] 0"

    def test_format_error(self, params):
        with patch("streamlink_cli.utils.progress.ProgressFormatter.term_width", lambda: 99):
            params = dict(**params)
            params["path"] = Mock(side_effect=ValueError("fail"))
            assert ProgressFormatter.format(ProgressFormatter.FORMATS, params) == "[download] Written WRITTEN (ELAPSED @ SPEED)"

    @pytest.mark.parametrize(("size", "expected"), [
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
    ])
    def test_format_filesize(self, size, expected):
        assert ProgressFormatter.format_filesize(size) == expected
        assert ProgressFormatter.format_filesize(float(size)) == expected
        assert ProgressFormatter.format_filesize(size, "/s") == f"{expected}/s"

    @pytest.mark.parametrize(("elapsed", "expected"), [
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
    ])
    def test_format_time(self, elapsed, expected):
        assert ProgressFormatter.format_time(elapsed) == expected

    _path_posix = PurePosixPath("/foobar/baz/some file name")
    _path_windows_abs = PureWindowsPath("C:\\foobar\\baz\\some file name")
    _path_windows_rel = PureWindowsPath("foobar\\baz\\some file name")
    _path_windows_unc = PureWindowsPath("\\\\?\\foobar\\baz\\some file name")

    @pytest.mark.parametrize(("path", "max_width", "expected"), [
        pytest.param(_path_posix, 26, "/foobar/baz/some file name", id="posix - full path"),
        pytest.param(_path_posix, 25, "…oobar/baz/some file name", id="posix - truncated by 1"),
        pytest.param(_path_posix, 24, "…obar/baz/some file name", id="posix - truncated by 2"),
        pytest.param(_path_posix, 23, "…bar/baz/some file name", id="posix - truncated by 3"),
        pytest.param(_path_posix, 22, "…ar/baz/some file name", id="posix - truncated by 4"),
        pytest.param(_path_posix, 21, "…r/baz/some file name", id="posix - truncated by 5"),
        pytest.param(_path_posix, 20, "…/baz/some file name", id="posix - truncated by 6"),
        pytest.param(_path_posix, 19, "…baz/some file name", id="posix - truncated by 7 (cuts off separator)"),
        pytest.param(_path_posix, 16, "…/some file name", id="posix - truncated (all parts except name)"),
        pytest.param(_path_posix, 15, "…some file name", id="posix - truncated (name without separator)"),
        pytest.param(_path_posix, 14, "…ome file name", id="posix - truncated name"),
        pytest.param(_path_windows_abs, 28, "C:\\foobar\\baz\\some file name", id="windows abs - full path"),
        pytest.param(_path_windows_abs, 27, "C:…oobar\\baz\\some file name", id="windows abs - truncated by 1"),
        pytest.param(_path_windows_abs, 26, "C:…obar\\baz\\some file name", id="windows abs - truncated by 2"),
        pytest.param(_path_windows_abs, 25, "C:…bar\\baz\\some file name", id="windows abs - truncated by 3"),
        pytest.param(_path_windows_abs, 24, "C:…ar\\baz\\some file name", id="windows abs - truncated by 4"),
        pytest.param(_path_windows_abs, 23, "C:…r\\baz\\some file name", id="windows abs - truncated by 5"),
        pytest.param(_path_windows_abs, 22, "C:…\\baz\\some file name", id="windows abs - truncated by 6"),
        pytest.param(_path_windows_abs, 21, "C:…baz\\some file name", id="windows abs - truncated by 7 (cuts off separator)"),
        pytest.param(_path_windows_abs, 18, "C:…\\some file name", id="windows abs - truncated (all parts except name)"),
        pytest.param(_path_windows_abs, 17, "C:…some file name", id="windows abs - truncated (name without separator)"),
        pytest.param(_path_windows_abs, 16, "C:…ome file name", id="windows abs - truncated name"),
        pytest.param(_path_windows_rel, 25, "foobar\\baz\\some file name", id="windows rel - full path"),
        pytest.param(_path_windows_rel, 24, "…obar\\baz\\some file name", id="windows rel - truncated by 1"),
        pytest.param(_path_windows_rel, 23, "…bar\\baz\\some file name", id="windows rel - truncated by 2"),
        pytest.param(_path_windows_rel, 22, "…ar\\baz\\some file name", id="windows rel - truncated by 3"),
        pytest.param(_path_windows_rel, 21, "…r\\baz\\some file name", id="windows rel - truncated by 4"),
        pytest.param(_path_windows_rel, 20, "…\\baz\\some file name", id="windows rel - truncated by 5"),
        pytest.param(_path_windows_rel, 19, "…baz\\some file name", id="windows rel - truncated by 6 (cuts off separator)"),
        pytest.param(_path_windows_rel, 16, "…\\some file name", id="windows rel - truncated (all parts except name)"),
        pytest.param(_path_windows_rel, 15, "…some file name", id="windows rel - truncated (name without separator)"),
        pytest.param(_path_windows_rel, 14, "…ome file name", id="windows rel - truncated name"),
        pytest.param(_path_windows_unc, 29, "\\\\?\\foobar\\baz\\some file name", id="windows UNC - full path"),
        pytest.param(_path_windows_unc, 28, "\\\\?\\…obar\\baz\\some file name", id="windows UNC - truncated by 1"),
        pytest.param(_path_windows_unc, 20, "\\\\?\\…\\some file name", id="windows UNC - truncated (all parts except name)"),
        pytest.param(_path_windows_unc, 19, "\\\\?\\…some file name", id="windows UNC - truncated (name without separator)"),
        pytest.param(_path_windows_unc, 18, "\\\\?\\…ome file name", id="windows UNC - truncated name"),
    ])
    def test_format_path(self, path, max_width, expected):
        with patch("os.path.sep", "\\" if type(path) is PureWindowsPath else "/"):
            assert ProgressFormatter.format_path(path, max_width) == expected


class TestWidth:
    @pytest.mark.parametrize(("chars", "expected"), [
        ("ABCDEFGHIJ", 10),
        ("A你好世界こんにちは안녕하세요B", 30),
        ("·「」『』【】-=！@#￥%……&×（）", 30),
    ])
    def test_width(self, chars, expected):
        assert ProgressFormatter.width(chars) == expected

    @pytest.mark.parametrize(("prefix", "max_len", "expected"), [
        ("你好世界こんにちは안녕하세요CD", 10, "녕하세요CD"),
        ("你好世界こんにちは안녕하세요CD", 9, "하세요CD"),
        ("你好世界こんにちは안녕하세요CD", 23, "こんにちは안녕하세요CD"),
    ])
    def test_cut(self, prefix, max_len, expected):
        assert ProgressFormatter.cut(prefix, max_len) == expected


class TestPrint:
    @pytest.fixture(autouse=True)
    def _terminal_size(self):
        with patch("streamlink_cli.utils.progress.get_terminal_size") as mock_get_terminal_size:
            mock_get_terminal_size.return_value = Mock(columns=10)
            yield

    @pytest.fixture()
    def stream(self):
        return StringIO()

    @pytest.fixture()
    def progress(self, stream: StringIO):
        return Progress(stream, Mock())

    @posix_only
    def test_print_posix(self, progress: Progress, stream: StringIO):
        progress.print_inplace("foo")
        progress.print_inplace("barbaz")
        progress.print_inplace("0123456789")
        progress.print_inplace("abcdefghijk")
        progress.print_end()
        assert stream.getvalue() == "\rfoo       \rbarbaz    \r0123456789\rabcdefghijk\n"

    @windows_only
    def test_print_windows(self, progress: Progress, stream: StringIO):
        progress.print_inplace("foo")
        progress.print_inplace("barbaz")
        progress.print_inplace("0123456789")
        progress.print_inplace("abcdefghijk")
        progress.print_end()
        assert stream.getvalue() == "\rfoo      \rbarbaz   \r0123456789\rabcdefghijk\n"


class TestProgress:
    def test_download_speed(self):
        kib = b"\x00" * 1024
        output_write = Mock()
        progress = Progress(
            Mock(write=output_write),
            PurePosixPath("../../the/path/where/we/write/to"),
            interval=1,
            history=3,
            threshold=2,
        )

        with freezegun.freeze_time("2000-01-01T00:00:00Z") as frozen_time, \
             patch("os.path.sep", "/"), \
             patch("streamlink_cli.utils.progress.ProgressFormatter.term_width", Mock(return_value=70)) as mock_width:
            progress.started = time()
            assert not output_write.call_args_list

            progress.update()
            assert output_write.call_args_list[-1] \
                   == call("\r[download] Written 0 bytes to ../../the/path/where/we/write/to (0s)   ")

            frozen_time.tick()
            progress.write(kib * 1)
            progress.update()
            assert output_write.call_args_list[-1] \
                   == call("\r[download] Written 1.00 KiB to …th/where/we/write/to (1s @ 1.00 KiB/s)")

            frozen_time.tick()
            mock_width.return_value = 65
            progress.write(kib * 3)
            progress.update()
            assert output_write.call_args_list[-1] \
                   == call("\r[download] Written 4.00 KiB to …ere/we/write/to (2s @ 2.00 KiB/s)")

            frozen_time.tick()
            mock_width.return_value = 60
            progress.write(kib * 5)
            progress.update()
            assert output_write.call_args_list[-1] \
                   == call("\r[download] Written 9.00 KiB (3s @ 4.50 KiB/s)               ")

            frozen_time.tick()
            progress.write(kib * 7)
            progress.update()
            assert output_write.call_args_list[-1] \
                   == call("\r[download] Written 16.00 KiB (4s @ 7.50 KiB/s)              ")

            frozen_time.tick()
            progress.write(kib * 5)
            progress.update()
            assert output_write.call_args_list[-1] \
                   == call("\r[download] Written 21.00 KiB (5s @ 8.50 KiB/s)              ")

            frozen_time.tick()
            progress.update()
            assert output_write.call_args_list[-1] \
                   == call("\r[download] Written 21.00 KiB (6s @ 6.00 KiB/s)              ")
