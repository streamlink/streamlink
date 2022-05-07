from typing import Any, Callable
from urllib.parse import urlparse

from lxml.etree import iselement

from streamlink.plugin.api.validate._schemas import AllSchema, AnySchema, TransformSchema
from streamlink.plugin.api.validate._validate import validate
from streamlink.utils.parse import (
    parse_html as _parse_html,
    parse_json as _parse_json,
    parse_qsd as _parse_qsd,
    parse_xml as _parse_xml,
)


# String related validators

def validator_length(number: int) -> Callable[[str], bool]:
    """
    Check input for minimum length using len().
    """

    def min_len(value):
        if not len(value) >= number:
            raise ValueError(f"Minimum length is {number} but value is {len(value)}")

        return True

    return min_len


def validator_startswith(string: str) -> Callable[[str], bool]:
    """
    Check if the input string starts with another string.
    """

    def starts_with(value):
        validate(str, value)
        if not value.startswith(string):
            raise ValueError(f"'{value}' does not start with '{string}'")

        return True

    return starts_with


def validator_endswith(string: str) -> Callable[[str], bool]:
    """
    Check if the input string ends with another string.
    """

    def ends_with(value):
        validate(str, value)
        if not value.endswith(string):
            raise ValueError(f"'{value}' does not end with '{string}'")

        return True

    return ends_with


def validator_contains(string: str) -> Callable[[str], bool]:
    """
    Check if the input string contains another string.
    """

    def contains_str(value):
        validate(str, value)
        if string not in value:
            raise ValueError(f"'{value}' does not contain '{string}'")

        return True

    return contains_str


def validator_url(**attributes) -> Callable[[str], bool]:
    """
    Parse a URL and validate its attributes using sub-schemas.
    """

    # Convert "http" to AnySchema("http", "https") for convenience
    if attributes.get("scheme") == "http":
        attributes["scheme"] = AnySchema("http", "https")

    def check_url(value):
        validate(str, value)
        parsed = urlparse(value)
        if not parsed.netloc:
            raise ValueError(f"'{value}' is not a valid URL")

        for name, schema in attributes.items():
            if not hasattr(parsed, name):
                raise ValueError(f"Invalid URL attribute '{name}'")

            try:
                validate(schema, getattr(parsed, name))
            except ValueError as err:
                raise ValueError(f"Unable to validate URL attribute '{name}': {err}")

        return True

    return check_url


# Object related validators


def validator_getattr(attr: Any, default: Any = None) -> TransformSchema:
    """
    Get a named attribute from the input object.

    If a default is set, it is returned when the attribute doesn't exist.
    """

    def getter(value):
        return getattr(value, attr, default)

    return TransformSchema(getter)


def validator_hasattr(attr: Any) -> Callable[[Any], bool]:
    """
    Verify that the input object has an attribute with the given name.
    """

    def getter(value):
        return hasattr(value, attr)

    return getter


# Sequence related validators


def validator_filter(func: Callable[[Any], bool]) -> TransformSchema:
    """
    Filter out unwanted items from the input using the specified function.

    Supports both dicts and sequences. key/value pairs are expanded when applied to a dict.
    """

    def expand_kv(kv):
        return func(*kv)

    def filter_values(value):
        cls = type(value)
        if isinstance(value, dict):
            return cls(filter(expand_kv, value.items()))
        else:
            return cls(filter(func, value))

    return TransformSchema(filter_values)


def validator_map(func: Callable[[Any], Any]) -> TransformSchema:
    """
    Transform items from the input using the specified function.

    Supports both dicts and sequences. key/value pairs are expanded when applied to a dict.
    """

    def expand_kv(kv):
        return func(*kv)

    def map_values(value):
        cls = type(value)
        if isinstance(value, dict):
            return cls(map(expand_kv, value.items()))
        else:
            return cls(map(func, value))

    return TransformSchema(map_values)


# lxml.etree related validators


def validator_xml_find(xpath: str) -> TransformSchema:
    """
    Find an XML element via xpath (:meth:`Element.find`).
    """

    def xpath_find(value):
        validate(iselement, value)
        value = value.find(xpath)
        if value is None:
            raise ValueError(f"XPath '{xpath}' did not return an element")

        return validate(iselement, value)

    return TransformSchema(xpath_find)


def validator_xml_findall(xpath) -> TransformSchema:
    """
    Find a list of XML elements via xpath.
    """

    def xpath_findall(value):
        validate(iselement, value)
        return value.findall(xpath)

    return TransformSchema(xpath_findall)


def validator_xml_findtext(xpath) -> AllSchema:
    """
    Find an XML element via xpath and extract its text.
    """

    return AllSchema(
        validator_xml_find(xpath),
        validator_getattr("text"),
    )


def validator_xml_xpath(xpath) -> TransformSchema:
    """
    Query XML elements via xpath (:meth:`Element.xpath`) and return None if the result is falsy.
    """

    def transform_xpath(value):
        validate(iselement, value)
        return value.xpath(xpath) or None

    return TransformSchema(transform_xpath)


def validator_xml_xpath_string(xpath) -> TransformSchema:
    """
    Query XML elements via xpath (:meth:`Element.xpath`),
    transform the result into a string and return None if the result is falsy.
    """

    return validator_xml_xpath(f"string({xpath})")


# Parse utility related validators


def validator_parse_json(*args, **kwargs) -> TransformSchema:
    """
    Parse JSON data via the :func:`streamlink.utils.parse.parse_json` utility function.
    """

    return TransformSchema(_parse_json, *args, **kwargs, exception=ValueError, schema=None)


def validator_parse_html(*args, **kwargs) -> TransformSchema:
    """
    Parse HTML data via the :func:`streamlink.utils.parse.parse_html` utility function.
    """

    return TransformSchema(_parse_html, *args, **kwargs, exception=ValueError, schema=None)


def validator_parse_xml(*args, **kwargs) -> TransformSchema:
    """
    Parse XML data via the :func:`streamlink.utils.parse.parse_xml` utility function.
    """

    return TransformSchema(_parse_xml, *args, **kwargs, exception=ValueError, schema=None)


def validator_parse_qsd(*args, **kwargs) -> TransformSchema:
    """
    Parse a query string via the :func:`streamlink.utils.parse.parse_qsd` utility function.
    """

    return TransformSchema(_parse_qsd, *args, **kwargs, exception=ValueError, schema=None)
