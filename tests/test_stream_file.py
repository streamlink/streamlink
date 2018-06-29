import unittest

from streamlink.stream.file import FileStream

try:
    from unittest.mock import Mock, patch, mock_open
except ImportError:
    from mock import Mock, patch, mock_open

from streamlink import Streamlink


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
