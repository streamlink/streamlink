import unittest
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


from streamlink.utils.l10n import Localization, Country, Language


class TestLocalization(unittest.TestCase):
    def test_language_code(self):
        l = Localization("en_US")
        self.assertEqual("en_US", l.language_code)

    def test_bad_language_code(self):
        self.assertRaises(LookupError, Localization, "enUS")

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
        self.assertRaises(LookupError, Localization.get_country, "XE")
        self.assertRaises(LookupError, Localization.get_country, "XEX")
        self.assertRaises(LookupError, Localization.get_country, "Nowhere")

    def test_get_language(self):
        self.assertEqual("eng",
                         Localization.get_language("en").alpha3)
        self.assertEqual("fre",
                         Localization.get_language("fra").bibliographic)
        self.assertEqual("fra",
                         Localization.get_language("fre").alpha3)
        self.assertEqual("gre",
                         Localization.get_language("gre").bibliographic)

    def test_get_language_miss(self):
        self.assertRaises(LookupError, Localization.get_language, "00")
        self.assertRaises(LookupError, Localization.get_language, "000")
        self.assertRaises(LookupError, Localization.get_language, "0000")

    def test_country_compare(self):
        a = Country("AA", "AAA", "001", "Test")
        b = Country("AA", "AAA", "001", "Test")
        self.assertEqual(a, b)

    def test_language_compare(self):
        a = Language("AA", "AAA", "Test")
        b = Language("AA", None, "Test")
        self.assertEqual(a, b)

        a = Language("BB", "BBB", "Test")
        b = Language("AA", None, "Test")
        self.assertNotEqual(a, b)
