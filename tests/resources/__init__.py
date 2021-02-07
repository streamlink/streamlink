import codecs
import os.path
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from io import BytesIO


__here__ = os.path.abspath(os.path.dirname(__file__))


def _parse_xml(data, strip_ns=False):
    data = bytearray(data, "utf8")
    try:
        it = ET.iterparse(BytesIO(data))
        for _, el in it:
            if '}' in el.tag and strip_ns:  # pragma: no branch
                # strip all namespaces
                el.tag = el.tag.split('}', 1)[1]
        return it.root
    except Exception as err:  # pragma: no cover
        snippet = repr(data)
        if len(snippet) > 35:
            snippet = snippet[:35] + " ..."

        raise ValueError("Unable to parse XML: {0} ({1})".format(err, snippet))


@contextmanager
def text(path, encoding="utf8"):
    with codecs.open(os.path.join(__here__, path), 'r', encoding=encoding) as resource_fh:
        yield resource_fh


@contextmanager
def xml(path, encoding="utf8"):
    with codecs.open(os.path.join(__here__, path), 'r', encoding=encoding) as resource_fh:
        yield _parse_xml(resource_fh.read(), strip_ns=True)
