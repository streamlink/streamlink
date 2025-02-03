from __future__ import annotations

import operator
from collections.abc import Callable, Container, Mapping
from typing import Any, Literal
from urllib.parse import urlparse

from lxml.etree import XPathError, iselement

from streamlink.utils.parse import (
    parse_html as _parse_html,
    parse_json as _parse_json,
    parse_qsd as _parse_qsd,
    parse_xml as _parse_xml,
)
from streamlink.validate._exception import ValidationError
from streamlink.validate._schemas import AllSchema, AnySchema, TransformSchema
from streamlink.validate._validate import validate


# String related validators

_validator_length_ops: Mapping[str, tuple[Callable, str]] = {
    "lt": (operator.lt, "Length must be <{number}, but value is {value}"),
    "le": (operator.le, "Length must be <={number}, but value is {value}"),
    "eq": (operator.eq, "Length must be =={number}, but value is {value}"),
    "ge": (operator.ge, "Length must be >={number}, but value is {value}"),
    "gt": (operator.gt, "Length must be >{number}, but value is {value}"),
}


def validator_length(
    number: int,
    op: Literal["lt", "le", "eq", "ge", "gt"] = "ge",
) -> Callable[[str], bool]:
    """
    Utility function for checking whether the input has a certain length, by using :func:`len()`.
    Checks the minimum length by default (``op="ge"``).

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.length(3),
        )
        assert schema.validate("abc") == "abc"
        assert schema.validate([1, 2, 3, 4]) == [1, 2, 3, 4]
        schema.validate("a")  # raises ValidationError
        schema.validate([1])  # raises ValidationError

    .. code-block:: python

        schema = validate.Schema(
            validate.length(3, op="lt"),
        )
        assert schema.validate("ab") == "ab"
        schema.validate([1, 2, 3])  # raises ValidationError
    """

    def length(value):
        func, msg = _validator_length_ops.get(op, "ge")
        if not func(len(value), number):
            raise ValidationError(
                msg,
                number=repr(number),
                value=len(value),
                schema="length",
            )

        return True

    return length


