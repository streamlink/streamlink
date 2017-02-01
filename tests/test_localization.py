import unittest
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from streamlink.utils.l10n import Localization


class TestLocalization(unittest.TestCase):
    def test_language_code(self):
        l = Localization("en_US")
        self.assertEqual("en_US", l.language_code)

    def test_bad_language_code(self):
        self.assertRaises(ValueError, Localization, "enUS")

    def test_equivalent(self):
        l = Localization("en_US")
        self.assertTrue(l.equivalent(language="eng"))
        self.assertTrue(l.equivalent(language="en"))
        self.assertTrue(l.equivalent(language="en", country="US"))
        self.assertTrue(l.equivalent(language="en", country="United States"))

    def test_equivalent_remap(self):
        l = Localization("fr_FR")
        self.assertTrue(l.equivalent(language="fra"))
        self.assertTrue(l.equivalent(language="fre"))

    def test_not_equivalent(self):
        l = Localization("es_ES")
        self.assertFalse(l.equivalent(language="eng"))
        self.assertFalse(l.equivalent(language="en"))
        self.assertFalse(l.equivalent(language="en", country="US"))
        self.assertFalse(l.equivalent(language="en", country="United States"))
        self.assertFalse(l.equivalent(language="en", country="ES"))
        self.assertFalse(l.equivalent(language="en", country="Spain"))

    @patch("locale.getdefaultlocale")
    def test_default(self, getdefaultlocale):
        getdefaultlocale.return_value = (None, None)
        l = Localization()
        self.assertEqual("en_US", l.language_code)
        self.assertTrue(l.equivalent(language="en", country="US"))

    def test_get_country(self):
        self.assertEqual("US",
                         Localization.get_country("USA").alpha2)
        self.assertEqual("GB",
                         Localization.get_country("GB").alpha2)
        self.assertEqual("United States",
                         Localization.get_country("United States").name)

    def test_get_country_miss(self):
        self.assertRaises(ValueError, Localization.get_country, "XE")
        self.assertRaises(ValueError, Localization.get_country, "XEX")
        self.assertRaises(ValueError, Localization.get_country, "Nowhere")

    def test_get_language(self):
        self.assertEqual("eng",
                         Localization.get_language("en").part2b)
        self.assertEqual("fre",
                         Localization.get_language("fra").part2b)
        self.assertEqual("fre",
                         Localization.get_language("fre").part2b)
        self.assertEqual("gre",
                         Localization.get_language("gre").part2b)

    def test_get_language_miss(self):
        self.assertRaises(ValueError, Localization.get_language, "00")
        self.assertRaises(ValueError, Localization.get_language, "000")
        self.assertRaises(ValueError, Localization.get_language, "0000")
