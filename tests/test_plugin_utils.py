from __future__ import unicode_literals
import sys

from streamlink.plugin.api.utils import itertags

if sys.version_info[0:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest


class TestPluginUtil(unittest.TestCase):
    test_html = """
<title>Title</title>
<meta property="og:type" content= "website" />
<meta property="og:url" content="http://test.se/"/>
<meta property="og:site_name" content="Test" />
<script src="https://test.se/test.js"></script>
<link rel="stylesheet" type="text/css" href="https://test.se/test.css">
<script>Tester.ready(function () {
alert("Hello, world!"); });</script>
<a 
href="http://test.se/foo">bar</a>
        """

    def test_itertags_single_text(self):
        title = list(itertags(self.test_html, "title"))
        self.assertTrue(len(title), 1)
        self.assertEqual(title[0].tag, "title")
        self.assertEqual(title[0].text, "Title")
        self.assertEqual(title[0].attributes, {})

    def test_itertags_attrs_text(self):
        script = list(itertags(self.test_html, "script"))
        self.assertTrue(len(script), 2)
        self.assertEqual(script[0].tag, "script")
        self.assertEqual(script[0].text, "")
        self.assertEqual(script[0].attributes, {"src": "https://test.se/test.js"})

        self.assertEqual(script[1].tag, "script")
        self.assertEqual(script[1].text.strip(), """Tester.ready(function () {\nalert("Hello, world!"); });""")
        self.assertEqual(script[1].attributes, {})

    def test_itertags_multi_attrs(self):
        metas = list(itertags(self.test_html, "meta"))
        self.assertTrue(len(metas), 3)
        self.assertTrue(all(meta.tag == "meta" for meta in metas))

        self.assertEqual(metas[0].text, None)
        self.assertEqual(metas[1].text, None)
        self.assertEqual(metas[2].text, None)

        self.assertEqual(metas[0].attributes, {"property": "og:type", "content": "website"})
        self.assertEqual(metas[1].attributes, {"property": "og:url", "content": "http://test.se/"})
        self.assertEqual(metas[2].attributes, {"property": "og:site_name", "content": "Test"})

    def test_multi_line_a(self):
        anchor = list(itertags(self.test_html, "a"))
        self.assertTrue(len(anchor), 1)
        self.assertEqual(anchor[0].tag, "a")
        self.assertEqual(anchor[0].text, "bar")
        self.assertEqual(anchor[0].attributes, {"href": "http://test.se/foo"})

    def test_no_end_tag(self):
        links = list(itertags(self.test_html, "link"))
        self.assertTrue(len(links), 1)
        self.assertEqual(links[0].tag, "link")
        self.assertEqual(links[0].text, None)
        self.assertEqual(links[0].attributes, {"rel": "stylesheet",
                                               "type": "text/css",
                                               "href": "https://test.se/test.css"})