def validator_startswith(string: str) -> Callable[[str], bool]:
    """
    Utility function for checking whether the input string starts with another string.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.startswith("1"),
        )
        assert schema.validate("123") == "123"
        schema.validate("321")  # raises ValidationError
        schema.validate(None)  # raises ValidationError

    :raise ValidationError: If input is not an instance of :class:`str`
    :raise ValidationError: If input doesn't start with ``string``
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
    Utility function for checking whether the input string ends with another string.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.endswith("3"),
        )
        assert schema.validate("123") == "123"
        schema.validate("321")  # raises ValidationError
        schema.validate(None)  # raises ValidationError

    :raise ValidationError: If input is not an instance of :class:`str`
    :raise ValidationError: If input doesn't end with ``string``
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


def validator_contains(obj: object) -> Callable[[Container], bool]:
    """
    Utility function for checking whether the input contains a certain element,
    e.g. a string within a string, an object in a list, a key in a dict, etc.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.contains("456"),
        )
        assert schema.validate("123456789") == "123456789"
        schema.validate("987654321")  # raises ValidationError
        schema.validate(None)  # raises ValidationError

    .. code-block:: python

        schema = validate.Schema(
            validate.contains(456),
        )
        assert schema.validate([123, 456, 789]) == [123, 456, 789]
        schema.validate([987, 654, 321])  # raises ValidationError
        schema.validate(None)  # raises ValidationError

    :raise ValidationError: If input is not an instance of :class:`collections.abc.Container`
    :raise ValidationError: If input doesn't contain ``obj``
    """

    def contains_str(value):
        validate(Container, value)
        if obj not in value:
            raise ValidationError(
                "{value} does not contain {obj}",
                value=repr(value),
                obj=repr(obj),
                schema="contains",
            )

        return True

    return contains_str


def validator_url(**attributes) -> Callable[[str], bool]:
    """
    Utility function for validating a URL using schemas.

    Allows validating all URL attributes returned by :func:`urllib.parse.urlparse()`:

    - ``scheme`` - updated to ``AnySchema("http", "https")`` if set to ``"http"``
    - ``netloc``
    - ``path``
    - ``params``
    - ``query``
    - ``fragment``
    - ``username``
    - ``password``
    - ``hostname``
    - ``port``

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.url(path=validate.endswith(".m3u8")),
        )
        assert schema.validate("https://host/pl.m3u8?query") == "https://host/pl.m3u8?query"
        schema.validate(None)  # raises ValidationError
        schema.validate("not a URL")  # raises ValidationError
        schema.validate("https://host/no-pl?pl.m3u8")  # raises ValidationError

    :raise ValidationError: If input is not a string
    :raise ValidationError: If input is not a URL (doesn't have a ``netloc`` parsing result)
    :raise ValidationError: If an unknown URL attribute is passed as an option
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
    Utility function for getting an attribute from the input object.

    If a default is set, it is returned when the attribute doesn't exist.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.getattr("year", "unknown"),
        )
        assert schema.validate(datetime.date.fromisoformat("2000-01-01")) == 2000
        assert schema.validate("not a date/datetime object") == "unknown"
    """

    def getter(value):
        return getattr(value, attr, default)

    return TransformSchema(getter)


def validator_hasattr(attr: Any) -> Callable[[Any], bool]:
    """
    Utility function for checking whether an attribute exists on the input object.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.hasattr("year"),
        )
        date = datetime.date.fromisoformat("2000-01-01")
        assert schema.validate(date) is date
        schema.validate("not a date/datetime object")  # raises ValidationError
    """

    def getter(value):
        return hasattr(value, attr)

    return getter


# Sequence related validators


def validator_filter(func: Callable[..., bool]) -> TransformSchema:
    """
    Utility function for filtering out unwanted items from the input using the specified function
    via the built-in :func:`filter() <builtins.filter>`.

    Supports iterables, as well as instances of :class:`dict` where key-value pairs are expanded.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.filter(lambda val: val < 3),
        )
        assert schema.validate([1, 2, 3, 4]) == [1, 2]

    .. code-block:: python

        schema = validate.Schema(
            validate.filter(lambda key, val: key > 1 and val < 3),
        )
        assert schema.validate({0: 0, 1: 1, 2: 2, 3: 3, 4: 4}) == {2: 2}
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
    Utility function for mapping/transforming items from the input using the specified function,
    via the built-in :func:`map() <builtins.map>`.

    Supports iterables, as well as instances of :class:`dict` where key-value pairs are expanded.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.map(lambda val: val + 1),
        )
        assert schema.validate([1, 2, 3, 4]) == [2, 3, 4, 5]

    .. code-block:: python

        schema = validate.Schema(
            validate.map(lambda key, val: (key + 1, val * 2)),
        )
        assert schema.validate({0: 0, 1: 1, 2: 2, 3: 3, 4: 4}) == {1: 0, 2: 2, 3: 4, 4: 6, 5: 8}
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
    namespaces: Mapping[str, str] | None = None,
) -> TransformSchema:
    """
    Utility function for finding an XML element using :meth:`Element.find()`.

    This method uses the ElementPath query language, which is a subset of XPath.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.xml_find(".//b/c"),
        )
        assert schema.validate(lxml.etree.XML("<a><b><c>d</c></b></a>")).text == "d"
        schema.validate(lxml.etree.XML("<a><b></b></a>"))  # raises ValidationError
        schema.validate("<a><b><c>d</c></b></a>")  # raises ValidationError

    :raise ValidationError: If the input is not an :class:`lxml.etree.Element`
    :raise ValidationError: On ElementPath evaluation error
    :raise ValidationError: If the query didn't return an XML element
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
    namespaces: Mapping[str, str] | None = None,
) -> TransformSchema:
    """
    Utility function for finding XML elements using :meth:`Element.findall()`.

    This method uses the ElementPath query language, which is a subset of XPath.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.xml_findall(".//b"),
            validate.map(lambda elem: elem.text),
        )
        assert schema.validate(lxml.etree.XML("<a><b>1</b><b>2</b></a>")) == ["1", "2"]
        assert schema.validate(lxml.etree.XML("<a><c></c></a>")) == []
        schema.validate("<a><b>1</b><b>2</b></a>")  # raises ValidationError

    :raise ValidationError: If the input is not an :class:`lxml.etree.Element`
    :raise ValidationError: On ElementPath evaluation error
    """

    def xpath_findall(value):
        validate(iselement, value)
        return value.findall(path, namespaces=namespaces)

    return TransformSchema(xpath_findall)


def validator_xml_findtext(
    path: str,
    namespaces: Mapping[str, str] | None = None,
) -> AllSchema:
    """
    Utility function for finding an XML element using :meth:`Element.find()` and returning its ``text`` attribute.

    This method uses the ElementPath query language, which is a subset of XPath.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.xml_findtext(".//b/c"),
        )
        assert schema.validate(lxml.etree.XML("<a><b><c>d</c></b></a>")) == "d"
        schema.validate(lxml.etree.XML("<a><b></b></a>"))  # raises ValidationError
        schema.validate("<a><b><c>d</c></b></a>")  # raises ValidationError

    :raise ValidationError: If the input is not an :class:`lxml.etree.Element`
    :raise ValidationError: On ElementPath evaluation error
    :raise ValidationError: If the query didn't return an XML element
    """

    return AllSchema(
        validator_xml_find(path, namespaces=namespaces),
        validator_getattr("text"),
    )


def validator_xml_xpath(
    xpath: str,
    namespaces: Mapping[str, str] | None = None,
    extensions: Mapping[tuple[str | None, str], Callable[..., Any]] | None = None,
    smart_strings: bool = True,
    **variables,
) -> TransformSchema:
    """
    Utility function for querying XML elements using XPath (:meth:`Element.xpath()`).

    XPath queries always return a result set, but if the result is an empty set, this function instead returns ``None``.

    Allows setting XPath variables (``$var``) as additional keywords.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.xml_xpath(".//b[@c=$c][1]/@d", c="2"),
        )
        assert schema.validate(lxml.etree.XML("<a><b c='1' d='A'/><b c='2' d='B'/></a>")) == ["B"]
        assert schema.validate(lxml.etree.XML("<a></a>")) is None
        schema.validate("<a><b c='1' d='A'/><b c='2' d='B'/></a>")  # raises ValidationError

    :raise ValidationError: If the input is not an :class:`lxml.etree.Element`
    :raise ValidationError: On XPath evaluation error
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
    namespaces: Mapping[str, str] | None = None,
    extensions: Mapping[tuple[str | None, str], Callable[..., Any]] | None = None,
    **variables,
) -> TransformSchema:
    """
    Utility function for querying XML elements using XPath (:meth:`Element.xpath()`) and turning the result into a string.

    XPath queries always return a result set, so be aware when querying multiple elements.
    If the result is an empty set, this function instead returns ``None``.

    Allows setting XPath variables (``$var``) as additional keywords.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.xml_xpath_string(".//b[2]/text()"),
        )
        assert schema.validate(lxml.etree.XML("<a><b>A</b><b>B</b><b>C</b></a>")) == "B"
        assert schema.validate(lxml.etree.XML("<a></a>")) is None
        schema.validate("<a><b>A</b><b>B</b><b>C</b></a>")  # raises ValidationError

    :raise ValidationError: If the input is not an :class:`lxml.etree.Element`
    :raise ValidationError: On XPath evaluation error
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
    Utility function for parsing JSON data using :func:`streamlink.utils.parse.parse_json()`.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.parse_json(),
        )
        assert schema.validate(\"\"\"{"a":[1,2,3],"b":null}\"\"\") == {"a": [1, 2, 3], "b": None}
        schema.validate(123)  # raises ValidationError

    :raise ValidationError: On parsing error
    """

    return TransformSchema(_parse_json, *args, **kwargs, exception=ValidationError, schema=None)


