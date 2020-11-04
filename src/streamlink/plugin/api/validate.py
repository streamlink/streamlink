"""This module provides an API to validate and to some extent
   manipulate data structures, such as JSON and XML parsing results.


   Example usage:

   >>> validate(int, 5)
   5

   >>> validate({text: int}, {'foo': '1'})
   ValueError: Type of '1' should be 'int' but is 'str'

   >>> validate({'foo': transform(int)}, {'foo': '1'})
   {'foo': 1}

"""


from copy import copy as copy_obj
from functools import singledispatch
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from streamlink.exceptions import PluginError

__all__ = [
    "any", "all", "filter", "get", "getattr", "hasattr", "length", "optional",
    "transform", "text", "union", "url", "startswith", "endswith", "contains",
    "xml_element", "xml_find", "xml_findall", "xml_findtext",
    "validate", "Schema", "SchemaContainer"
]

text = str

# References to original functions that we override in this module
_all = all
_getattr = getattr
_hasattr = hasattr
_filter = filter
_map = map


_re_match_attr = ("group", "groups", "groupdict", "re")


def _is_re_match(value):
    return _all(_hasattr(value, a) for a in _re_match_attr)


class any(tuple):
    """At least one of the schemas must be valid."""
    def __new__(cls, *args):
        return super().__new__(cls, args)


class all(tuple):
    """All schemas must be valid."""
    def __new__(cls, *args):
        return super().__new__(cls, args)


class SchemaContainer:
    def __init__(self, schema):
        self.schema = schema


class transform:
    """Applies function to value to transform it."""

    def __init__(self, func):
        self.func = func


class optional:
    """An optional key used in a dict or union-dict."""

    def __init__(self, key):
        self.key = key


class union(SchemaContainer):
    """Extracts multiple validations based on the same value."""


class attr(SchemaContainer):
    """Validates an object's attributes."""


class xml_element:
    """A XML element."""

    def __init__(self, tag=None, text=None, attrib=None):
        self.tag = tag
        self.text = text
        self.attrib = attrib


def length(length):
    """Checks value for minimum length using len()."""
    def min_len(value):
        if not len(value) >= length:
            raise ValueError(
                "Minimum length is {0} but value is {1}".format(length, len(value))
            )
        return True

    return min_len


def startswith(string):
    """Checks if the string value starts with another string."""
    def starts_with(value):
        validate(text, value)
        if not value.startswith(string):
            raise ValueError("'{0}' does not start with '{1}'".format(value, string))
        return True

    return starts_with


def endswith(string):
    """Checks if the string value ends with another string."""
    def ends_with(value):
        validate(text, value)
        if not value.endswith(string):
            raise ValueError("'{0}' does not end with '{1}'".format(value, string))
        return True

    return ends_with


def contains(string):
    """Checks if the string value contains another string."""
    def contains_str(value):
        validate(text, value)
        if string not in value:
            raise ValueError("'{0}' does not contain '{1}'".format(value, string))
        return True

    return contains_str


def get(item, default=None):
    """Get item from value (value[item]).

    If the item is not found, return the default.

    Handles XML elements, regex matches and anything that has __getitem__.
    """

    def getter(value):
        if ET.iselement(value):
            value = value.attrib

        try:
            # Use .group() if this is a regex match object
            if _is_re_match(value):
                return value.group(item)
            else:
                return value[item]
        except (KeyError, IndexError):
            return default
        except (TypeError, AttributeError) as err:
            raise ValueError(err)

    return transform(getter)


def getattr(attr, default=None):
    """Get a named attribute from an object.

    When a default argument is given, it is returned when the attribute
    doesn't exist.
    """
    def getter(value):
        return _getattr(value, attr, default)

    return transform(getter)


def hasattr(attr):
    """Verifies that the object has an attribute with the given name."""
    def has_attr(value):
        return _hasattr(value, attr)

    return has_attr


def filter(func):
    """Filters out unwanted items using the specified function.

    Supports both dicts and sequences, key/value pairs are
    expanded when applied to a dict.
    """
    def expand_kv(kv):
        return func(*kv)

    def filter_values(value):
        cls = type(value)
        if isinstance(value, dict):
            return cls(_filter(expand_kv, value.items()))
        else:
            return cls(_filter(func, value))

    return transform(filter_values)


def map(func):
    """Apply function to each value inside the sequence or dict.

    Supports both dicts and sequences, key/value pairs are
    expanded when applied to a dict.
    """
    def expand_kv(kv):
        return func(*kv)

    def map_values(value):
        cls = type(value)
        if isinstance(value, dict):
            return cls(_map(expand_kv, value.items()))
        else:
            return cls(_map(func, value))

    return transform(map_values)


def url(**attributes):
    """Parses an URL and validates its attributes."""
    def check_url(value):
        validate(text, value)
        parsed = urlparse(value)
        if not parsed.netloc:
            raise ValueError("'{0}' is not a valid URL".format(value))

        for name, schema in attributes.items():
            if not _hasattr(parsed, name):
                raise ValueError("Invalid URL attribute '{0}'".format(name))

            try:
                validate(schema, _getattr(parsed, name))
            except ValueError as err:
                raise ValueError(
                    "Unable to validate URL attribute '{0}': {1}".format(
                        name, err
                    )
                )

        return True

    # Convert "http" to be either any("http", "https") for convenience
    if attributes.get("scheme") == "http":
        attributes["scheme"] = any("http", "https")

    return check_url


