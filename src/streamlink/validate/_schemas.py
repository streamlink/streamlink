from __future__ import annotations

from collections.abc import Callable, Sequence
from re import Pattern
from typing import Any, Literal


class SchemaContainer:
    """
    A simple schema container.
    """

    def __init__(self, schema):
        self.schema = schema


class _CollectionSchemaContainer(SchemaContainer):
    def __init__(self, *schemas):
        super().__init__(schemas)


class AllSchema(_CollectionSchemaContainer):
    """
    A collection of schemas where each schema must be valid.

    Validates one schema after another with the input value of the return value of the previous one.

    Example:

    .. code-block:: python

        # `validate.Schema` is a subclass of `AllSchema` (`validate.all`)
        schema = validate.Schema(
            int,
            validate.transform(lambda val: val + 1),
            lambda val: val < 3,
        )
        assert schema.validate(1) == 2
        schema.validate("a")  # raises ValidationError
        schema.validate(2)  # raises ValidationError

    :param Any \\*schemas: Schemas where each one must be valid
    :return: The return value of the last schema
    """


class AnySchema(_CollectionSchemaContainer):
    """
    A collection of schemas where at least one schema must be valid.

    Validates one schema after another with the same input value until the first one succeeds.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.any(int, float, str),
        )
        assert schema.validate(123) == 123
        assert schema.validate(123.0) == 123.0
        assert schema.validate("123") == "123"
        schema.validate(None)  # raises ValidationError

    :param Any \\*schemas: Schemas where at least one must be valid
    :raise ValidationError: Error collection of all schema validations if none succeeded
    :return: The return value of the first valid schema
    """


class NoneOrAllSchema(_CollectionSchemaContainer):
    """
    Similar to :class:`AllSchema`, but skips the validation if the input value is ``None``.

    This is useful for optional validation results, e.g. when validating a potential match of a regular expression.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.none_or_all(
                int,
                lambda val: val < 2,
            ),
        )
        assert schema.validate(None) is None
        assert schema.validate(1) == 1
        schema.validate("123")  # raises ValidationError
        schema.validate(2)  # raises ValidationError

    :param Any \\*schemas: Schemas where each one must be valid, unless the input is ``None``
    :raise ValidationError: Error wrapper of the failed schema validation
    :return: ``None`` if the input is ``None``, or the return value of the last schema
    """


class TransformSchema:
    """
    A transform function which receives the input value as the argument, with optional custom arguments and keywords.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.transform(lambda val: val + 1),
            validate.transform(operator.lt, 3),
        )
        assert schema.validate(1) is True
        assert schema.validate(2) is False

    :param func: A transform function
    :param \\*args: Additional arguments
    :param \\*\\*kwargs: Additional keywords
    :raise ValidationError: If the transform function is not callable
    :return: The return value of the transform function
    """

    def __init__(
        self,
        func: Callable,
        *args,
        **kwargs,
    ):
        self.func = func
        self.args = args
        self.kwargs = kwargs


class OptionalSchema:  # noqa: B903
    """
    An optional key set in a :class:`dict`.

    See the :func:`dict <streamlink.plugin.api.validate.validate_dict>` validation and the :class:`UnionSchema`.
    """

    def __init__(self, key: Any):
        self.key = key


class ListSchema(_CollectionSchemaContainer):
    """
    A list of schemas where every item must be valid, as well as the input type and length.

    Please note the difference between :class:`ListSchema`
    and the :func:`list <streamlink.plugin.api.validate.validate_sequence()>` validation.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.list(1, 2, int),
        )
        assert schema.validate([1, 2, 3]) == [1, 2, 3]
        schema.validate(None)  # raises ValidationError
        schema.validate([1, 2])  # raises ValidationError
        schema.validate([3, 2, 1])  # raises ValidationError

    :param Any \\*schema: Schemas where each one must be valid
    :raise ValidationError: If the input is not a :class:`list`
    :raise ValidationError: If the input's length is not equal to the number of schemas
    :return: A new :class:`list <builtins.list>` with the validated input
    """


class AttrSchema(SchemaContainer):
    """
    Validate attributes of an input object according to a :class:`dict`'s key-value pairs.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.attr({
                "a": str,
                "b": int,
            }),
        )
        assert schema.validate(obj) is not obj
        schema.validate(obj_without_a)  # raises ValidationError
        schema.validate(obj_b_is_str)  # raises ValidationError

    :param dict[str, Any] schema: A :class:`dict` with attribute validations
    :raise ValidationError: If the input doesn't have one of the schema's attributes
    :return: A copy of the input object with validated attributes
    """


class GetItemSchema:  # noqa: B903
    """
    Get an ``item`` from the input.

    The input can be anything that implements :func:`__getitem__()`,
    as well as :class:`lxml.etree.Element` objects where element attributes are looked up.

    Returns the ``default`` value if ``item`` was not found.

    Unless ``strict`` is set to ``True``, the ``item`` can be a :class:`tuple` of items for a recursive lookup.
    In this case, the ``default`` value is only returned if the leaf-input-object doesn't contain the current ``item``.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.get("name", default="unknown"),
        )
        assert schema.validate({"name": "user"}) == "user"
        assert schema.validate(re.match(r"Hello, (?P<name>\\w+)!", "Hello, user!")) == "user"
        assert schema.validate(lxml.etree.XML(\"\"\"<elem name="abc"/>\"\"\")) == "abc"
        assert schema.validate({}) == "unknown"
        schema.validate(None)  # raises ValidationError

    .. code-block:: python

        schema = validate.Schema(
            validate.get(("a", "b", "c")),
        )
        assert schema.validate({"a": {"b": {"c": "d"}}}) == "d"
        assert schema.validate({"a": {"b": {}}}) is None
        schema.validate({"a": {}})  # raises ValidationError

    :param item: The lookup key, or a :class:`tuple` of recursive lookup keys
    :param default: Optional custom default value
    :param strict: If ``True``, don't perform recursive lookups with the :class:`tuple` item
    :raise ValidationError: If the input doesn't implement :func:`__getitem__()`
    :raise ValidationError: If the input doesn't have the current ``item`` in a recursive non-leaf-input-object lookup
    :return: The :func:`__getitem__()` return value, or an :class:`lxml.etree.Element` attribute
    """

    def __init__(
        self,
        item: Any | tuple,
        default: Any = None,
        strict: bool = False,
    ):
        self.item = item
        self.default = default
        self.strict = strict


