import json
import re
from urllib.parse import parse_qsl

from lxml.etree import HTML, XML

from streamlink.compat import detect_encoding
from streamlink.exceptions import PluginError


def _parse(parser, data, name, exception, schema, *args, **kwargs):
    try:
        parsed = parser(data, *args, **kwargs)
    except Exception as err:
        snippet = repr(data)
        if len(snippet) > 35:
            snippet = f"{snippet[:35]} ..."

        raise exception(f"Unable to parse {name}: {err} ({snippet})")  # noqa: B904

    if schema:
        parsed = schema.validate(parsed, name=name, exception=exception)

    return parsed


def parse_json(
    data,
    name="JSON",
    exception=PluginError,
    schema=None,
    *args,
    **kwargs,
):
    """Wrapper around json.loads.

    Provides these extra features:
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    return _parse(json.loads, data, name, exception, schema, *args, **kwargs)


def parse_html(
    data,
    name="HTML",
    exception=PluginError,
    schema=None,
    *args,
    **kwargs,
):
    """Wrapper around lxml.etree.HTML with some extras.

    Provides these extra features:
     - Removes XML declarations of invalid XHTML5 documents
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    # strip XML text declarations from XHTML5 documents which were incorrectly defined as HTML5
    is_bytes = isinstance(data, bytes)
    if data and data.lstrip()[:5].lower() == (b"<?xml" if is_bytes else "<?xml"):
        if is_bytes:
            # get the document's encoding using the "encoding" attribute value of the XML text declaration
            match = re.match(rb"^\s*<\?xml\s.*?encoding=(?P<q>[\'\"])(?P<encoding>.+?)(?P=q).*?\?>", data, re.IGNORECASE)
            if match:
                encoding_value = detect_encoding(match["encoding"])["encoding"]
                encoding = match["encoding"].decode(encoding_value)
            else:
                # no "encoding" attribute: try to figure out encoding from the document's content
                encoding = detect_encoding(data)["encoding"]

            data = data.decode(encoding)

        data = re.sub(r"^\s*<\?xml.+?\?>", "", data)

    return _parse(HTML, data, name, exception, schema, *args, **kwargs)


def parse_xml(
    data,
    ignore_ns=False,
    invalid_char_entities=False,
    name="XML",
    exception=PluginError,
    schema=None,
    *args,
    **kwargs,
):
    """Wrapper around lxml.etree.XML with some extras.

    Provides these extra features:
     - Handles incorrectly encoded XML
     - Allows stripping namespace information
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    if isinstance(data, str):
        data = bytes(data, "utf8")
    if ignore_ns:
        data = re.sub(rb"\s+xmlns=\"(.+?)\"", b"", data)
    if invalid_char_entities:
        data = re.sub(rb"&(?!(?:#(?:[0-9]+|[Xx][0-9A-Fa-f]+)|[A-Za-z0-9]+);)", b"&amp;", data)

    return _parse(XML, data, name, exception, schema, *args, **kwargs)


def parse_qsd(
    data,
    name="query string",
    exception=PluginError,
    schema=None,
    *args,
    **kwargs,
):
    """Parses a query string into a dict.

    Provides these extra features:
     - Unlike parse_qs and parse_qsl, duplicate keys are not preserved in favor of a simpler return value
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    return _parse(lambda d: dict(parse_qsl(d, *args, **kwargs)), data, name, exception, schema)
