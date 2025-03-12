from __future__ import annotations

import locale
import logging
from warnings import catch_warnings

from pycountry import countries, languages  # type: ignore[import]


DEFAULT_LANGUAGE = "en"
DEFAULT_COUNTRY = "US"
DEFAULT_LANGUAGE_CODE = f"{DEFAULT_LANGUAGE}_{DEFAULT_COUNTRY}"

log = logging.getLogger(__name__)


class Country:
    def __init__(self, alpha2, alpha3, numeric, name, official_name=None):
        self.alpha2 = alpha2
        self.alpha3 = alpha3
        self.numeric = numeric
        self.name = name
        self.official_name = official_name

    @classmethod
    def get(cls, country):
        try:
            c = countries.lookup(country)

            # changed in pycountry 23.12.11: a UserWarning is emitted when the official_name is missing
            with catch_warnings(record=True):
                official_name = getattr(c, "official_name", c.name)

            return Country(
                c.alpha_2,
                c.alpha_3,
                c.numeric,
                c.name,
                official_name=official_name,
            )
        except LookupError as err:
            raise LookupError(f"Invalid country code: {country}") from err

    def __hash__(self):
        return hash((self.alpha2, self.alpha3, self.numeric, self.name, self.official_name))

    def __eq__(self, other):
        return (
            (self.alpha2 and self.alpha2 == other.alpha2)
            or (self.alpha3 and self.alpha3 == other.alpha3)
            or (self.numeric and self.numeric == other.numeric)
        )

    def __str__(self):
        return "Country({0!r}, {1!r}, {2!r}, {3!r}, official_name={4!r})".format(
            self.alpha2,
            self.alpha3,
            self.numeric,
            self.name,
            self.official_name,
        )


class Language:
    def __init__(self, alpha2, alpha3, name, bibliographic=None):
        self.alpha2 = alpha2
        self.alpha3 = alpha3
        self.name = name
        self.bibliographic = bibliographic

    @classmethod
    def get(cls, language):
        try:
            lang = (
                languages.get(alpha_2=language)
                or languages.get(alpha_3=language)
                or languages.get(bibliographic=language)
                or languages.get(name=language)
            )
            if not lang:
                raise KeyError(language)
            return Language(
                # some languages don't have an alpha_2 code
                getattr(lang, "alpha_2", ""),
                lang.alpha_3,
                lang.name,
                getattr(lang, "bibliographic", ""),
            )
        except LookupError as err:
            raise LookupError(f"Invalid language code: {language}") from err

    def __hash__(self):
        return hash((self.alpha2, self.alpha3, self.name, self.bibliographic))

    def __eq__(self, other):
        return (
            (self.alpha2 and self.alpha2 == other.alpha2)
            or (self.alpha3 and self.alpha3 == other.alpha3)
            or (self.bibliographic and self.bibliographic == other.bibliographic)
        )

    def __str__(self):
        return "Language({0!r}, {1!r}, {2!r}, bibliographic={3!r})".format(
            self.alpha2,
            self.alpha3,
            self.name,
            self.bibliographic,
        )


class Localization:
    def __init__(self, language_code=None):
        self._language_code = None
        self.country = None
        self.language = None
        self.explicit = bool(language_code)
        self._set_language_code(language_code)

    @property
    def language_code(self):
        return self._language_code

    @language_code.setter
    def language_code(self, language_code):
        self._set_language_code(language_code)

    def _parse_locale_code(self, language_code):
        parts = language_code.split("_", 1)
        if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2:
            raise LookupError(f"Invalid language code: {language_code}")
        return self.get_language(parts[0]), self.get_country(parts[1])

    def _set_language_code(self, language_code):
        is_system_locale = language_code is None
        if is_system_locale:
            try:
                language_code, _ = locale.getlocale()
            except ValueError:
                language_code = None
            if language_code is None or language_code == "C":
                # cannot be determined
                language_code = DEFAULT_LANGUAGE_CODE

        try:
            self.language, self.country = self._parse_locale_code(language_code)
            self._language_code = language_code
        except LookupError:
            if not is_system_locale:
                raise
            # If the system locale returns an invalid code, use the default
            self.language = self.get_language(DEFAULT_LANGUAGE)
            self.country = self.get_country(DEFAULT_COUNTRY)
            self._language_code = DEFAULT_LANGUAGE_CODE
        log.debug(f"Language code: {self._language_code}")

    def equivalent(
        self,
        language: Language | str | None = None,
        country: Country | str | None = None,
    ) -> bool:
        try:
            return (
                (
                    not language
                    or isinstance(language, Language) and self.language == language
                    or self.language == self.get_language(language)
                )
                and (
                    not country
                    or isinstance(country, Country) and self.country == country
                    or self.country == self.get_country(country)
                )
            )  # fmt: skip
        except LookupError:
            # if an unknown language/country code is given, they cannot be equivalent
            return False

    @classmethod
    def get_country(cls, country):
        return Country.get(country)

    @classmethod
    def get_language(cls, language):
        return Language.get(language)
