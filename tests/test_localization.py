import unittest
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

import streamlink.utils.l10n as l10n


class TestLocalization(unittest.TestCase):
    def setUp(self):
        l10n.PYCOUNTRY = False

    def test_pycountry(self):
        self.assertEqual(False, l10n.PYCOUNTRY)

    def test_language_code(self):
        l = l10n.Localization("en_US")
        self.assertEqual("en_US", l.language_code)

    def test_bad_language_code(self):
        self.assertRaises(LookupError, l10n.Localization, "enUS")

    def test_equivalent(self):
        l = l10n.Localization("en_US")
        self.assertTrue(l.equivalent(language="eng"))
        self.assertTrue(l.equivalent(language="en"))
        self.assertTrue(l.equivalent(language="en", country="US"))
        self.assertTrue(l.equivalent(language="en", country="United States"))

    def test_equivalent_remap(self):
        l = l10n.Localization("fr_FR")
        self.assertTrue(l.equivalent(language="fra"))
        self.assertTrue(l.equivalent(language="fre"))

    def test_not_equivalent(self):
        l = l10n.Localization("es_ES")
        self.assertFalse(l.equivalent(language="eng"))
        self.assertFalse(l.equivalent(language="en"))
        self.assertFalse(l.equivalent(language="en", country="US"))
        self.assertFalse(l.equivalent(language="en", country="United States"))
        self.assertFalse(l.equivalent(language="en", country="ES"))
        self.assertFalse(l.equivalent(language="en", country="Spain"))

    @patch("locale.getdefaultlocale")
    def test_default(self, getdefaultlocale):
        getdefaultlocale.return_value = (None, None)
        l = l10n.Localization()
        self.assertEqual("en_US", l.language_code)
        self.assertTrue(l.equivalent(language="en", country="US"))

    def test_get_country(self):
        self.assertEqual("US",
                         l10n.Localization.get_country("USA").alpha2)
        self.assertEqual("GB",
                         l10n.Localization.get_country("GB").alpha2)
        self.assertEqual("United States",
                         l10n.Localization.get_country("United States").name)

    def test_get_country_miss(self):
        self.assertRaises(LookupError, l10n.Localization.get_country, "XE")
        self.assertRaises(LookupError, l10n.Localization.get_country, "XEX")
        self.assertRaises(LookupError, l10n.Localization.get_country, "Nowhere")

    def test_get_language(self):
        self.assertEqual("eng",
                         l10n.Localization.get_language("en").alpha3)
        self.assertEqual("fre",
                         l10n.Localization.get_language("fra").bibliographic)
        self.assertEqual("fra",
                         l10n.Localization.get_language("fre").alpha3)
        self.assertEqual("gre",
                         l10n.Localization.get_language("gre").bibliographic)

    def test_get_language_miss(self):
        self.assertRaises(LookupError, l10n.Localization.get_language, "00")
        self.assertRaises(LookupError, l10n.Localization.get_language, "000")
        self.assertRaises(LookupError, l10n.Localization.get_language, "0000")

    def test_country_compare(self):
        a = l10n.Country("AA", "AAA", "001", "Test")
        b = l10n.Country("AA", "AAA", "001", "Test")
        self.assertEqual(a, b)

    def test_language_compare(self):
        a = l10n.Language("AA", "AAA", "Test")
        b = l10n.Language("AA", None, "Test")
        self.assertEqual(a, b)

        a = l10n.Language("BB", "BBB", "Test")
        b = l10n.Language("AA", None, "Test")
        self.assertNotEqual(a, b)
