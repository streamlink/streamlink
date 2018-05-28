import unittest

from streamlink.plugins.eltrecetv import ElTreceTV


class TestPluginElTreceTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(ElTreceTV.can_handle_url("http://www.eltrecetv.com.ar/vivo"))
        self.assertTrue(ElTreceTV.can_handle_url("http://www.eltrecetv.com.ar/pasapalabra/capitulo-1_084027"))
        self.assertTrue(ElTreceTV.can_handle_url("http://www.eltrecetv.com.ar/a-todo-o-nada-2014/programa-2_072251"))

        # shouldn't match
        self.assertFalse(ElTreceTV.can_handle_url("http://eltrecetv.com.ar/"))
        self.assertFalse(ElTreceTV.can_handle_url("https://www.youtube.com/c/eltrece"))
