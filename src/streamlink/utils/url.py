from __future__ import annotations

import re
from enum import IntEnum
from functools import cache
from typing import Mapping
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlparse, urlunparse


_re_scheme = re.compile(r"""^[a-z0-9][a-z0-9.+-]*://""", re.IGNORECASE)


class _ProxyMatcherPriority(IntEnum):
    ALL_SCHEME_WITHOUT_NETLOC = 1
    ALL_SCHEME_WITH_NETLOC = 2
    SPECIFIC_SCHEME_WITHOUT_NETLOC = 3
    SPECIFIC_SCHEME_WITH_NETLOC = 4


@cache
def _proxymatcher_to_prio_and_pattern(matcher: str) -> tuple[int, re.Pattern] | None:
    if not matcher or matcher == "all":
        return _ProxyMatcherPriority.ALL_SCHEME_WITHOUT_NETLOC, _re_scheme

    if matcher in ("http", "https"):
        return _ProxyMatcherPriority.SPECIFIC_SCHEME_WITHOUT_NETLOC, re.compile(f"^{matcher}://", re.IGNORECASE)

    if not _re_scheme.match(matcher):
        matcher = f"all://{matcher}"

    try:
        parsed = urlparse(matcher)
        hostname: str = parsed.hostname or ""
        portnumber: int = parsed.port or 0
    except ValueError:
        return None

    netloc = parsed.netloc
    if not hostname or hostname == "*":
        netloc = ".+?"
        hostname = ""
    elif netloc.startswith("*."):
        netloc = f".+\\.{re.escape(netloc[2:])}"
    elif netloc.startswith("*"):
        netloc = f"(?:.+\\.)?{re.escape(netloc[1:])}"
    else:
        netloc = re.escape(netloc)

    if not hostname and portnumber > 0:
        netloc += f":{portnumber}"
    elif parsed.scheme == "http":
        netloc += "(?::80)?"
    elif parsed.scheme == "https":
        netloc += "(?::443)?"

    if parsed.scheme == "all":
        scheme = "[a-z0-9][a-z0-9.+-]*"
        priority = _ProxyMatcherPriority.ALL_SCHEME_WITH_NETLOC
    else:
        scheme = re.escape(parsed.scheme)
        priority = _ProxyMatcherPriority.SPECIFIC_SCHEME_WITH_NETLOC

    pattern = re.compile(f"^{scheme}://{netloc}(?:/.*)?$", re.IGNORECASE)

    return priority, pattern


def select_proxy(url: str, proxies: Mapping[str, str]) -> str | None:
    """
    Replacement function for `requests.utils.select_proxy`, with support for wildcards in proxy URL matchers.
    Support for wildcards means that the lookup time now scales linearly with the size of `proxies`.
    """

    proxies = proxies or {}
    urlparts = urlparse(url)
    if urlparts.hostname is None:
        return proxies.get(urlparts.scheme, proxies.get("all"))

    proxy: str | None = None
    current: int = 0
    for key, value in proxies.items():
        if (prio_and_pattern := _proxymatcher_to_prio_and_pattern(key)) is None:
            continue
        priority, pattern = prio_and_pattern
        if pattern.match(url) and priority > current:
            current = priority
            proxy = value
            if current >= _ProxyMatcherPriority.SPECIFIC_SCHEME_WITH_NETLOC:
                break

    return proxy


def absolute_url(baseurl, url):
    parsed = urlparse(url)
    if not parsed.scheme:
        url = urljoin(baseurl, url)

    return url


def prepend_www(url):
    parsed = urlparse(url)
    if not parsed.netloc.startswith("www."):
        # noinspection PyProtectedMember
        parsed = parsed._replace(netloc=f"www.{parsed.netloc}")

    return parsed.geturl()


