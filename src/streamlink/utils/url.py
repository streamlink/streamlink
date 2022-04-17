import re
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlparse, urlunparse


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


_re_uri_implicit_scheme = re.compile(r"""^[a-z0-9][a-z0-9.+-]*://""", re.IGNORECASE)


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
        not _re_uri_implicit_scheme.search(target) and not target.startswith("//")
        # target URLs without scheme and netloc: ("http://", "foo.bar/foo") -> "http://foo.bar/foo"
        or not target_p.scheme and not target_p.netloc
    ):
        return f"{urlparse(current).scheme}://{urlunparse(target_p)}"

    # target URLs without scheme but with netloc: ("http://", "//foo.bar/foo") -> "http://foo.bar/foo"
    if not target_p.scheme and target_p.netloc:
        return f"{urlparse(current).scheme}:{urlunparse(target_p)}"

    # target URLs with scheme
    # override the target scheme
    if force:
        return urlunparse(target_p._replace(scheme=urlparse(current).scheme))

    # keep the target scheme
    return target


def url_equal(first, second, ignore_scheme=False, ignore_netloc=False, ignore_path=False, ignore_params=False,
              ignore_query=False, ignore_fragment=False):
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
