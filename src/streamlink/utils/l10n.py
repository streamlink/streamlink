import locale
from iso639 import languages
from iso3166 import countries

DEFAULT_LANGUAGE_CODE = "en_US"


class Localization(object):
    language_code_remap = {
        "fre": "fra"
    }

    def __init__(self, language_code=None):
        self._language_code = None
        self.country = None
        self.language = None
        self.explicit = bool(language_code)
        self.language_code = language_code

    @property
    def language_code(self):
        return self._language_code

    @language_code.setter
    def language_code(self, language_code):
        if language_code is None:
            language_code, _ = locale.getdefaultlocale()
            if language_code is None or language_code == "C":
                # cannot be determined
                language_code = DEFAULT_LANGUAGE_CODE

        parts = language_code.split("_", 1)

        if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2:
            raise ValueError("Invalid language code: {0}".format(language_code))

        self._language_code = language_code
        self.language = self.get_language(parts[0])
        self.country = self.get_country(parts[1])

    def equivalent(self, language=None, country=None):
        equivalent = True
        equivalent = equivalent and (not language or self.language == self.get_language(language))
        equivalent = equivalent and (not country or self.country == self.get_country(country))

        return equivalent

    @classmethod
    def get_country(cls, country):
        try:
            return countries.get(country)
        except KeyError:
            raise ValueError("Invalid country code: {0}".format(country))

    @classmethod
    def get_language(cls, language):
        # some language codes need to be remapped. why? because standards were designed to be broken.
        _language = cls.language_code_remap.get(language, language)
        try:
            if len(_language) == 2:
                return languages.get(alpha2=_language)
            elif len(_language) == 3:
                return languages.get(part3=_language)
            else:
                raise ValueError("Invalid language code: {0}".format(language))
        except KeyError:
            raise ValueError("Invalid language code: {0}".format(language))
