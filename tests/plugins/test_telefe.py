import unittest

from streamlink.plugins.telefe import Telefe


class TestPluginTelefe(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Telefe.can_handle_url("http://telefe.com/pone-a-francella/temporada-1/programa-01/"))
        self.assertTrue(Telefe.can_handle_url("http://telefe.com/los-simuladores/temporada-1/capitulo-01/"))
        self.assertTrue(Telefe.can_handle_url("http://telefe.com/dulce-amor/capitulos/capitulo-01/"))

        # shouldn't match
        self.assertFalse(Telefe.can_handle_url("http://telefe.com/"))
        self.assertFalse(Telefe.can_handle_url("http://www.telefeinternacional.com.ar/"))
        self.assertFalse(Telefe.can_handle_url("http://marketing.telefe.com/"))
