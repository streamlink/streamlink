from __future__ import annotations

from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

import pytest

from streamlink.utils.deno import DenoProcessor


@pytest.fixture()
def fake_exe(tmp_path):
    exe = tmp_path / "deno.exe"
    exe.write_bytes(b"")
    return exe


class TestResolvePath:
    def test_explicit_path(self, fake_exe):
        assert DenoProcessor.resolve_path(str(fake_exe)) == str(fake_exe)

    def test_not_found(self):
        with patch("streamlink.utils.deno.resolve_executable", return_value=None):
            with pytest.raises(FileNotFoundError):
                DenoProcessor.resolve_path()

    def test_auto_resolve(self, fake_exe):
        with patch("streamlink.utils.deno.resolve_executable", return_value=fake_exe):
            assert DenoProcessor.resolve_path() == str(fake_exe)


class TestExecute:
    def test_success(self, fake_exe):
        stdin = 'console.log("Hello");'
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (stdin, "")

        with (
            patch("streamlink.utils.deno.DenoProcessor.resolve_path", return_value=str(fake_exe)),
            patch("subprocess.Popen", return_value=mock_proc),
        ):
            result = DenoProcessor.execute(stdin)

        assert result == stdin

    def test_stderr_raises(self, fake_exe):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = ("", "ERROR: Test deno error")

        with (
            patch("streamlink.utils.deno.DenoProcessor.resolve_path", return_value=str(fake_exe)),
            patch("subprocess.Popen", return_value=mock_proc),
        ):
            with pytest.raises(Exception, match="Deno process failed"):
                DenoProcessor.execute("invalid js")

    def test_timeout_kills_process(self, fake_exe):
        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = TimeoutExpired("deno", 1)

        with (
            patch("streamlink.utils.deno.DenoProcessor.resolve_path", return_value=str(fake_exe)),
            patch("subprocess.Popen", return_value=mock_proc),
        ):
            with pytest.raises(TimeoutExpired):
                DenoProcessor.execute('console.log("Hello");', timeout=1)

        mock_proc.kill.assert_called_once()


class TestProcessOutputIntegration:
    def test_output_collected(self, fake_exe):
        with patch("streamlink.utils.deno.DenoProcessor.resolve_path", return_value=str(fake_exe)):
            proc = DenoProcessor(["run", *DenoProcessor.DEFAULT_PARAMS], stdin=b'console.log("Hello");')

        proc.onstdout(0, "Hello")
        assert proc.output == "Hello"

    def test_onstderr_raises(self, fake_exe):
        with patch("streamlink.utils.deno.DenoProcessor.resolve_path", return_value=str(fake_exe)):
            proc = DenoProcessor(["run", *DenoProcessor.DEFAULT_PARAMS])

        with pytest.raises(RuntimeError, match="Deno error: some error"):
            proc.onstderr(0, "some error")
