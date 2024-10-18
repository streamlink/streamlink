Validation schemas
------------------

.. ..
    Sphinx's autodoc doesn't properly document imported module members and it just outputs "alias of" for re-exported classes.
    This means we'll have to run `automodule` twice if we want to document the original classes:
    1. the main public interface (which contains aliases, like `all` for `AllSchema` for example)
    2. the original schema classes with their full signatures and docstrings
    .
    Ignore unneeded classes like `SchemaContainer` which are not useful for the API docs.
    .
    Ignore `validate` as well, as `functools.singledispatch` functions are not fully supported by autodoc.
    Instead, manually document `validate` and its overloading functions for base schema types here at the top,
    just below the manually imported `Schema` (the main validation schema interface).
    The documentations for any custom schemas like `AllSchema` for example is done on the schemas themselves.
    .
    Ideally, we'd just run autodoc on the main module and configure the order of items. :(

Please see the :ref:`validation schema guides <api_guide/validate:Validation schemas>`
for an introduction to this API and a list of examples.

.. admonition:: Public interface
   :class: caution

   While the internals are implemented in the ``streamlink.validate`` package,
   :ref:`streamlink.plugin.api.validate <api/validate:Validation schemas>` provides the main public interface
   for plugin implementors.

.. autoclass:: streamlink.plugin.api.validate.Schema
    :members:
    :undoc-members:

.. py:function:: validate(schema, value)
    :module: streamlink.plugin.api.validate

    The core of the :mod:`streamlink.plugin.api.validate` module.

    It validates the given input ``value`` and returns a value according to the specific validation rules of the ``schema``.

    If the validation fails, a :exc:`ValidationError <_exception.ValidationError>` is raised with a detailed error message.

    The ``schema`` can be any kind of object. Depending on the ``schema``, different validation rules apply.

    Simple schema objects like ``"abc"`` or ``123`` for example test the equality of ``value`` and ``schema``
    and return ``value`` again, while type schema objects like ``str`` test whether ``value`` is an instance of ``schema``.
    ``schema`` objects which are callable receive ``value`` as a single argument and must return a truthy value, otherwise the
    validation fails. These are just a few examples.

    The ``validate`` module implements lots of special schemas, like :class:`validate.all <all>` or :class:`validate.any <any>`
    for example, which are schema containers that receive a sequence of sub-schemas as arguments and where each sub-schema
    then gets validated one after another.

    :class:`validate.all <all>` requires each sub-schema to successfully validate. It passes the return value of each
    sub-schema to the next one and then returns the return value of the last sub-schema.

    :class:`validate.any <any>` on the other hand requires at least one sub-schema to be valid and returns the return value of
    the first valid sub-schema. Any validation failures prior will be ignored, but at least one must succeed.

    Other special ``schema`` cases for example are instances of sequences like ``list`` or ``tuple``, or mappings like ``dict``.
    Here, each sequence item or key-value mapping pair is validated against the input ``value``
    and a new sequence/mapping object according to the ``schema`` validation is returned.

    :func:`validate()` should usually not be called directly when validating schemas. Instead, the wrapper method
    :meth:`Schema.validate() <Schema.validate>` of the main :class:`Schema` class should be called. Other Streamlink APIs
    like the methods of the :class:`HTTPSession <streamlink.session.Streamlink.http>` or the various
    :mod:`streamlink.utils.parse` functions for example expect this interface when the ``schema`` keyword is set,
    which allows for immediate validation of the data using a :class:`Schema` object.

    :func:`validate()` is implemented using the stdlib's :func:`functools.singledispatch` decorator, where more specific
    schemas overload the default implementation with more validation logic.

    ----

    By default, :func:`validate()` compares ``value`` and ``schema`` for equality. This means that simple schema objects
    like booleans, strings, numbers, None, etc. are validated here, as well as anything unknown.

    Example:

    .. code-block:: python

        schema = validate.Schema(123)
        assert schema.validate(123) == 123
        assert schema.validate(123.0) == 123.0
        schema.validate(456)  # raises ValidationError
        schema.validate(None)  # raises ValidationError

    :param Any schema: Any kind of object not handled by a more specific validation function
    :param Any value: The input value
    :raise ValidationError: If ``value`` and ``schema`` are not equal
    :return: Unmodified ``value``

.. py:function:: _validate_type(schema, value)
    :module: streamlink.plugin.api.validate

    :class:`type` validation.

    Checks if ``value`` is an instance of ``schema``.

    Example:

    .. code-block:: python

        schema = validate.Schema(int)
        assert schema.validate(123) == 123
        assert schema.validate(True) is True  # `bool` is a subclass of `int`
        schema.validate("123")  # raises ValidationError

    *This function is included for documentation purposes only! (singledispatch overload)*

    :param type schema: A :class:`type` object
    :param Any value: The input value
    :raise ValidationError: If ``value`` is not an instance of ``schema``
    :return: Unmodified ``value``

