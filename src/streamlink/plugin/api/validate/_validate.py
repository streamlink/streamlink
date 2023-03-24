from collections import abc
from copy import copy, deepcopy
from functools import singledispatch
from re import Match, Pattern

from lxml.etree import Element, iselement

from streamlink.exceptions import PluginError
from streamlink.plugin.api.validate._exception import ValidationError
from streamlink.plugin.api.validate._schemas import (
    AllSchema,
    AnySchema,
    AttrSchema,
    GetItemSchema,
    ListSchema,
    NoneOrAllSchema,
    OptionalSchema,
    RegexSchema,
    TransformSchema,
    UnionGetSchema,
    UnionSchema,
    XmlElementSchema,
)


class Schema(AllSchema):
    """
    Wrapper class for :class:`AllSchema` with a validate method which raises :class:`PluginError` by default on error.
    """

    def validate(self, value, name="result", exception=PluginError):
        try:
            return validate(self, value)
        except ValidationError as err:
            raise exception(f"Unable to validate {name}: {err}") from None


# ----


@singledispatch
def validate(schema, value):
    if schema != value:
        raise ValidationError(
            "{value} does not equal {expected}",
            value=repr(value),
            expected=repr(schema),
            schema="equality",
        )

    return value


@validate.register(type)
def _validate_type(schema, value):
    if not isinstance(value, schema):
        raise ValidationError(
            "Type of {value} should be {expected}, but is {actual}",
            value=repr(value),
            expected=schema.__name__,
            actual=type(value).__name__,
            schema=type,
        )

    return value


@validate.register(list)
@validate.register(tuple)
@validate.register(set)
@validate.register(frozenset)
def _validate_sequence(schema, value):
    cls = type(schema)
    validate(cls, value)

    return cls(
        validate(AnySchema(*schema), v) for v in value
    )


@validate.register(dict)
def _validate_dict(schema, value):
    cls = type(schema)
    validate(cls, value)
    new = cls()

    for key, subschema in schema.items():
        if isinstance(key, OptionalSchema):
            if key.key not in value:
                continue
            key = key.key

        if type(key) in (type, AllSchema, AnySchema, TransformSchema, UnionSchema):
            for subkey, subvalue in value.items():
                try:
                    newkey = validate(key, subkey)
                except ValidationError as err:
                    raise ValidationError("Unable to validate key", schema=dict) from err
                try:
                    newvalue = validate(subschema, subvalue)
                except ValidationError as err:
                    raise ValidationError("Unable to validate value", schema=dict) from err
                new[newkey] = newvalue
            break

        if key not in value:
            raise ValidationError(
                "Key {key} not found in {value}",
                key=repr(key),
                value=repr(value),
                schema=dict,
            )

        try:
            new[key] = validate(subschema, value[key])
        except ValidationError as err:
            raise ValidationError("Unable to validate value of key {key}", key=repr(key), schema=dict) from err

    return new


@validate.register
def _validate_callable(schema: abc.Callable, value):
    if not schema(value):
        raise ValidationError(
            "{callable} is not true",
            callable=f"{schema.__name__}({value!r})",
            schema=abc.Callable,
        )

    return value


@validate.register
def _validate_pattern(schema: Pattern, value):
    if not isinstance(value, (str, bytes)):
        raise ValidationError(
            "Type of {value} should be str or bytes, but is {actual}",
            value=repr(value),
            actual=type(value).__name__,
            schema=Pattern,
        )

    try:
        result = schema.search(value)
    except TypeError as err:
        raise ValidationError(err, schema=Pattern) from None

    return result


@validate.register
def _validate_allschema(schema: AllSchema, value):
    for subschema in schema.schema:
        value = validate(subschema, value)

    return value


@validate.register
def _validate_anyschema(schema: AnySchema, value):
    errors = []
    for subschema in schema.schema:
        try:
            return validate(subschema, value)
        except ValidationError as err:
            errors.append(err)

    raise ValidationError(*errors, schema=AnySchema)


@validate.register
def _validate_noneorallschema(schema: NoneOrAllSchema, value):
    if value is not None:
        try:
            for subschema in schema.schema:
                value = validate(subschema, value)
        except ValidationError as err:
            raise ValidationError(err, schema=NoneOrAllSchema) from None

    return value


@validate.register
def _validate_listschema(schema: ListSchema, value):
    if type(value) is not list:
        raise ValidationError(
            "Type of {value} should be list, but is {actual}",
            value=repr(value),
            actual=type(value).__name__,
            schema=ListSchema,
        )
    if len(value) != len(schema.schema):
        raise ValidationError(
            "Length of list ({length}) does not match expectation ({expected})",
            length=len(value),
            expected=len(schema.schema),
            schema=ListSchema,
        )

    new = []
    errors = []
    for k, v in enumerate(schema.schema):
        try:
            new.append(validate(v, value[k]))
        except ValidationError as err:
            errors.append(err)

    if errors:
        raise ValidationError(*errors, schema=ListSchema)

    return new


