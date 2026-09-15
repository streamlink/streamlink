from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest

from streamlink.utils.deno import DenoProcessor


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _clear_resolve_path_cache():
    yield
    DenoProcessor.resolve_path.cache_clear()


@pytest.fixture()
def fake_exe(tmp_path):
    exe = tmp_path / "deno.exe"
    exe.write_bytes(b"")
    return exe


class TestResolvePath:
    @pytest.fixture()
    def mock_resolve_executable(self, monkeypatch: pytest.MonkeyPatch, fake_exe: Path):
        mock_resolve_executable = Mock(return_value=fake_exe)
        monkeypatch.setattr("streamlink.utils.deno.resolve_executable", mock_resolve_executable)
        yield mock_resolve_executable
        assert mock_resolve_executable.call_count == 1

    def test_explicit_path(self, fake_exe: Path):
        assert DenoProcessor.resolve_path(str(fake_exe)) == str(fake_exe)

    def test_not_found(self, mock_resolve_executable: Mock):
        mock_resolve_executable.return_value = None
        with pytest.raises(FileNotFoundError):
            DenoProcessor()
        with pytest.raises(FileNotFoundError):
            DenoProcessor()

    def test_auto_resolve(self, mock_resolve_executable: Mock, fake_exe: Path):
        assert DenoProcessor.resolve_path() == str(fake_exe)
        assert DenoProcessor.resolve_path() == str(fake_exe)


class TestProcessOutputIntegration:
    @pytest.fixture(autouse=True)
    def _resolve(self, monkeypatch: pytest.MonkeyPatch, fake_exe: Path):
        monkeypatch.setattr("streamlink.utils.deno.DenoProcessor.resolve_path", Mock(return_value=str(fake_exe)))

    def test_process_args(self, fake_exe: Path):
        proc = DenoProcessor(stdin="console.log('🐻');")
        assert proc.command == [str(fake_exe), "run", *DenoProcessor._RUN_FLAGS, "-"]
        assert proc.stdin == b""

    @pytest.mark.trio()
    async def test_log_command(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, fake_exe: Path):
        monkeypatch.setattr("streamlink.utils.deno.ProcessOutput.arun", AsyncMock(return_value=True))
        caplog.set_level(1, "streamlink")
        proc = DenoProcessor()
        assert await proc.arun(stdin=b"foo")
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.utils.deno",
                "trace",
                f"Running Deno with a stdin payload of 3 bytes: {[str(fake_exe), 'run', *DenoProcessor._RUN_FLAGS, '-']!r}",
            ),
        ]

    def test_output_collected(self):
        proc = DenoProcessor()
        proc.onstdout(0, "Hello")
        proc.onstdout(0, "World!")
        assert proc.output == "Hello\nWorld!"

    def test_onstderr_raises(self):
        proc = DenoProcessor()
        with pytest.raises(RuntimeError, match="Deno error: some error"):
            proc.onstderr(0, "some error")
