import unittest
from unittest.mock import Mock, mock_open, patch

from streamlink import Streamlink
from streamlink.stream.file import FileStream


class TestFileStream(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def test_open_file_path(self):
        m = mock_open()
        s = FileStream(self.session, path="/test/path")
        with patch('streamlink.stream.file.open', m, create=True):
            s.open()
            m.assert_called_with("/test/path")

    def test_open_fileobj(self):
        fileobj = Mock()
        s = FileStream(self.session, fileobj=fileobj)
        self.assertEqual(fileobj, s.open())
