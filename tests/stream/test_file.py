from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING
from unittest.mock import Mock, call

import pytest

from streamlink.stream.file import FileStream


if TYPE_CHECKING:
    from streamlink import Streamlink


class TestFileStream:
    @pytest.fixture(autouse=True)
    def mock_open(self, monkeypatch: pytest.MonkeyPatch) -> Mock:
        mock_open = Mock(return_value=BytesIO(b"foo"))
        monkeypatch.setattr("builtins.open", mock_open)

        return mock_open

    def test_open_path(self, session: Streamlink, mock_open: Mock):
        stream = FileStream(session, path="/test/path")
        streamio = stream.open()
        assert mock_open.call_args_list == [call("/test/path", "rb")]
        assert streamio.read() == b"foo"

        streamio.close()

    def test_open_fileobj(self, session: Streamlink, mock_open: Mock):
        fileobj = BytesIO(b"bar")
        stream = FileStream(session, fileobj=fileobj)
        streamio = stream.open()
        assert streamio is fileobj
        assert mock_open.call_args_list == []
        assert streamio.read() == b"bar"

        streamio.close()
