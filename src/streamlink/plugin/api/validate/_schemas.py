from typing import Any, Callable, FrozenSet, List, Optional, Sequence, Set, Tuple, Type, Union


class SchemaContainer:
    """
    A simple schema container.
    """

    def __init__(self, schema):
        self.schema = schema


class AllSchema(SchemaContainer):
    """
    Collection of schemas where every schema must be valid.
    """

    def __init__(self, *schemas):
        super().__init__(schemas)


class AnySchema(SchemaContainer):
    """
    Collection of schemas where at least one schema must be valid.
    """

    def __init__(self, *schemas):
        super().__init__(schemas)


class GetItemSchema:
    """
    Get an item from the input.

    Unless strict is set to True, item can be a tuple of items for recursive lookups.
    If the item is not found in the last object of a recursive lookup, return the default.
    Supported inputs are XML elements, regex matches and anything that implements __getitem__.
    """

    def __init__(
        self,
        item: Union[Any, Tuple[Any]],
        default: Any = None,
        strict: bool = False,
    ):
        self.item = item
        self.default = default
        self.strict = strict


class TransformSchema:
    """
    Transform the input using the specified function and args/keywords.
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


class OptionalSchema:
    """
    An optional key set in a dict or dict in a :class:`UnionSchema`.
    """

    def __init__(self, key: Any):
        self.key = key


class AttrSchema(SchemaContainer):
    """
    Validate attributes of an input object.
    """


class XmlElementSchema:
    """
    Validate an XML element.
    """

    # signature is weird because of backwards compatiblity
    def __init__(
        self,
        tag: Optional[Any] = None,
        text: Optional[Any] = None,
        attrib: Optional[Any] = None,
        tail: Optional[Any] = None,
    ):
        self.tag = tag
        self.attrib = attrib
        self.text = text
        self.tail = tail


class UnionGetSchema:
    """
    Validate multiple :class:`GetItemSchema` schemas on the same input.
    """

    def __init__(
        self,
        *getters,
        seq: Type[Union[List, FrozenSet, Set, Tuple]] = tuple,
    ):
        self.getters: Sequence[GetItemSchema] = tuple(GetItemSchema(getter) for getter in getters)
        self.seq = seq


class UnionSchema(SchemaContainer):
    """
    Validate multiple schemas on the same input.

    Can be a tuple, list, set, frozenset or dict of schemas.
    """
