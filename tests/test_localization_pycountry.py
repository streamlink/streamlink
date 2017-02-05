from tests.test_localization import TestLocalization
import streamlink.utils.l10n as l10n

from pycountry import languages, countries
l10n.countries = countries
l10n.languages = languages
l10n.PYCOUNTRY = True


class TestLocalizationPyCountry(TestLocalization):
    """Duplicate of all the Localization tests but using PyCountry instead of the iso* modules"""
    pass
