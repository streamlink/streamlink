from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

from lxml.etree import XPathError, iselement

from streamlink.plugin.api.validate._exception import ValidationError
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
        if len(value) < number:
            raise ValidationError(
                "Minimum length is {number}, but value is {value}",
                number=repr(number),
                value=len(value),
                schema="length",
            )

        return True

    return min_len


def validator_startswith(string: str) -> Callable[[str], bool]:
    """
    Check if the input string starts with another string.
    """

    def starts_with(value):
        validate(str, value)
        if not value.startswith(string):
            raise ValidationError(
                "{value} does not start with {string}",
                value=repr(value),
                string=repr(string),
                schema="startswith",
            )

        return True

    return starts_with


def validator_endswith(string: str) -> Callable[[str], bool]:
    """
    Check if the input string ends with another string.
    """

    def ends_with(value):
        validate(str, value)
        if not value.endswith(string):
            raise ValidationError(
                "{value} does not end with {string}",
                value=repr(value),
                string=repr(string),
                schema="endswith",
            )

        return True

    return ends_with


def validator_contains(string: str) -> Callable[[str], bool]:
    """
    Check if the input string contains another string.
    """

    def contains_str(value):
        validate(str, value)
        if string not in value:
            raise ValidationError(
                "{value} does not contain {string}",
                value=repr(value),
                string=repr(string),
                schema="contains",
            )

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
            raise ValidationError(
                "{value} is not a valid URL",
                value=repr(value),
                schema="url",
            )

        for name, schema in attributes.items():
            if not hasattr(parsed, name):
                raise ValidationError(
                    "Invalid URL attribute {name}",
                    name=repr(name),
                    schema="url",
                )

            try:
                validate(schema, getattr(parsed, name))
            except ValidationError as err:
                raise ValidationError(
                    "Unable to validate URL attribute {name}",
                    name=repr(name),
                    schema="url",
                ) from err

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


def validator_filter(func: Callable[..., bool]) -> TransformSchema:
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


def validator_map(func: Callable[..., Any]) -> TransformSchema:
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


def validator_xml_find(
    path: str,
    namespaces: Optional[Dict[str, str]] = None,
) -> TransformSchema:
    """
    Find an XML element (:meth:`Element.find`).
    This method uses the ElementPath query language, which is a subset of XPath.
    """

    def xpath_find(value):
        validate(iselement, value)

        try:
            value = value.find(path, namespaces=namespaces)
        except SyntaxError as err:
            raise ValidationError(
                "ElementPath syntax error: {path}",
                path=repr(path),
                schema="xml_find",
            ) from err

        if value is None:
            raise ValidationError(
                "ElementPath query {path} did not return an element",
                path=repr(path),
                schema="xml_find",
            )

        return value

    return TransformSchema(xpath_find)


def validator_xml_findall(
    path: str,
    namespaces: Optional[Dict[str, str]] = None,
) -> TransformSchema:
    """
    Find a list of XML elements (:meth:`Element.findall`).
    This method uses the ElementPath query language, which is a subset of XPath.
    """

    def xpath_findall(value):
        validate(iselement, value)
        return value.findall(path, namespaces=namespaces)

    return TransformSchema(xpath_findall)


def validator_xml_findtext(
    path: str,
    namespaces: Optional[Dict[str, str]] = None,
) -> AllSchema:
    """
    Find an XML element (:meth:`Element.find`) and return its text.
    This method uses the ElementPath query language, which is a subset of XPath.
    """

    return AllSchema(
        validator_xml_find(path, namespaces=namespaces),
        validator_getattr("text"),
    )


def validator_xml_xpath(
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None,
    extensions: Optional[Dict[Tuple[Optional[str], str], Callable[..., Any]]] = None,
    smart_strings: bool = True,
    **variables,
) -> TransformSchema:
    """
    Query XML elements via XPath (:meth:`Element.xpath`) and return None if the result is falsy.
    """

    def transform_xpath(value):
        validate(iselement, value)
        try:
            result = value.xpath(
                xpath,
                namespaces=namespaces,
                extensions=extensions,
                smart_strings=smart_strings,
                **variables,
            )
        except XPathError as err:
            raise ValidationError(
                "XPath evaluation error: {xpath}",
                xpath=repr(xpath),
                schema="xml_xpath",
            ) from err

        return result or None

    return TransformSchema(transform_xpath)


def validator_xml_xpath_string(
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None,
    extensions: Optional[Dict[Tuple[Optional[str], str], Callable[..., Any]]] = None,
    **variables,
) -> TransformSchema:
    """
    Query XML elements via XPath (:meth:`Element.xpath`),
    transform the result into a string and return None if the result is falsy.
    """

    return validator_xml_xpath(
        f"string({xpath})",
        namespaces=namespaces,
        extensions=extensions,
        smart_strings=False,
        **variables,
    )


# Parse utility related validators


def validator_parse_json(*args, **kwargs) -> TransformSchema:
    """
    Parse JSON data via the :func:`streamlink.utils.parse.parse_json` utility function.
    """

    return TransformSchema(_parse_json, *args, **kwargs, exception=ValidationError, schema=None)


def validator_parse_html(*args, **kwargs) -> TransformSchema:
    """
    Parse HTML data via the :func:`streamlink.utils.parse.parse_html` utility function.
    """

    return TransformSchema(_parse_html, *args, **kwargs, exception=ValidationError, schema=None)


def validator_parse_xml(*args, **kwargs) -> TransformSchema:
    """
    Parse XML data via the :func:`streamlink.utils.parse.parse_xml` utility function.
    """

    return TransformSchema(_parse_xml, *args, **kwargs, exception=ValidationError, schema=None)


def validator_parse_qsd(*args, **kwargs) -> TransformSchema:
    """
    Parse a query string via the :func:`streamlink.utils.parse.parse_qsd` utility function.
    """

    return TransformSchema(_parse_qsd, *args, **kwargs, exception=ValidationError, schema=None)
