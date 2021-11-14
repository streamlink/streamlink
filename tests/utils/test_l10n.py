import unittest
from unittest.mock import patch

import streamlink.utils.l10n as l10n


class TestLocalization(unittest.TestCase):
    def test_language_code_us(self):
        locale = l10n.Localization("en_US")
        self.assertEqual("en_US", locale.language_code)

    def test_language_code_kr(self):
        locale = l10n.Localization("ko_KR")
        self.assertEqual("ko_KR", locale.language_code)

    def test_bad_language_code(self):
        self.assertRaises(LookupError, l10n.Localization, "enUS")

    def test_equivalent(self):
        locale = l10n.Localization("en_CA")
        self.assertTrue(locale.equivalent(language="eng"))
        self.assertTrue(locale.equivalent(language="en"))
        self.assertTrue(locale.equivalent(language="en", country="CA"))
        self.assertTrue(locale.equivalent(language="en", country="CAN"))
        self.assertTrue(locale.equivalent(language="en", country="Canada"))

    def test_equivalent_remap(self):
        locale = l10n.Localization("fr_FR")
        self.assertTrue(locale.equivalent(language="fra"))
        self.assertTrue(locale.equivalent(language="fre"))

    def test_not_equivalent(self):
        locale = l10n.Localization("es_ES")
        self.assertFalse(locale.equivalent(language="eng"))
        self.assertFalse(locale.equivalent(language="en"))
        self.assertFalse(locale.equivalent(language="en", country="US"))
        self.assertFalse(locale.equivalent(language="en", country="Canada"))
        self.assertFalse(locale.equivalent(language="en", country="ES"))
        self.assertFalse(locale.equivalent(language="en", country="Spain"))

    @patch("locale.getdefaultlocale")
    def test_default(self, getdefaultlocale):
        getdefaultlocale.return_value = (None, None)
        locale = l10n.Localization()
        self.assertEqual("en_US", locale.language_code)
        self.assertTrue(locale.equivalent(language="en", country="US"))

    @patch("locale.getdefaultlocale")
    def test_default_invalid(self, getdefaultlocale):
        getdefaultlocale.return_value = ("en_150", None)
        locale = l10n.Localization()
        self.assertEqual("en_US", locale.language_code)
        self.assertTrue(locale.equivalent(language="en", country="US"))

    def test_get_country(self):
        self.assertEqual("US",
                         l10n.Localization.get_country("USA").alpha2)
        self.assertEqual("GB",
                         l10n.Localization.get_country("GB").alpha2)
        self.assertEqual("Canada",
                         l10n.Localization.get_country("Canada").name)

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

    # issue #3517: language lookups without alpha2 but with alpha3 codes should not raise
    def test_language_a3_no_a2(self):
        a = l10n.Localization.get_language("des")
        self.assertEqual(a.alpha2, "")
        self.assertEqual(a.alpha3, "des")
        self.assertEqual(a.name, "Desano")
        self.assertEqual(a.bibliographic, "")

    # issue #3057: generic "en" lookups via pycountry yield the "En" language, but not "English"
    def test_language_en(self):
        english_a = l10n.Localization.get_language("en")
        english_b = l10n.Localization.get_language("eng")
        english_c = l10n.Localization.get_language("English")
        for lang in [english_a, english_b, english_c]:
            self.assertEqual(lang.alpha2, "en")
            self.assertEqual(lang.alpha3, "eng")
            self.assertEqual(lang.name, "English")
            self.assertEqual(lang.bibliographic, "")