class UnionSchema(SchemaContainer):
    """
    Validate multiple schemas on the same input.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.union((
                validate.transform(str.format, one="abc", two="def"),
                validate.transform(str.format, one="123", two="456"),
            )),
        )
        assert schema.validate("{one} {two}") == ("abc def", "123 456")

    .. code-block:: python

        schema = validate.Schema(
            validate.union({
                "one": lambda val: val < 3,
                validate.optional("two"): lambda val: val > 1,
            }),
        )
        assert schema.validate(1) == {"one": 1}
        assert schema.validate(2) == {"one": 2, "two": 2}
        schema.validate(3)  # raises ValidationError

    :param Union[tuple, list, set, frozenset, dict] schema: A :class:`tuple`, :class:`list`, :class:`set`, :class:`frozenset`
                                                            or :class:`dict` of schemas
    :raises ValidationError: If a sequence item or the value of a non-optional key-value pair doesn't validate
    :return: A new object of the same type, with each item or key-value pair being validated against the same input value
    """


class UnionGetSchema:
    """
    Validate multiple :class:`GetItemSchema` schemas on the same input.

    Convenience wrapper for ``validate.union((validate.get(...), validate.get(...), ...))``.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.union_get("a", "b", ("c", "d")),
        )
        assert schema.validate({"a": 1, "b": 2, "c": {"d": 3}}) == (1, 2, 3)

    :param \\*getters: Inputs for each :class:`GetItemSchema`
    :return: A :class:`tuple` (default ``seq`` type) with items of the respective :class:`GetItemSchema` validations
    """

    def __init__(
        self,
        *getters,
        seq: type[tuple | list | set | frozenset] = tuple,
    ):
        self.getters: Sequence[GetItemSchema] = tuple(GetItemSchema(getter) for getter in getters)
        self.seq = seq


class RegexSchema:  # noqa: B903
    """
    A :class:`re.Pattern` that **must** match.

    Allows selecting a different regex pattern method (default is :meth:`re.Pattern.search()`).

    Please note the difference between :class:`RegexSchema`
    and the :func:`re.Pattern <streamlink.plugin.api.validate.validate_pattern()>` validation.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.regex(re.compile(r"Hello, (?P<name>\\w+)!")),
        )
        assert schema.validate("Hello, world!")["name"] == "world"
        schema.validate("Does not match")  # raises ValidationError
        schema.validate(123)  # raises ValidationError
        schema.validate(b"Hello, world!")  # raises ValidationError

    .. code-block:: python

        schema = validate.Schema(
            validate.regex(re.compile(r"Hello, (?P<name>\\w+)!"), method="findall"),
        )
        assert schema.validate("Hello, userA! Hello, userB!") == ["userA", "userB"]
        assert schema.validate("Does not match") == []  # findall does not return None

    :param pattern: A compiled pattern (:func:`re.compile` return value)
    :param method: The pattern's method which will be called when validating
    :raise ValidationError: If the input is not an instance of ``str`` or ``bytes``
    :raise ValidationError: If the type of the input doesn't match the pattern's ``str``/``bytes`` type
    :raise ValidationError: If the return value of the chosen regex pattern method is ``None``
    """

    def __init__(
        self,
        pattern: Pattern,
        method: Literal["search", "match", "fullmatch", "findall", "split", "sub", "subn"] = "search",
    ):
        self.pattern = pattern
        self.method = method


class XmlElementSchema:  # noqa: B903
    """
    Validate an XML element.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            validate.xml_element(
                tag="foo",
                attrib={"bar": str},
                text=validate.transform(str.upper),
            ),
        )
        elem = lxml.etree.XML(\"\"\"<foo bar="baz">qux</foo>\"\"\")
        new_elem = schema.validate(elem)
        assert new_elem is not elem
        assert new_elem.tag == "foo"
        assert new_elem.attrib == {"bar": "baz"}
        assert new_elem.text == "QUX"
        assert new_elem.tail is None
        schema.validate(123)  # raises ValidationError
        schema.validate(lxml.etree.XML(\"\"\"<unknown/>\"\"\"))  # raises ValidationError

    :param tag: Optional element tag validation
    :param text: Optional element text validation
    :param attrib: Optional element attributes validation
    :param tail: Optional element tail validation
    :raise ValidationError: If ``value`` is not an :class:`lxml.etree.Element`
    :return: A new :class:`lxml.etree.Element` object, including a deep-copy of the input's child nodes,
             with optionally validated ``tag``, ``attrib`` mapping, ``text`` or ``tail``.
    """

    # signature is weird because of backwards compatiblity
    def __init__(
        self,
        tag: Any = None,
        text: Any = None,
        attrib: Any = None,
        tail: Any = None,
    ):
        self.tag = tag
        self.attrib = attrib
        self.text = text
        self.tail = tail
