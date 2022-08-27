# noinspection PyPep8Naming,PyShadowingBuiltins
from streamlink.plugin.api.validate._schemas import (  # noqa: I101, F401
    SchemaContainer,
    AllSchema as all,
    AnySchema as any,
    NoneOrAllSchema as none_or_all,
    ListSchema as list,
    RegexSchema as regex,
    TransformSchema as transform,
    OptionalSchema as optional,
    GetItemSchema as get,
    AttrSchema as attr,
    UnionSchema as union,
    UnionGetSchema as union_get,
    XmlElementSchema as xml_element,
)
from streamlink.plugin.api.validate._validate import (  # noqa: F401
    Schema,
    validate,
)
# noinspection PyShadowingBuiltins
from streamlink.plugin.api.validate._validators import (  # noqa: I101, F401
    validator_length as length,
    validator_startswith as startswith,
    validator_endswith as endswith,
    validator_contains as contains,
    validator_url as url,
    validator_getattr as getattr,
    validator_hasattr as hasattr,
    validator_filter as filter,
    validator_map as map,
    validator_xml_find as xml_find,
    validator_xml_findall as xml_findall,
    validator_xml_findtext as xml_findtext,
    validator_xml_xpath as xml_xpath,
    validator_xml_xpath_string as xml_xpath_string,
    validator_parse_json as parse_json,
    validator_parse_html as parse_html,
    validator_parse_xml as parse_xml,
    validator_parse_qsd as parse_qsd,
)


text = str