def update_scheme(current: str, target: str, force: bool = True) -> str:
    """
    Take the scheme from the current URL and apply it to the target URL if it is missing
    :param current: current URL
    :param target: target URL
    :param force: always apply the current scheme to the target, even if a target scheme exists
    :return: target URL with the current URL's scheme
    """
    target_p = urlparse(target)

    if (
        # target URLs with implicit scheme and netloc including a port: ("http://", "foo.bar:1234") -> "http://foo.bar:1234"
        # urllib.parse.urlparse has incorrect behavior in py<3.9, so we'll have to use a regex here
        # py>=3.9: urlparse("127.0.0.1:1234") == ParseResult(scheme='127.0.0.1', netloc='', path='1234', ...)
        # py<3.9 : urlparse("127.0.0.1:1234") == ParseResult(scheme='', netloc='', path='127.0.0.1:1234', ...)
        not _re_scheme.search(target) and not target.startswith("//")
        # target URLs without scheme and without netloc: ("http://", "foo.bar/foo") -> "http://foo.bar/foo"
        or not target_p.scheme and not target_p.netloc
    ):  # fmt: skip
        return f"{urlparse(current).scheme}://{urlunparse(target_p)}"

    # target URLs without scheme but with netloc: ("http://", "//foo.bar/foo") -> "http://foo.bar/foo"
    if not target_p.scheme:
        return f"{urlparse(current).scheme}:{urlunparse(target_p)}"

    # target URLs with scheme
    # override the target scheme
    if force:
        return urlunparse(target_p._replace(scheme=urlparse(current).scheme))

    # keep the target scheme
    return target


def url_equal(
    first,
    second,
    ignore_scheme=False,
    ignore_netloc=False,
    ignore_path=False,
    ignore_params=False,
    ignore_query=False,
    ignore_fragment=False,
):
    """
    Compare two URLs and return True if they are equal, some parts of the URLs can be ignored
    :param first: URL
    :param second: URL
    :param ignore_scheme: ignore the scheme
    :param ignore_netloc: ignore the netloc
    :param ignore_path: ignore the path
    :param ignore_params: ignore the params
    :param ignore_query: ignore the query string
    :param ignore_fragment: ignore the fragment
    :return: result of comparison
    """
    # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>

    firstp = urlparse(first)
    secondp = urlparse(second)

    return (
        (firstp.scheme == secondp.scheme or ignore_scheme)
        and (firstp.netloc == secondp.netloc or ignore_netloc)
        and (firstp.path == secondp.path or ignore_path)
        and (firstp.params == secondp.params or ignore_params)
        and (firstp.query == secondp.query or ignore_query)
        and (firstp.fragment == secondp.fragment or ignore_fragment)
    )


def url_concat(base, *parts, **kwargs):
    """
    Join extra paths to a URL, does not join absolute paths
    :param base: the base URL
    :param parts: a list of the parts to join
    :param allow_fragments: include url fragments
    :return: the joined URL
    """
    allow_fragments = kwargs.get("allow_fragments", True)
    for part in parts:
        base = urljoin(base.rstrip("/") + "/", part.strip("/"), allow_fragments)
    return base


def update_qsd(url, qsd=None, remove=None, keep_blank_values=True, safe="", quote_via=quote_plus):
    """
    Update or remove keys from a query string in a URL

    :param url: URL to update
    :param qsd: dict of keys to update, a None value leaves it unchanged
    :param remove: list of keys to remove, or "*" to remove all
                   note: updated keys are never removed, even if unchanged
    :param keep_blank_values: whether params with blank values should be kept or not
    :param safe: string of reserved encoding characters, passed to the quote_via function
    :param quote_via: function which encodes query string keys and values. Default: urllib.parse.quote_plus
    :return: updated URL
    """
    qsd = qsd or {}
    remove = remove or []

    # parse current query string
    parsed = urlparse(url)
    current_qsd = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # * removes all possible keys
    if remove == "*":
        remove = list(current_qsd.keys())

    # remove keys before updating, but leave updated keys untouched
    for key in remove:
        if key not in qsd:
            del current_qsd[key]

    # and update the query string
    for key, value in qsd.items():
        if value is not None:
            current_qsd[key] = value

    for key, value in list(current_qsd.items()):  # use list() to create a view of the current_qsd
        if not value and not keep_blank_values and key not in qsd:
            del current_qsd[key]

    query = urlencode(query=current_qsd, safe=safe, quote_via=quote_via)

    return parsed._replace(query=query).geturl()
