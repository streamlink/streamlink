import base64
import unittest

from streamlink.utils.swf import swfdecompress


class TestUtilsSWF(unittest.TestCase):
    def test_swf_decompress(self):
        # FYI, not a valid SWF
        swf = b"FWS " + b"0000" + b"test data 12345"
        swf_compressed = b"CWS " + b"0000" + base64.b64decode(b"eJwrSS0uUUhJLElUMDQyNjEFACpTBJo=")
        self.assertEqual(swf, swfdecompress(swf_compressed))
        self.assertEqual(swf, swfdecompress(swf))
