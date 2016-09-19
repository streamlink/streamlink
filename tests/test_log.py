import unittest

from streamlink.logger import Logger
from streamlink.compat import is_py2

# Docs says StringIO is suppose to take non-unicode strings
# but it doesn't, so let's use BytesIO instead there...

if is_py2:
    from io import BytesIO as StringIO
else:
    from io import StringIO

class TestSession(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.manager = Logger()
        self.manager.set_output(self.output)
        self.logger = self.manager.new_module("test")

    def test_level(self):
        self.logger.debug("test")
        self.assertEqual(self.output.tell(), 0)
        self.manager.set_level("debug")
        self.logger.debug("test")
        self.assertNotEqual(self.output.tell(), 0)

    def test_output(self):
        self.manager.set_level("debug")
        self.logger.debug("test")
        self.assertEqual(self.output.getvalue(), "[test][debug] test\n")

if __name__ == "__main__":
    unittest.main()

