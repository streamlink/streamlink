import re
import time
import warnings
from typing import Any, Dict, Pattern, Tuple

import requests.adapters
import urllib3
from requests import PreparedRequest, Request, Session
from requests.adapters import HTTPAdapter

from streamlink.exceptions import PluginError, StreamlinkDeprecationWarning
from streamlink.packages.requests_file import FileAdapter
from streamlink.plugin.api import useragents
from streamlink.utils.parse import parse_json, parse_xml


try:
    from urllib3.util import create_urllib3_context  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    # urllib3 <2.0.0 compat import
    from urllib3.util.ssl_ import create_urllib3_context


# urllib3>=2.0.0: enforce_content_length now defaults to True (keep the override for backwards compatibility)
class _HTTPResponse(urllib3.response.HTTPResponse):
    def __init__(self, *args, **kwargs):
        # Always enforce content length validation!
        # This fixes a bug in requests which doesn't raise errors on HTTP responses where
        # the "Content-Length" header doesn't match the response's body length.
        # https://github.com/psf/requests/issues/4956#issuecomment-573325001
        #
        # Summary:
        # This bug is related to urllib3.response.HTTPResponse.stream() which calls urllib3.response.HTTPResponse.read() as
        # a wrapper for http.client.HTTPResponse.read(amt=...), where no http.client.IncompleteRead exception gets raised
        # due to "backwards compatiblity" of an old bug if a specific amount is attempted to be read on an incomplete response.
        #
        # urllib3.response.HTTPResponse.read() however has an additional check implemented via the enforce_content_length
        # parameter, but it doesn't check by default and requests doesn't set the parameter for enabling it either.
        #
        # Fix this by overriding urllib3.response.HTTPResponse's constructor and always setting enforce_content_length to True,
        # as there is no way to make requests set this parameter on its own.
        kwargs["enforce_content_length"] = True
        super().__init__(*args, **kwargs)


# override all urllib3.response.HTTPResponse references in requests.adapters.HTTPAdapter.send
urllib3.connectionpool.HTTPConnectionPool.ResponseCls = _HTTPResponse  # type: ignore[attr-defined]
requests.adapters.HTTPResponse = _HTTPResponse  # type: ignore[misc]


# Never convert percent-encoded characters to uppercase in urllib3>=1.25.8.
# This is required for sites which compare request URLs byte by byte and return different responses depending on that.
# Older versions of urllib3 are not compatible with this override and will always convert to uppercase characters.
#
# https://datatracker.ietf.org/doc/html/rfc3986#section-2.1
# > The uppercase hexadecimal digits 'A' through 'F' are equivalent to
# > the lowercase digits 'a' through 'f', respectively.  If two URIs
# > differ only in the case of hexadecimal digits used in percent-encoded
# > octets, they are equivalent.  For consistency, URI producers and
# > normalizers should use uppercase hexadecimal digits for all percent-
# > encodings.
class Urllib3UtilUrlPercentReOverride:
    # urllib3>=2.0.0: _PERCENT_RE, urllib3<2.0.0: PERCENT_RE
    _re_percent_encoding: Pattern \
        = getattr(urllib3.util.url, "_PERCENT_RE", getattr(urllib3.util.url, "PERCENT_RE", re.compile(r"%[a-fA-F0-9]{2}")))

    # urllib3>=1.25.8
    # https://github.com/urllib3/urllib3/blame/1.25.8/src/urllib3/util/url.py#L219-L227
    @classmethod
    def subn(cls, repl: Any, string: str, count: Any = None) -> Tuple[str, int]:
        return string, len(cls._re_percent_encoding.findall(string))


# urllib3>=2.0.0: _PERCENT_RE, urllib3<2.0.0: PERCENT_RE
urllib3.util.url._PERCENT_RE = urllib3.util.url.PERCENT_RE = Urllib3UtilUrlPercentReOverride  # type: ignore[attr-defined]


# requests.Request.__init__ keywords, except for "hooks"
_VALID_REQUEST_ARGS = "method", "url", "headers", "files", "data", "params", "auth", "cookies", "json"