.. py:function:: _validate_callable(schema, value)
    :module: streamlink.plugin.api.validate

    ``Callable`` validation.

    Validates a ``schema`` function where ``value`` gets passed as a single argument.

    Must return a truthy value.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            lambda val: val < 2,
        )
        assert schema.validate(1) == 1
        schema.validate(2)  # raises ValidationError

    *This function is included for documentation purposes only! (singledispatch overload)*

    :param Callable schema: A function with one argument
    :param Any value: The input value
    :raise ValidationError: If ``schema`` returns a non-truthy value
    :return: Unmodified ``value``

.. py:function:: _validate_sequence(schema, value)
    :module: streamlink.plugin.api.validate

    :class:`list <builtins.list>`, :class:`tuple`, :class:`set` and :class:`frozenset` validation.

    Each item of ``value`` gets validated against **any** of the items of ``schema``.

    Please note the difference between :class:`list <builtins.list>`
    and the :class:`ListSchema <_schemas.ListSchema>` validation.

    Example:

    .. code-block:: python

        schema = validate.Schema([1, 2, 3])
        assert schema.validate([]) == []
        assert schema.validate([1, 2]) == [1, 2]
        assert schema.validate([3, 2, 1]) == [3, 2, 1]
        schema.validate({1, 2, 3})  # raises ValidationError
        schema.validate([1, 2, 3, 4])  # raises ValidationError

    *This function is included for documentation purposes only! (singledispatch overload)*

    :param Union[list, tuple, set, frozenset] schema: A sequence of validation schemas
    :param Any value: The input value
    :raise ValidationError: If ``value`` is not an instance of the ``schema``'s own type
    :return: A new sequence of the same type as ``schema`` with each item of ``value`` being validated

.. py:function:: _validate_dict(schema, value)
    :module: streamlink.plugin.api.validate

    :class:`dict` validation.

    Each key-value pair of ``schema`` gets validated against the respective key-value pair of ``value``.

    Additional keys in ``value`` are ignored and not included in the validation result.

    If a ``schema`` key is an instance of :class:`OptionalSchema <_schemas.OptionalSchema>`, then ``value`` may omit it.

    If one of the ``schema``'s keys is a :class:`type`,
    :class:`AllSchema <_schemas.AllSchema>`, :class:`AnySchema <_schemas.AnySchema>`,
    :class:`TransformSchema <_schemas.TransformSchema>`, or :class:`UnionSchema <_schemas.UnionSchema>`,
    then all key-value pairs of ``value`` are validated against the ``schema``'s key-value pair.

    Example:

    .. code-block:: python

        schema = validate.Schema({
            "key": str,
            validate.optional("opt"): 123,
        })
        assert schema.validate({"key": "val", "other": 123}) == {"key": "val"}
        assert schema.validate({"key": "val", "opt": 123}) == {"key": "val", "opt": 123}
        schema.validate(None)  # raises ValidationError
        schema.validate({})  # raises ValidationError
        schema.validate({"key": 123})  # raises ValidationError
        schema.validate({"key": "val", "opt": 456})  # raises ValidationError

    .. code-block:: python

        schema = validate.Schema({
            validate.any("a", "b"): int,
        })
        assert schema.validate({}) == {}
        assert schema.validate({"a": 1}) == {"a": 1}
        assert schema.validate({"b": 2}) == {"b": 2}
        assert schema.validate({"a": 1, "b": 2}) == {"a": 1, "b": 2}
        schema.validate({"a": 1, "b": 2, "other": 0})  # raises ValidationError
        schema.validate({"a": None})  # raises ValidationError

    *This function is included for documentation purposes only! (singledispatch overload)*

    :param dict schema: A :class:`dict`
    :param Any value: The input value
    :raise ValidationError: If ``value`` is not a :class:`dict`
    :raise ValidationError: If any of the ``schema``'s non-optional keys are not part of the input ``value``
    :return: A new :class:`dict`

.. py:function:: _validate_pattern(schema, value)
    :module: streamlink.plugin.api.validate

    :class:`re.Pattern` validation.

    Calls the :meth:`re.Pattern.search()` method on the ``schema`` pattern.

    Please note the difference between :class:`re.Pattern` and the :class:`RegexSchema <_schemas.RegexSchema>` validation.

    Example:

    .. code-block:: python

        schema = validate.Schema(
            re.compile(r"^Hello, (?P<name>\w+)!$"),
        )
        assert schema.validate("Does not match") is None
        assert schema.validate("Hello, world!")["name"] == "world"
        schema.validate(123)  # raises ValidationError
        schema.validate(b"Hello, world!")  # raises ValidationError

    *This function is included for documentation purposes only! (singledispatch overload)*

    :param re.Pattern schema: A compiled :class:`re.Pattern` object (:func:`re.compile()` return value)
    :param Any value: The input value
    :raise ValidationError: If ``value`` is not an instance of :class:`str` or :class:`bytes`
    :raise ValidationError: If the type of ``value`` doesn't match ``schema``'s :class:`str`/:class:`bytes` type
    :return: ``None`` if ``value`` doesn't match ``schema``, or the resulting :class:`re.Match` object

.. automodule:: streamlink.plugin.api.validate
    :imported-members:
    :exclude-members: Schema, SchemaContainer, validate
    :member-order: bysource

.. automodule:: streamlink.validate._schemas
    :exclude-members: SchemaContainer
    :member-order: bysource
    :no-show-inheritance:

.. autoexception:: streamlink.validate._exception.ValidationError