def xml_find(xpath):
    """Find a XML element via xpath."""
    def xpath_find(value):
        validate(ET.iselement, value)
        value = value.find(xpath)
        if value is None:
            raise ValueError("XPath '{0}' did not return an element".format(xpath))

        return validate(ET.iselement, value)

    return transform(xpath_find)


def xml_findall(xpath):
    """Find a list of XML elements via xpath."""
    def xpath_findall(value):
        validate(ET.iselement, value)
        return value.findall(xpath)

    return transform(xpath_findall)


def xml_findtext(xpath):
    """Find a XML element via xpath and extract its text."""
    return all(
        xml_find(xpath),
        getattr("text"),
    )


@singledispatch
def validate(schema, value):
    if callable(schema):
        if schema(value):
            return value
        else:
            raise ValueError("{0}({1!r}) is not true".format(schema.__name__, value))

    if schema == value:
        return value
    else:
        raise ValueError("{0!r} does not equal {1!r}".format(value, schema))


@validate.register(any)
def validate_any(schema, value):
    errors = []
    for subschema in schema:
        try:
            return validate(subschema, value)
        except ValueError as err:
            errors.append(err)
    else:
        err = " or ".join(_map(str, errors))
        raise ValueError(err)


@validate.register(all)
def validate_all(schemas, value):
    for schema in schemas:
        value = validate(schema, value)

    return value


@validate.register(transform)
def validate_transform(schema, value):
    validate(callable, schema.func)
    return schema.func(value)


@validate.register(list)
@validate.register(tuple)
@validate.register(set)
@validate.register(frozenset)
def validate_sequence(schema, value):
    validate(type(schema), value)
    return type(schema)(validate(any(*schema), v) for v in value)


@validate.register(dict)
def validate_dict(schema, value):
    validate(type(schema), value)
    new = type(schema)()

    for key, subschema in schema.items():
        if isinstance(key, optional):
            if key.key not in value:
                continue
            key = key.key

        if type(key) in (type, transform, any, all, union):
            for subkey, subvalue in value.items():
                new[validate(key, subkey)] = validate(subschema, subvalue)
            break
        else:
            if key not in value:
                raise ValueError("Key '{0}' not found in {1!r}".format(key, value))

            try:
                new[key] = validate(subschema, value[key])
            except ValueError as err:
                raise ValueError("Unable to validate key '{0}': {1}".format(key, err))

    return new


@validate.register(type)
def validate_type(schema, value):
    if isinstance(value, schema):
        return value
    else:
        raise ValueError(
            "Type of {0!r} should be '{1}' but is '{2}'".format(
                value, schema.__name__, type(value).__name__
            )
        )


@validate.register(xml_element)
def validate_xml_element(schema, value):
    validate(ET.iselement, value)
    new = ET.Element(value.tag, attrib=value.attrib)

    if schema.attrib is not None:
        try:
            new.attrib = validate(schema.attrib, value.attrib)
        except ValueError as err:
            raise ValueError("Unable to validate XML attributes: {0}".format(err))

    if schema.tag is not None:
        try:
            new.tag = validate(schema.tag, value.tag)
        except ValueError as err:
            raise ValueError("Unable to validate XML tag: {0}".format(err))

    if schema.text is not None:
        try:
            new.text = validate(schema.text, value.text)
        except ValueError as err:
            raise ValueError("Unable to validate XML text: {0}".format(err))

    for child in value:
        new.append(child)

    return new


@validate.register(attr)
def validate_attr(schema, value):
    new = copy_obj(value)

    for attr, schema in schema.schema.items():
        if not _hasattr(value, attr):
            raise ValueError("Attribute '{0}' not found on object '{1}'".format(
                attr, value
            ))

        setattr(new, attr, validate(schema, _getattr(value, attr)))

    return new


@singledispatch
def validate_union(schema, value):
    raise ValueError("Invalid union type: {0}".format(type(schema).__name__))


@validate_union.register(dict)
def validate_union_dict(schema, value):
    new = type(schema)()
    for key, schema in schema.items():
        optional_ = isinstance(key, optional)
        if optional_:
            key = key.key

        try:
            new[key] = validate(schema, value)
        except ValueError as err:
            if optional_:
                continue

            raise ValueError("Unable to validate union '{0}': {1}".format(key, err))

    return new


@validate_union.register(list)
@validate_union.register(tuple)
@validate_union.register(set)
@validate_union.register(frozenset)
def validate_union_sequence(schemas, value):
    return type(schemas)(validate(schema, value) for schema in schemas)


@validate.register(union)
def validate_unions(schema, value):
    return validate_union(schema.schema, value)


class Schema:
    """Wraps a validator schema into a object."""

    def __init__(self, *schemas):
        self.schema = all(*schemas)

    def validate(self, value, name="result", exception=PluginError):
        try:
            return validate(self.schema, value)
        except ValueError as err:
            raise exception("Unable to validate {0}: {1}".format(name, err))


@validate.register(Schema)
def validate_schema(schema, value):
    return schema.validate(value, exception=ValueError)
