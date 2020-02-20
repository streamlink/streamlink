import unittest

from streamlink.plugins.streann import Streann


class TestPluginStreann(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://ott.streann.com/streaming/player.html?U2FsdGVkX1/BPZsbal3VWfGa7sWzTIlFtDEU+hyCEHP9Ma"
            + "vCxtCfL1G8nXtK5LHSsgFYhG3Nw9UilT1fx3H+lf5R54SLHAU6BKP/n7kjJBDF0HBFblSUHmApiEf5BrU3coECX9RQcR"
            + "aOY+uLtkeyEktvlrQ5nhg2QRw5x1IjkxFD0Rk5/ylTYxMqnu8snxRe2p09iJLi9E6cG8eXSHZby2We+pyV0obzGDbI2J"
            + "pyh4dFL646strLxFraeAJq5+mfpTqK10XZQi3sXA1/ULDH5lz+I9bZW4q/wZtlEdyA0CuB9LpDvCM11imLIhthGnRz",
        ]
        for url in should_match:
            self.assertTrue(Streann.can_handle_url(url))

        should_not_match = [
            "https://ott.streann.com",
        ]
        for url in should_not_match:
            self.assertFalse(Streann.can_handle_url(url))