class HTTPSession(Session):
    params: Dict

    def __init__(self):
        super().__init__()

        self.headers["User-Agent"] = useragents.FIREFOX
        self.timeout = 20.0

        self.mount("file://", FileAdapter())

    @classmethod
    def determine_json_encoding(cls, sample: bytes):
        """
        Determine which Unicode encoding the JSON text sample is encoded with

        RFC4627 suggests that the encoding of JSON text can be determined
        by checking the pattern of NULL bytes in first 4 octets of the text.
        https://datatracker.ietf.org/doc/html/rfc4627#section-3

        :param sample: a sample of at least 4 bytes of the JSON text
        :return: the most likely encoding of the JSON text
        """
        warnings.warn("Deprecated HTTPSession.determine_json_encoding() call", StreamlinkDeprecationWarning, stacklevel=1)
        data = int.from_bytes(sample[:4], "big")

        if data & 0xffffff00 == 0:
            return "UTF-32BE"
        elif data & 0xff00ff00 == 0:
            return "UTF-16BE"
        elif data & 0x00ffffff == 0:
            return "UTF-32LE"
        elif data & 0x00ff00ff == 0:
            return "UTF-16LE"
        else:
            return "UTF-8"

    @classmethod
    def json(cls, res, *args, **kwargs):
        """Parses JSON from a response."""
        if res.encoding is None:
            # encoding is unknown: let ``json.loads`` figure it out from the bytes data via ``json.detect_encoding``
            return parse_json(res.content, *args, **kwargs)
        else:
            # encoding is explicitly set: get the decoded string value and let ``json.loads`` parse it
            return parse_json(res.text, *args, **kwargs)

    @classmethod
    def xml(cls, res, *args, **kwargs):
        """Parses XML from a response."""
        return parse_xml(res.text, *args, **kwargs)

    def resolve_url(self, url):
        """Resolves any redirects and returns the final URL."""
        return self.get(url, stream=True).url

    @staticmethod
    def valid_request_args(**req_keywords) -> Dict:
        return {k: v for k, v in req_keywords.items() if k in _VALID_REQUEST_ARGS}

    def prepare_new_request(self, **req_keywords) -> PreparedRequest:
        valid_args = self.valid_request_args(**req_keywords)
        valid_args.setdefault("method", "GET")
        request = Request(**valid_args)

        # prepare request with the session context, which might add params, headers, cookies, etc.
        return self.prepare_request(request)

    def request(self, method, url, *args, **kwargs):
        acceptable_status = kwargs.pop("acceptable_status", [])
        exception = kwargs.pop("exception", PluginError)
        headers = kwargs.pop("headers", {})
        params = kwargs.pop("params", {})
        proxies = kwargs.pop("proxies", self.proxies)
        raise_for_status = kwargs.pop("raise_for_status", True)
        schema = kwargs.pop("schema", None)
        session = kwargs.pop("session", None)
        timeout = kwargs.pop("timeout", self.timeout)
        total_retries = kwargs.pop("retries", 0)
        retry_backoff = kwargs.pop("retry_backoff", 0.3)
        retry_max_backoff = kwargs.pop("retry_max_backoff", 10.0)
        retries = 0

        if session:
            headers.update(session.headers)
            params.update(session.params)

        while True:
            try:
                res = super().request(
                    method,
                    url,
                    *args,
                    headers=headers,
                    params=params,
                    timeout=timeout,
                    proxies=proxies,
                    **kwargs,
                )
                if raise_for_status and res.status_code not in acceptable_status:
                    res.raise_for_status()
                break
            except KeyboardInterrupt:
                raise
            except Exception as rerr:
                if retries >= total_retries:
                    err = exception(f"Unable to open URL: {url} ({rerr})")
                    err.err = rerr
                    raise err
                retries += 1
                # back off retrying, but only to a maximum sleep time
                delay = min(retry_max_backoff,
                            retry_backoff * (2 ** (retries - 1)))
                time.sleep(delay)

        if schema:
            res = schema.validate(res.text, name="response text", exception=PluginError)

        return res


class TLSNoDHAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.load_default_certs()
        ciphers = ":".join(cipher.get("name") for cipher in ctx.get_ciphers())
        ciphers += ":!DH"
        ctx.set_ciphers(ciphers)
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


class TLSSecLevel1Adapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.load_default_certs()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


__all__ = ["HTTPSession", "TLSNoDHAdapter", "TLSSecLevel1Adapter"]
