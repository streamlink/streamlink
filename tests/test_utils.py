import sys
import os.path

from streamlink.plugin.api.validate import xml_element, text
from streamlink.utils import update_scheme, url_equal, search_dict, load_module

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from streamlink import PluginError
from streamlink.plugin.api import validate
from streamlink.utils import *

import unittest

# used in the import test to verify that this module was imported
__test_marker__ = "test_marker"


class TestUtil(unittest.TestCase):
    def test_verifyjson(self):
        self.assertEqual(verifyjson({"test": 1}, "test"),
                         1)

        self.assertRaises(PluginError, verifyjson, None, "test")
        self.assertRaises(PluginError, verifyjson, {}, "test")

    def test_absolute_url(self):
        self.assertEqual("http://test.se/test",
                         absolute_url("http://test.se", "/test"))
        self.assertEqual("http://test2.se/test",
                         absolute_url("http://test.se", "http://test2.se/test"))

    def test_prepend_www(self):
        self.assertEqual("http://www.test.se/test",
                         prepend_www("http://test.se/test"))
        self.assertEqual("http://www.test.se",
                         prepend_www("http://www.test.se"))

    def test_parse_json(self):
        self.assertEqual({}, parse_json("{}"))
        self.assertEqual({"test": 1}, parse_json("""{"test": 1}"""))
        self.assertEqual({"test": 1}, parse_json("""{"test": 1}""", schema=validate.Schema({"test": 1})))
        self.assertRaises(PluginError, parse_json, """{"test: 1}""")
        self.assertRaises(IOError, parse_json, """{"test: 1}""", exception=IOError)
        self.assertRaises(PluginError, parse_json, """{"test: 1}""" * 10)

    def test_parse_xml(self):
        expected = ET.Element("test", {"foo": "bar"})
        actual = parse_xml(u"""<test foo="bar"/>""", ignore_ns=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_ns_ignore(self):
        expected = ET.Element("test", {"foo": "bar"})
        actual = parse_xml(u"""<test foo="bar" xmlns="foo:bar"/>""", ignore_ns=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_ns(self):
        expected = ET.Element("{foo:bar}test", {"foo": "bar"})
        actual = parse_xml(u"""<h:test foo="bar" xmlns:h="foo:bar"/>""")
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_fail(self):
        self.assertRaises(PluginError,
                          parse_xml, u"1" * 1000)
        self.assertRaises(IOError,
                          parse_xml, u"1" * 1000, exception=IOError)

    def test_parse_xml_validate(self):
        expected = ET.Element("test", {"foo": "bar"})
        actual = parse_xml(u"""<test foo="bar"/>""",
                           schema=validate.Schema(xml_element(tag="test", attrib={"foo": text})))
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_entities_fail(self):
        self.assertRaises(PluginError,
                          parse_xml, u"""<test foo="bar &"/>""")


    def test_parse_xml_entities(self):
        expected = ET.Element("test", {"foo": "bar &"})
        actual = parse_xml(u"""<test foo="bar &"/>""",
                           schema=validate.Schema(xml_element(tag="test", attrib={"foo": text})),
                           invalid_char_entities=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)


    def test_parse_qsd(self):
        self.assertEqual(
            {"test": "1", "foo": "bar"},
            parse_qsd("test=1&foo=bar", schema=validate.Schema({"test": validate.text, "foo": "bar"})))

    def test_update_scheme(self):
        self.assertEqual(
            "https://example.com/foo",  # becomes https
            update_scheme("https://other.com/bar", "//example.com/foo")
        )
        self.assertEqual(
            "http://example.com/foo",  # becomes http
            update_scheme("http://other.com/bar", "//example.com/foo")
        )
        self.assertEqual(
            "http://example.com/foo",  # remains unchanged
            update_scheme("https://other.com/bar", "http://example.com/foo")
        )
        self.assertEqual(
            "https://example.com/foo",  # becomes https
            update_scheme("https://other.com/bar", "example.com/foo")
        )

    def test_url_equal(self):
        self.assertTrue(url_equal("http://test.com/test", "http://test.com/test"))
        self.assertFalse(url_equal("http://test.com/test", "http://test.com/test2"))

        self.assertTrue(url_equal("http://test.com/test", "http://test.com/test2", ignore_path=True))
        self.assertTrue(url_equal("http://test.com/test", "https://test.com/test", ignore_scheme=True))
        self.assertFalse(url_equal("http://test.com/test", "https://test.com/test"))

        self.assertTrue(url_equal("http://test.com/test", "http://test.com/test#hello", ignore_fragment=True))
        self.assertTrue(url_equal("http://test.com/test", "http://test2.com/test", ignore_netloc=True))
        self.assertFalse(url_equal("http://test.com/test", "http://test2.com/test1", ignore_netloc=True))

    def test_search_dict(self):

        self.assertSequenceEqual(
            list(search_dict(["one", "two"], "one")),
            []
        )
        self.assertSequenceEqual(
            list(search_dict({"two": "test2"}, "one")),
            []
        )
        self.assertSequenceEqual(
            list(search_dict({"one": "test1", "two": "test2"}, "one")),
            ["test1"]
        )
        self.assertSequenceEqual(
            list(search_dict({"one": {"inner": "test1"}, "two": "test2"}, "inner")),
            ["test1"]
        )
        self.assertSequenceEqual(
            list(search_dict({"one": [{"inner": "test1"}], "two": "test2"}, "inner")),
            ["test1"]
        )
        self.assertSequenceEqual(
            list(sorted(search_dict({"one": [{"inner": "test1"}], "two": {"inner": "test2"}}, "inner"))),
            list(sorted(["test1", "test2"]))
        )

    def test_load_module_non_existent(self):
        self.assertRaises(ImportError, load_module, "non_existent_module", os.path.dirname(__file__))

    def test_load_module(self):
        self.assertEqual(
            sys.modules[__name__].__test_marker__,
            load_module(__name__.split(".")[-1], os.path.dirname(__file__)).__test_marker__
        )
