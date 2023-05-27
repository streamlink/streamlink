from unittest.mock import Mock, call, mock_open, patch

from streamlink import Streamlink
from streamlink.stream.file import FileStream


class TestFileStream:
    def test_open_path(self, session: Streamlink):
        mock = mock_open()
        stream = FileStream(session, path="/test/path")
        with patch("streamlink.stream.file.open", mock, create=True):
            stream.open()
        assert mock.call_args_list == [call("/test/path")]

    def test_open_fileobj(self, session: Streamlink):
        fileobj = Mock()
        stream = FileStream(session, fileobj=fileobj)
        assert stream.open() is fileobj
