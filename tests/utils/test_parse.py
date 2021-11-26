import unittest

from lxml.etree import Element

from streamlink.exceptions import PluginError
from streamlink.plugin.api import validate
from streamlink.plugin.api.validate import xml_element
from streamlink.utils.parse import parse_html, parse_json, parse_qsd, parse_xml


class TestUtilsParse(unittest.TestCase):
    def test_parse_json(self):
        self.assertEqual({}, parse_json("{}"))
        self.assertEqual({"test": 1}, parse_json("""{"test": 1}"""))
        self.assertEqual({"test": 1}, parse_json("""{"test": 1}""", schema=validate.Schema({"test": 1})))
        self.assertRaises(PluginError, parse_json, """{"test: 1}""")
        self.assertRaises(IOError, parse_json, """{"test: 1}""", exception=IOError)
        self.assertRaises(PluginError, parse_json, """{"test: 1}""" * 10)

    def test_parse_xml(self):
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml("""<test foo="bar"/>""", ignore_ns=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_ns_ignore(self):
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml("""<test foo="bar" xmlns="foo:bar"/>""", ignore_ns=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

        actual = parse_xml("""<test	foo="bar"	xmlns="foo:bar"/>""", ignore_ns=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

        actual = parse_xml("""<test\nfoo="bar"\nxmlns="foo:bar"/>""", ignore_ns=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_ns(self):
        expected = Element("{foo:bar}test", {"foo": "bar"})
        actual = parse_xml("""<h:test foo="bar" xmlns:h="foo:bar"/>""")
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_fail(self):
        self.assertRaises(PluginError, parse_xml, "1" * 1000)
        self.assertRaises(IOError, parse_xml, "1" * 1000, exception=IOError)

    def test_parse_xml_validate(self):
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml(
            """<test foo="bar"/>""",
            schema=validate.Schema(xml_element(tag="test", attrib={"foo": str}))
        )
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_entities_fail(self):
        self.assertRaises(PluginError, parse_xml, """<test foo="bar &"/>""")

    def test_parse_xml_entities(self):
        expected = Element("test", {"foo": "bar &"})
        actual = parse_xml(
            """<test foo="bar &"/>""",
            schema=validate.Schema(xml_element(tag="test", attrib={"foo": str})),
            invalid_char_entities=True
        )
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_encoding(self):
        tree = parse_xml("""<?xml version="1.0" encoding="UTF-8"?><test>ä</test>""")
        self.assertEqual(tree.xpath(".//text()"), ["ä"])
        tree = parse_xml("""<test>ä</test>""")
        self.assertEqual(tree.xpath(".//text()"), ["ä"])
        tree = parse_xml(b"""<?xml version="1.0" encoding="UTF-8"?><test>\xC3\xA4</test>""")
        self.assertEqual(tree.xpath(".//text()"), ["ä"])
        tree = parse_xml(b"""<test>\xC3\xA4</test>""")
        self.assertEqual(tree.xpath(".//text()"), ["ä"])

    def test_parse_html_encoding(self):
        tree = parse_html("""<!DOCTYPE html><html><head><meta charset="utf-8"/></head><body>ä</body></html>""")
        self.assertEqual(tree.xpath(".//body/text()"), ["ä"])
        tree = parse_html("""<!DOCTYPE html><html><body>ä</body></html>""")
        self.assertEqual(tree.xpath(".//body/text()"), ["ä"])
        tree = parse_html(b"""<!DOCTYPE html><html><meta charset="utf-8"/><body>\xC3\xA4</body></html>""")
        self.assertEqual(tree.xpath(".//body/text()"), ["ä"])
        tree = parse_html(b"""<!DOCTYPE html><html><body>\xC3\xA4</body></html>""")
        self.assertEqual(tree.xpath(".//body/text()"), ["Ã¤"])

    def test_parse_html_xhtml5(self):
        tree = parse_html("""<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html><html><body>ä?></body></html>""")
        self.assertEqual(tree.xpath(".//body/text()"), ["ä?>"])
        tree = parse_html(b"""<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html><html><body>\xC3\xA4?></body></html>""")
        self.assertEqual(tree.xpath(".//body/text()"), ["ä?>"])

    def test_parse_qsd(self):
        self.assertEqual(
            {"test": "1", "foo": "bar"},
            parse_qsd("test=1&foo=bar", schema=validate.Schema({"test": str, "foo": "bar"}))
        )
