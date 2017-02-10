from tests.test_localization import TestLocalization
import streamlink.utils.l10n as l10n


class TestLocalizationPyCountry(TestLocalization):
    """Duplicate of all the Localization tests but using PyCountry instead of the iso* modules"""

    def setUp(self):
        from pycountry import languages, countries
        l10n.countries = countries
        l10n.languages = languages
        l10n.PYCOUNTRY = True

    def test_pycountry(self):
        self.assertEqual(True, l10n.PYCOUNTRY)
