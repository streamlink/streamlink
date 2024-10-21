# ruff: noqa: A001, A004, I001
# order the module members logically (autodoc_member_order == "bysource")

from streamlink.validate._validate import (
    Schema,
    validate,
)

# noinspection PyPep8Naming,PyShadowingBuiltins
from streamlink.validate._schemas import (
    SchemaContainer,
    AllSchema as all,
    AnySchema as any,
    NoneOrAllSchema as none_or_all,
    TransformSchema as transform,
    OptionalSchema as optional,
    ListSchema as list,
    AttrSchema as attr,
    GetItemSchema as get,
    UnionSchema as union,
    UnionGetSchema as union_get,
    RegexSchema as regex,
    XmlElementSchema as xml_element,
)

# noinspection PyShadowingBuiltins
from streamlink.validate._validators import (
    validator_contains as contains,
    validator_startswith as startswith,
    validator_endswith as endswith,
    validator_length as length,
    validator_getattr as getattr,
    validator_hasattr as hasattr,
    validator_filter as filter,
    validator_map as map,
    validator_url as url,
    validator_parse_html as parse_html,
    validator_parse_json as parse_json,
    validator_parse_qsd as parse_qsd,
    validator_parse_xml as parse_xml,
    validator_xml_find as xml_find,
    validator_xml_findall as xml_findall,
    validator_xml_findtext as xml_findtext,
    validator_xml_xpath as xml_xpath,
    validator_xml_xpath_string as xml_xpath_string,
)
