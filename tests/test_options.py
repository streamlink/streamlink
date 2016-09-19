import unittest

from streamlink.options import Options

class TestOptions(unittest.TestCase):
    def setUp(self):
        self.options = Options({
            "a_default": "default"
        })

    def test_options(self):
        self.assertEqual(self.options.get("a_default"), "default")
        self.assertEqual(self.options.get("non_existing"), None)

        self.options.set("a_option", "option")
        self.assertEqual(self.options.get("a_option"), "option")

if __name__ == "__main__":
    unittest.main()

