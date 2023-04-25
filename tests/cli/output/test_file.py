import os
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from streamlink_cli.output import FileOutput


@patch("streamlink_cli.output.file.stdout")
class TestFileOutput(unittest.TestCase):
    @staticmethod
    def subject(filename, fd):
        fo_record = FileOutput(fd=fd)
        fo_main = FileOutput(filename=filename, record=fo_record)

        return fo_main, fo_record

    def test_init(self, mock_stdout: Mock):
        mock_path = Mock(spec=Path("foo", "bar"))
        fo_main, fo_record = self.subject(mock_path, mock_stdout)

        assert not fo_main.opened
        assert fo_main.filename is mock_path
        assert fo_main.fd is None
        assert fo_main.record is fo_record

        assert not fo_main.record.opened
        assert fo_main.record.filename is None
        assert fo_main.record.fd is mock_stdout
        assert fo_main.record.record is None

    def test_early_close(self, mock_stdout: Mock):
        mock_path = Mock(spec=Path("foo", "bar"))
        fo_main, fo_record = self.subject(mock_path, mock_stdout)

        fo_main.close()  # doesn't raise

    def test_early_write(self, mock_stdout: Mock):
        mock_path = Mock(spec=Path("foo", "bar"))
        fo_main, fo_record = self.subject(mock_path, mock_stdout)

        with pytest.raises(OSError, match=r"^Output is not opened$"):
            fo_main.write(b"foo")

    def _test_open(self, mock_open: Mock, mock_stdout: Mock):
        mock_path = Mock(spec=Path("foo", "bar"))
        mock_fd = mock_open(mock_path, "wb")
        fo_main, fo_record = self.subject(mock_path, mock_stdout)

        fo_main.open()
        assert fo_main.opened
        assert fo_main.record.opened
        assert mock_path.parent.mkdir.call_args_list == [call(parents=True, exist_ok=True)]
        assert fo_main.fd is mock_fd

        fo_main.write(b"foo")
        assert mock_fd.write.call_args_list == [call(b"foo")]
        assert mock_stdout.write.call_args_list == [call(b"foo")]

        fo_main.close()
        assert mock_fd.close.call_args_list == [call()]
        assert mock_stdout.close.call_args_list == []
        assert not fo_main.opened
        assert not fo_main.record.opened

        return mock_path

    @pytest.mark.posix_only()
    @patch("builtins.open")
    def test_open_posix(self, mock_open: Mock, mock_stdout: Mock):
        self._test_open(mock_open, mock_stdout)

    @pytest.mark.windows_only()
    @patch("streamlink_cli.output.file.msvcrt")
    @patch("builtins.open")
    def test_open_windows(self, mock_open: Mock, mock_msvcrt: Mock, mock_stdout: Mock):
        mock_path = self._test_open(mock_open, mock_stdout)
        assert mock_msvcrt.setmode.call_args_list == [
            call(mock_stdout.fileno(), os.O_BINARY),
            call(mock_open(mock_path, "wb").fileno(), os.O_BINARY),
        ]
