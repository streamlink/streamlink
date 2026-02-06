# ruff: noqa: RUF067
from streamlink.compat import deprecated


_msg = "Importing from the 'streamlink.utils' package has been deprecated. Import from its submodules instead."

deprecated({
    "LRUCache": ("streamlink.utils.cache.LRUCache", None, _msg),
    "search_dict": ("streamlink.utils.data.search_dict", None, _msg),
    "load_module": ("streamlink.utils.module.load_module", None, _msg),
    "NamedPipe": ("streamlink.utils.named_pipe.NamedPipe", None, _msg),
    "parse_html": ("streamlink.utils.parse.parse_html", None, _msg),
    "parse_json": ("streamlink.utils.parse.parse_json", None, _msg),
    "parse_qsd": ("streamlink.utils.parse.parse_qsd", None, _msg),
    "parse_xml": ("streamlink.utils.parse.parse_xml", None, _msg),
    "absolute_url": ("streamlink.utils.url.absolute_url", None, _msg),
    "prepend_www": ("streamlink.utils.url.prepend_www", None, _msg),
    "update_qsd": ("streamlink.utils.url.update_qsd", None, _msg),
    "update_scheme": ("streamlink.utils.url.update_scheme", None, _msg),
    "url_concat": ("streamlink.utils.url.url_concat", None, _msg),
    "url_equal": ("streamlink.utils.url.url_equal", None, _msg),
})

del _msg
