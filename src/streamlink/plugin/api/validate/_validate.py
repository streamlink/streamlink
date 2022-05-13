from collections import OrderedDict
from copy import copy, deepcopy

from lxml.etree import Element, iselement

from streamlink.compat import Callable, Match, is_py2, singledispatch, str as text_type
from streamlink.exceptions import PluginError
from streamlink.plugin.api.validate._exception import ValidationError
from streamlink.plugin.api.validate._schemas import (
    AllSchema,
    AnySchema,
    AttrSchema,
    GetItemSchema,
    OptionalSchema,
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
            raise exception("Unable to validate {0}: {1}".format(name, err))


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
    if is_py2 and type(value) == unicode:
        value = str(value)
    if schema == text_type:
        schema = str
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
                    raise ValidationError("Unable to validate key", schema=dict, context=err)
                try:
                    newvalue = validate(subschema, subvalue)
                except ValidationError as err:
                    raise ValidationError("Unable to validate value", schema=dict, context=err)
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
            raise ValidationError(
                "Unable to validate value of key {key}",
                key=repr(key),
                schema=dict,
                context=err,
            )

    return new


@validate.register(Callable)
def _validate_callable(schema, value):
    # type: (Callable)
    if not schema(value):
        raise ValidationError(
            "{callable} is not true",
            callable="{0}({1!r})".format(schema.__name__, value),
            schema=Callable,
        )

    return value


@validate.register(AllSchema)
def _validate_allschema(schema, value):
    # type: (AllSchema)
    for schema in schema.schema:
        value = validate(schema, value)

    return value


@validate.register(AnySchema)
def _validate_anyschema(schema, value):
    # type: (AnySchema)
    errors = []
    for subschema in schema.schema:
        try:
            return validate(subschema, value)
        except ValidationError as err:
            errors.append(err)

    raise ValidationError(*errors, schema=AnySchema)


@validate.register(TransformSchema)
def _validate_transformschema(schema, value):
    # type: (TransformSchema)
    validate(Callable, schema.func)
    return schema.func(value, *schema.args, **schema.kwargs)


@validate.register(GetItemSchema)
def _validate_getitemschema(schema, value):
    # type: (GetItemSchema)
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
            )
        return schema.default
    except (TypeError, AttributeError) as err:
        raise ValidationError(
            "Could not get key {key} from object {value}",
            key=repr(key),
            value=repr(value),
            schema=GetItemSchema,
            context=err,
        )


@validate.register(AttrSchema)
def _validate_attrschema(schema, value):
    # type: (AttrSchema)
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
                context=err,
            )

        setattr(new, key, value)

    return new


@validate.register(XmlElementSchema)
def _validate_xmlelementschema(schema, value):
    # type: (XmlElementSchema)
    validate(iselement, value)
    tag = value.tag
    attrib = value.attrib
    text = value.text
    tail = value.tail

    if schema.tag is not None:
        try:
            tag = validate(schema.tag, value.tag)
        except ValidationError as err:
            raise ValidationError("Unable to validate XML tag: {0}".format(err), schema=XmlElementSchema, context=err)

    if schema.attrib is not None:
        try:
            attrib = validate(schema.attrib, OrderedDict(value.attrib))
        except ValidationError as err:
            raise ValidationError("Unable to validate XML attributes: {0}".format(err), schema=XmlElementSchema, context=err)

    if schema.text is not None:
        try:
            text = validate(schema.text, value.text)
        except ValidationError as err:
            raise ValidationError("Unable to validate XML text: {0}".format(err), schema=XmlElementSchema, context=err)

    if schema.tail is not None:
        try:
            tail = validate(schema.tail, value.tail)
        except ValidationError as err:
            raise ValidationError("Unable to validate XML tail: {0}".format(err), schema=XmlElementSchema, context=err)

    new = Element(tag, attrib)
    new.text = text
    new.tail = tail
    for child in value:
        new.append(deepcopy(child))

    return new


@validate.register(UnionGetSchema)
def _validate_uniongetschema(schema, value):
    # type: (UnionGetSchema)
    return schema.seq(
        validate(getter, value) for getter in schema.getters
    )


@validate.register(UnionSchema)
def _validate_unionschema(schema, value):
    # type: (UnionSchema)
    try:
        return validate_union(schema.schema, value)
    except ValidationError as err:
        raise ValidationError("Could not validate union", schema=UnionSchema, context=err)


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
    for key, schema in schema.items():
        is_optional = isinstance(key, OptionalSchema)
        if is_optional:
            key = key.key

        try:
            new[key] = validate(schema, value)
        except ValidationError as err:
            if is_optional:
                continue

            raise ValidationError(
                "Unable to validate union {key}",
                key=repr(key),
                schema=dict,
                context=err,
            )

    return new


@validate_union.register(list)
@validate_union.register(tuple)
@validate_union.register(set)
@validate_union.register(frozenset)
def _validate_union_sequence(schemas, value):
    return type(schemas)(
        validate(schema, value) for schema in schemas
    )
