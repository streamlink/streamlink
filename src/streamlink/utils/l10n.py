import locale
import logging
import re


try:
    from iso639 import languages
    from iso3166 import countries

    PYCOUNTRY = False
except ImportError:  # pragma: no cover
    from pycountry import languages, countries

    PYCOUNTRY = True

DEFAULT_LANGUAGE = "en"
DEFAULT_COUNTRY = "US"
DEFAULT_LANGUAGE_CODE = "{0}_{1}".format(DEFAULT_LANGUAGE, DEFAULT_COUNTRY)

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
            if PYCOUNTRY:
                c = countries.lookup(country)
                return Country(c.alpha_2, c.alpha_3, c.numeric, c.name, getattr(c, "official_name", c.name))
            else:
                c = countries.get(country)
                return Country(c.alpha2, c.alpha3, c.numeric, c.name, c.apolitical_name)
        except (LookupError, KeyError):
            raise LookupError("Invalid country code: {0}".format(country))

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
            self.official_name
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
            if PYCOUNTRY:
                # lookup workaround for alpha_2 language codes
                lang = languages.get(alpha_2=language) if re.match(r"^[a-z]{2}$", language) else languages.lookup(language)
                return Language(lang.alpha_2, lang.alpha_3, lang.name, getattr(lang, "bibliographic", None))
            else:
                lang = None
                if len(language) == 2:
                    lang = languages.get(alpha2=language)
                elif len(language) == 3:
                    for code_type in ['part2b', 'part2t', 'part3']:
                        try:
                            lang = languages.get(**{code_type: language})
                            break
                        except KeyError:
                            pass
                    if not lang:
                        raise KeyError(language)
                else:
                    raise KeyError(language)
                return Language(lang.alpha2, lang.part3, lang.name, lang.part2b or lang.part2t)
        except (LookupError, KeyError):
            raise LookupError("Invalid language code: {0}".format(language))

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
            self.bibliographic
        )


class Localization:
    def __init__(self, language_code=None):
        self._language_code = None
        self.country = None
        self.language = None
        self.explicit = bool(language_code)
        self.language_code = language_code

    @property
    def language_code(self):
        return self._language_code

    def _parse_locale_code(self, language_code):
        parts = language_code.split("_", 1)
        if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2:
            raise LookupError("Invalid language code: {0}".format(language_code))
        return self.get_language(parts[0]), self.get_country(parts[1])

    @language_code.setter
    def language_code(self, language_code):
        is_system_locale = language_code is None
        if language_code is None:
            try:
                language_code, _ = locale.getdefaultlocale()
            except ValueError:
                language_code = None
            if language_code is None or language_code == "C":
                # cannot be determined
                language_code = DEFAULT_LANGUAGE_CODE

        try:
            self.language, self.country = self._parse_locale_code(language_code)
            self._language_code = language_code
        except LookupError:
            if is_system_locale:
                # If the system locale returns an invalid code, use the default
                self.language = self.get_language(DEFAULT_LANGUAGE)
                self.country = self.get_country(DEFAULT_COUNTRY)
                self._language_code = DEFAULT_LANGUAGE_CODE
            else:
                raise
        log.debug("Language code: {0}".format(self._language_code))

    def equivalent(self, language=None, country=None):
        equivalent = True
        try:
            equivalent = equivalent and (not language or self.language == self.get_language(language))
            equivalent = equivalent and (not country or self.country == self.get_country(country))
        except LookupError:
            # if an unknown language/country code is given they cannot equivalent
            return False

        return equivalent

    @classmethod
    def get_country(cls, country):
        return Country.get(country)

    @classmethod
    def get_language(cls, language):
        return Language.get(language)
