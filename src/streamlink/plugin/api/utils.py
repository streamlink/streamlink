"""Useful wrappers and other tools."""
import re
from collections import namedtuple

from ...utils import parse_qsd as parse_query, parse_json, parse_xml

__all__ = ["parse_json", "parse_xml", "parse_query"]


tag_re = re.compile('''(?=<(?P<tag>[a-zA-Z]+)(?P<attr>.*?)(?P<end>/)?>(?:(?P<inner>.*?)</\s*(?P=tag)\s*>)?)''',
                    re.MULTILINE | re.DOTALL)
attr_re = re.compile('''\s*(?P<key>[\w-]+)\s*(?:=\s*(?P<quote>["']?)(?P<value>.*?)(?P=quote)\s*)?''')
Tag = namedtuple("Tag", "tag attributes text")


def itertags(html, tag):
    """
    Brute force regex based HTML tag parser. This is a rough-and-ready searcher to find HTML tags when
    standards compliance is not required. Will find tags that are commented out, or inside script tag etc.
    :param html: HTML page
    :param tag: tag name to find
    :return: generator with Tags
    """
    for match in tag_re.finditer(html):
        if match.group("tag") == tag:
            attrs = dict((a.group("key").lower(), a.group("value")) for a in attr_re.finditer(match.group("attr")))
            yield Tag(match.group("tag"), attrs, match.group("inner"))
