# noinspection PyPep8Naming,PyShadowingBuiltins
from streamlink.plugin.api.validate._schemas import (  # noqa: A001
    AllSchema as all,
    AnySchema as any,
    AttrSchema as attr,
    GetItemSchema as get,
    ListSchema as list,
    NoneOrAllSchema as none_or_all,
    OptionalSchema as optional,
    RegexSchema as regex,
    SchemaContainer,
    TransformSchema as transform,
    UnionGetSchema as union_get,
    UnionSchema as union,
    XmlElementSchema as xml_element,
)
from streamlink.plugin.api.validate._validate import (
    Schema,
    validate,
)

# noinspection PyShadowingBuiltins
from streamlink.plugin.api.validate._validators import (  # noqa: A001
    validator_contains as contains,
    validator_endswith as endswith,
    validator_filter as filter,
    validator_getattr as getattr,
    validator_hasattr as hasattr,
    validator_length as length,
    validator_map as map,
    validator_parse_html as parse_html,
    validator_parse_json as parse_json,
    validator_parse_qsd as parse_qsd,
    validator_parse_xml as parse_xml,
    validator_startswith as startswith,
    validator_url as url,
    validator_xml_find as xml_find,
    validator_xml_findall as xml_findall,
    validator_xml_findtext as xml_findtext,
    validator_xml_xpath as xml_xpath,
    validator_xml_xpath_string as xml_xpath_string,
)
