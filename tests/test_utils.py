import base64
import os.path
import sys
import unittest

from lxml.etree import Element

from streamlink.exceptions import PluginError
from streamlink.plugin.api import validate
from streamlink.plugin.api.validate import xml_element
from streamlink.utils import (
    absolute_url,
    load_module,
    parse_json,
    parse_qsd,
    parse_xml,
    prepend_www,
    rtmpparse,
    search_dict,
    swfdecompress,
    verifyjson,
)

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
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml("""<test foo="bar"/>""", ignore_ns=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_ns_ignore(self):
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml("""<test foo="bar" xmlns="foo:bar"/>""", ignore_ns=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_ns_ignore_tab(self):
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml("""<test	foo="bar"	xmlns="foo:bar"/>""", ignore_ns=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_ns(self):
        expected = Element("{foo:bar}test", {"foo": "bar"})
        actual = parse_xml("""<h:test foo="bar" xmlns:h="foo:bar"/>""")
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_fail(self):
        self.assertRaises(PluginError,
                          parse_xml, "1" * 1000)
        self.assertRaises(IOError,
                          parse_xml, "1" * 1000, exception=IOError)

    def test_parse_xml_validate(self):
        expected = Element("test", {"foo": "bar"})
        actual = parse_xml("""<test foo="bar"/>""",
                           schema=validate.Schema(xml_element(tag="test", attrib={"foo": str})))
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_xml_entities_fail(self):
        self.assertRaises(PluginError,
                          parse_xml, """<test foo="bar &"/>""")

    def test_parse_xml_entities(self):
        expected = Element("test", {"foo": "bar &"})
        actual = parse_xml("""<test foo="bar &"/>""",
                           schema=validate.Schema(xml_element(tag="test", attrib={"foo": str})),
                           invalid_char_entities=True)
        self.assertEqual(expected.tag, actual.tag)
        self.assertEqual(expected.attrib, actual.attrib)

    def test_parse_qsd(self):
        self.assertEqual(
            {"test": "1", "foo": "bar"},
            parse_qsd("test=1&foo=bar", schema=validate.Schema({"test": str, "foo": "bar"})))

    def test_rtmpparse(self):
        self.assertEqual(
            ("rtmp://testserver.com:1935/app", "playpath?arg=1"),
            rtmpparse("rtmp://testserver.com/app/playpath?arg=1"))
        self.assertEqual(
            ("rtmp://testserver.com:1935/long/app", "playpath?arg=1"),
            rtmpparse("rtmp://testserver.com/long/app/playpath?arg=1"))
        self.assertEqual(
            ("rtmp://testserver.com:1935/app", None),
            rtmpparse("rtmp://testserver.com/app"))

    def test_swf_decompress(self):
        # FYI, not a valid SWF
        swf = b"FWS " + b"0000" + b"test data 12345"
        swf_compressed = b"CWS " + b"0000" + base64.b64decode(b"eJwrSS0uUUhJLElUMDQyNjEFACpTBJo=")
        self.assertEqual(swf, swfdecompress(swf_compressed))
        self.assertEqual(swf, swfdecompress(swf))

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