def validator_parse_html(*args, **kwargs) -> TransformSchema:
    """
    Utility function for parsing HTML data using :func:`streamlink.utils.parse.parse_html()`.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.parse_html(),
        )
        assert schema.validate(\"\"\"<html lang="en">\"\"\").attrib["lang"] == "en"
        schema.validate(123)  # raises ValidationError

    :raise ValidationError: On parsing error
    """

    return TransformSchema(_parse_html, *args, **kwargs, exception=ValidationError, schema=None)


def validator_parse_xml(*args, **kwargs) -> TransformSchema:
    """
    Utility function for parsing XML data using :func:`streamlink.utils.parse.parse_xml()`.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.parse_xml(),
        )
        assert schema.validate(\"\"\"<a b="c"/>\"\"\").attrib["b"] == "c"
        schema.validate(123)  # raises ValidationError

    :raise ValidationError: On parsing error
    """

    return TransformSchema(_parse_xml, *args, **kwargs, exception=ValidationError, schema=None)


def validator_parse_qsd(*args, **kwargs) -> TransformSchema:
    """
    Utility function for parsing a query string using :func:`streamlink.utils.parse.parse_qsd()`.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.parse_qsd(),
        )
        assert schema.validate("a=b&a=c&foo=bar") == {"a": "c", "foo": "bar"}
        schema.validate(123)  # raises ValidationError

    :raise ValidationError: On parsing error
    """

    def parser(*_args, **_kwargs):
        validate(AnySchema(str, bytes), _args[0])
        return _parse_qsd(*_args, **_kwargs, exception=ValidationError, schema=None)

    return TransformSchema(parser, *args, **kwargs)
