from time import time

import freezegun
import pytest

from streamlink_cli.utils.progress import Progress, ProgressFormatter
from streamlink_cli.utils.terminal import TerminalOutput


class TestProgressFormatter:
    @pytest.fixture(scope="class")
    def params(self):
        return dict(written="WRITTEN", elapsed="ELAPSED", speed="SPEED")

    @pytest.mark.parametrize("max_size,expected", [
        (99, "[download] Written WRITTEN (ELAPSED @ SPEED)"),
        (44, "[download] Written WRITTEN (ELAPSED @ SPEED)"),
        (43, "[download] WRITTEN (ELAPSED @ SPEED)"),
        (36, "[download] WRITTEN (ELAPSED @ SPEED)"),
        (35, "[download] WRITTEN (ELAPSED)"),
        (28, "[download] WRITTEN (ELAPSED)"),
        (27, "[download] WRITTEN"),
        (1, "[download] WRITTEN"),
    ])
    def test_format(self, max_size, params, expected):
        assert ProgressFormatter.format(max_size, ProgressFormatter.FORMATS, **params) == expected

    @pytest.mark.parametrize("max_size,expected", [
        (99, "[download] Written WRITTEN (ELAPSED)"),
        (36, "[download] Written WRITTEN (ELAPSED)"),
        (35, "[download] WRITTEN (ELAPSED)"),
        (28, "[download] WRITTEN (ELAPSED)"),
        (27, "[download] WRITTEN"),
        (1, "[download] WRITTEN"),
    ])
    def test_format_nospeed(self, max_size, params, expected):
        assert ProgressFormatter.format(max_size, ProgressFormatter.FORMATS_NOSPEED, **params) == expected

    @pytest.mark.parametrize("size,expected", [
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

    @pytest.mark.parametrize("elapsed,expected", [
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


class FakeOutput(TerminalOutput):
    def __init__(self):
        super().__init__()
        self.buffer = []

    # noinspection PyMethodMayBeStatic
    def term_width(self):
        return 50

    def print_inplace(self, msg):
        self.buffer.append(msg)

    def end(self):  # pragma: no cover
        self.buffer.append("\n")


class TestProgress:
    def test_download_speed(self):
        kib = b"\x00" * 1024
        output = FakeOutput()
        progress = Progress(
            output=output,
            interval=1,
            history=3,
            threshold=2,
        )

        with freezegun.freeze_time("2000-01-01T00:00:00Z") as frozen_time:
            progress.started = time()
            assert not output.buffer

            progress.update()
            assert output.buffer[-1] == "[download] Written 0 bytes (0s)"

            frozen_time.tick()
            progress.put(kib * 1)
            progress.update()
            assert output.buffer[-1] == "[download] Written 1.00 KiB (1s @ 1.00 KiB/s)"

            frozen_time.tick()
            progress.put(kib * 3)
            progress.update()
            assert output.buffer[-1] == "[download] Written 4.00 KiB (2s @ 2.00 KiB/s)"

            frozen_time.tick()
            progress.put(kib * 5)
            progress.update()
            assert output.buffer[-1] == "[download] Written 9.00 KiB (3s @ 4.50 KiB/s)"

            frozen_time.tick()
            progress.put(kib * 7)
            progress.update()
            assert output.buffer[-1] == "[download] Written 16.00 KiB (4s @ 7.50 KiB/s)"

            frozen_time.tick()
            progress.put(kib * 5)
            progress.update()
            assert output.buffer[-1] == "[download] Written 21.00 KiB (5s @ 8.50 KiB/s)"

            frozen_time.tick()
            progress.update()
            assert output.buffer[-1] == "[download] Written 21.00 KiB (6s @ 6.00 KiB/s)"
