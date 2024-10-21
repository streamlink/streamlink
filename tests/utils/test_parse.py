import pytest
from lxml.etree import Element

from streamlink.exceptions import PluginError
from streamlink.plugin.api import validate
from streamlink.plugin.api.validate import xml_element
from streamlink.utils.parse import parse_html, parse_json, parse_qsd, parse_xml


class TestUtilsParse:
    def test_parse_json(self):
        assert parse_json("{}") == {}
        assert parse_json('{"test": 1}') == {"test": 1}
        assert parse_json('{"test": 1}', schema=validate.Schema({"test": 1})) == {"test": 1}
        with pytest.raises(PluginError):
            parse_json("""{"test: 1}""")
        with pytest.raises(SyntaxError):
            parse_json("""{"test: 1}""", exception=SyntaxError)
        with pytest.raises(PluginError):
            parse_json("""{"test: 1}""" * 10)

    def test_parse_xml(self):
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml("""<test foo="bar"/>""", ignore_ns=True)
        assert actual.tag == expected.tag
        assert actual.attrib == expected.attrib

    def test_parse_xml_ns_ignore(self):
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml("""<test foo="bar" xmlns="foo:bar"/>""", ignore_ns=True)
        assert actual.tag == expected.tag
        assert actual.attrib == expected.attrib

        actual = parse_xml("""<test	foo="bar"	xmlns="foo:bar"/>""", ignore_ns=True)
        assert actual.tag == expected.tag
        assert actual.attrib == expected.attrib

        actual = parse_xml("""<test\nfoo="bar"\nxmlns="foo:bar"/>""", ignore_ns=True)
        assert actual.tag == expected.tag
        assert actual.attrib == expected.attrib

    def test_parse_xml_ns(self):
        expected = Element("{foo:bar}test", {"foo": "bar"})
        actual = parse_xml("""<h:test foo="bar" xmlns:h="foo:bar"/>""")
        assert actual.tag == expected.tag
        assert actual.attrib == expected.attrib

    def test_parse_xml_fail(self):
        with pytest.raises(PluginError):
            parse_xml("1" * 1000)
        with pytest.raises(SyntaxError):
            parse_xml("1" * 1000, exception=SyntaxError)

    def test_parse_xml_validate(self):
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml(
            """<test foo="bar"/>""",
            schema=validate.Schema(xml_element(tag="test", attrib={"foo": str})),
        )
        assert actual.tag == expected.tag
        assert actual.attrib == expected.attrib

    def test_parse_xml_entities_fail(self):
        with pytest.raises(PluginError):
            parse_xml("""<test foo="bar &"/>""")

    def test_parse_xml_entities(self):
        expected = Element("test", {"foo": "bar &"})
        actual = parse_xml(
            """<test foo="bar &"/>""",
            schema=validate.Schema(xml_element(tag="test", attrib={"foo": str})),
            invalid_char_entities=True,
        )
        assert actual.tag == expected.tag
        assert actual.attrib == expected.attrib

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            pytest.param(
                """<?xml version="1.0" encoding="UTF-8"?><test>ä</test>""",
                "ä",
                id="string-utf-8",
            ),
            pytest.param(
                """<test>ä</test>""",
                "ä",
                id="string-unknown",
            ),
            pytest.param(
                b"""<?xml version="1.0" encoding="UTF-8"?><test>\xc3\xa4</test>""",
                "ä",
                id="bytes-utf-8",
            ),
            pytest.param(
                b"""<?xml version="1.0" encoding="ISO-8859-1"?><test>\xe4</test>""",
                "ä",
                id="bytes-iso-8859-1",
            ),
            pytest.param(
                b"""<test>\xc3\xa4</test>""",
                "ä",
                id="bytes-unknown",
            ),
        ],
    )
    def test_parse_xml_encoding(self, content, expected):
        tree = parse_xml(content)
        assert tree.xpath(".//text()") == [expected]

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            pytest.param(
                """<!DOCTYPE html><html><head><meta charset="utf-8"/></head><body>ä</body></html>""",
                "ä",
                id="string-utf-8",
            ),
            pytest.param(
                """<!DOCTYPE html><html><body>ä</body></html>""",
                "ä",
                id="string-unknown",
            ),
            pytest.param(
                b"""<!DOCTYPE html><html><head><meta charset="utf-8"/></head><body>\xc3\xa4</body></html>""",
                "ä",
                id="bytes-utf-8",
            ),
            pytest.param(
                b"""<!DOCTYPE html><html><head><meta charset="ISO-8859-1"/></head><body>\xe4</body></html>""",
                "ä",
                id="bytes-iso-8859-1",
            ),
            pytest.param(
                b"""<!DOCTYPE html><html><body>\xc3\xa4</body></html>""",
                "Ã¤",
                id="bytes-unknown",
            ),
        ],
    )
    def test_parse_html_encoding(self, content, expected):
        tree = parse_html(content)
        assert tree.xpath(".//body/text()") == [expected]

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            pytest.param(
                """<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html><html><body>ä?></body></html>""",
                "ä?>",
                id="string",
            ),
            pytest.param(
                b"""<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html><html><body>\xc3\xa4?></body></html>""",
                "ä?>",
                id="bytes-utf-8",
            ),
            pytest.param(
                b"""<?xml version="1.0" encoding="ISO-8859-1"?><!DOCTYPE html><html><body>\xe4?></body></html>""",
                "ä?>",
                id="bytes-iso-8859-1",
            ),
            pytest.param(
                b"""<?xml version="1.0"?><!DOCTYPE html><html><body>\xc3\xa4?></body></html>""",
                "ä?>",
                id="bytes-unknown",
            ),
        ],
    )
    def test_parse_html_xhtml5(self, content, expected):
        tree = parse_html(content)
        assert tree.xpath(".//body/text()") == [expected]

    def test_parse_qsd(self):
        assert parse_qsd("test=1&foo=bar", schema=validate.Schema({"test": str, "foo": "bar"})) == {"test": "1", "foo": "bar"}