@validate.register
def _validate_regexschema(schema: RegexSchema, value):
    if not isinstance(value, (str, bytes)):
        raise ValidationError(
            "Type of {value} should be str or bytes, but is {actual}",
            value=repr(value),
            actual=type(value).__name__,
            schema=RegexSchema,
        )

    try:
        result = getattr(schema.pattern, schema.method)(value)
    except TypeError as err:
        raise ValidationError(err, schema=RegexSchema) from None

    if result is None:
        raise ValidationError(
            "Pattern {pattern} did not match {value}",
            pattern=repr(schema.pattern.pattern),
            value=repr(value),
            schema=RegexSchema,
        )

    return result


@validate.register
def _validate_transformschema(schema: TransformSchema, value):
    validate(abc.Callable, schema.func)
    return schema.func(value, *schema.args, **schema.kwargs)


@validate.register
def _validate_getitemschema(schema: GetItemSchema, value):
    item = schema.item if type(schema.item) is tuple and not schema.strict else (schema.item,)
    idx = 0
    key = None
    try:
        for key in item:
            if iselement(value):
                value = value.attrib[key]
            elif isinstance(value, Match):
                value = value.group(key)
            else:
                value = value[key]
            idx += 1
        return value
    except (KeyError, IndexError):
        # only return default value on last item in nested lookup
        if idx < len(item) - 1:
            raise ValidationError(
                "Item {key} was not found in object {value}",
                key=repr(key),
                value=repr(value),
                schema=GetItemSchema,
            ) from None
        return schema.default
    except (TypeError, AttributeError) as err:
        raise ValidationError(
            "Could not get key {key} from object {value}",
            key=repr(key),
            value=repr(value),
            schema=GetItemSchema,
        ) from err


@validate.register
def _validate_attrschema(schema: AttrSchema, value):
    new = copy(value)

    for key, subschema in schema.schema.items():
        if not hasattr(value, key):
            raise ValidationError(
                "Attribute {key} not found on object {value}",
                key=repr(key),
                value=repr(value),
                schema=AttrSchema,
            )

        try:
            value = validate(subschema, getattr(value, key))
        except ValidationError as err:
            raise ValidationError(
                "Could not validate attribute {key}",
                key=repr(key),
                schema=AttrSchema,
            ) from err

        setattr(new, key, value)

    return new


@validate.register
def _validate_xmlelementschema(schema: XmlElementSchema, value):
    validate(iselement, value)
    tag = value.tag
    attrib = value.attrib
    text = value.text
    tail = value.tail

    if schema.tag is not None:
        try:
            tag = validate(schema.tag, value.tag)
        except ValidationError as err:
            raise ValidationError("Unable to validate XML tag", schema=XmlElementSchema) from err

    if schema.attrib is not None:
        try:
            attrib = validate(schema.attrib, dict(value.attrib))
        except ValidationError as err:
            raise ValidationError("Unable to validate XML attributes", schema=XmlElementSchema) from err

    if schema.text is not None:
        try:
            text = validate(schema.text, value.text)
        except ValidationError as err:
            raise ValidationError("Unable to validate XML text", schema=XmlElementSchema) from err

    if schema.tail is not None:
        try:
            tail = validate(schema.tail, value.tail)
        except ValidationError as err:
            raise ValidationError("Unable to validate XML tail", schema=XmlElementSchema) from err

    new = Element(tag, attrib)
    new.text = text
    new.tail = tail
    for child in value:
        new.append(deepcopy(child))

    return new


@validate.register
def _validate_uniongetschema(schema: UnionGetSchema, value):
    return schema.seq(
        validate(getter, value) for getter in schema.getters
    )


@validate.register
def _validate_unionschema(schema: UnionSchema, value):
    try:
        return validate_union(schema.schema, value)
    except ValidationError as err:
        raise ValidationError("Could not validate union", schema=UnionSchema) from err


# ----


# noinspection PyUnusedLocal
@singledispatch
def validate_union(schema, value):
    raise ValidationError(
        "Invalid union type: {type}",
        type=type(schema).__name__,
    )


@validate_union.register(dict)
def _validate_union_dict(schema, value):
    new = type(schema)()
    for key, subschema in schema.items():
        is_optional = isinstance(key, OptionalSchema)
        if is_optional:
            key = key.key

        try:
            new[key] = validate(subschema, value)
        except ValidationError as err:
            if is_optional:
                continue

            raise ValidationError(
                "Unable to validate union {key}",
                key=repr(key),
                schema=dict,
            ) from err

    return new


@validate_union.register(list)
@validate_union.register(tuple)
@validate_union.register(set)
@validate_union.register(frozenset)
def _validate_union_sequence(schemas, value):
    return type(schemas)(
        validate(schema, value) for schema in schemas
    )
