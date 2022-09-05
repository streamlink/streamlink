import ssl
import time
from typing import Any, Callable, Dict, List, Pattern, Tuple

import requests.adapters
# noinspection PyPackageRequirements
import urllib3
from requests import PreparedRequest, Request, Session

from streamlink.exceptions import PluginError
from streamlink.packages.requests_file import FileAdapter
from streamlink.plugin.api import useragents
from streamlink.utils.parse import parse_json, parse_xml


urllib3_version = tuple(map(int, urllib3.__version__.split(".")[:3]))


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


# Never convert percent-encoded characters to uppercase in urllib3>=1.25.4.
# This is required for sites which compare request URLs byte for byte and return different responses depending on that.
# Older versions of urllib3 are not compatible with this override and will always convert to uppercase characters.
#
# https://datatracker.ietf.org/doc/html/rfc3986#section-2.1
# > The uppercase hexadecimal digits 'A' through 'F' are equivalent to
# > the lowercase digits 'a' through 'f', respectively.  If two URIs
# > differ only in the case of hexadecimal digits used in percent-encoded
# > octets, they are equivalent.  For consistency, URI producers and
# > normalizers should use uppercase hexadecimal digits for all percent-
# > encodings.
if urllib3_version >= (1, 25, 4):
    class Urllib3UtilUrlPercentReOverride:
        _re_percent_encoding: Pattern = urllib3.util.url.PERCENT_RE  # type: ignore[attr-defined]

        @classmethod
        def _num_percent_encodings(cls, string) -> int:
            return len(cls._re_percent_encoding.findall(string))

        # urllib3>=1.25.8
        # https://github.com/urllib3/urllib3/blame/1.25.8/src/urllib3/util/url.py#L219-L227
        @classmethod
        def subn(cls, repl: Callable, string: str) -> Tuple[str, int]:
            return string, cls._num_percent_encodings(string)

        # urllib3>=1.25.4,<1.25.8
        # https://github.com/urllib3/urllib3/blame/1.25.4/src/urllib3/util/url.py#L218-L228
        @classmethod
        def findall(cls, string: str) -> List[Any]:
            class _List(list):
                def __len__(self) -> int:
                    return cls._num_percent_encodings(string)

            return _List()

    urllib3.util.url.PERCENT_RE = Urllib3UtilUrlPercentReOverride  # type: ignore[attr-defined]


# requests.Request.__init__ keywords, except for "hooks"
_VALID_REQUEST_ARGS = "method", "url", "headers", "files", "data", "params", "auth", "cookies", "json"


class HTTPSession(Session):
    params: Dict

    def __init__(self):
        super().__init__()

        self.headers['User-Agent'] = useragents.FIREFOX
        self.timeout = 20.0

        self.mount('file://', FileAdapter())

    @classmethod
    def determine_json_encoding(cls, sample):
        """
        Determine which Unicode encoding the JSON text sample is encoded with

        RFC4627 (http://www.ietf.org/rfc/rfc4627.txt) suggests that the encoding of JSON text can be determined
        by checking the pattern of NULL bytes in first 4 octets of the text.
        :param sample: a sample of at least 4 bytes of the JSON text
        :return: the most likely encoding of the JSON text
        """
        nulls_at = [i for i, j in enumerate(bytearray(sample[:4])) if j == 0]
        if nulls_at == [0, 1, 2]:
            return "UTF-32BE"
        elif nulls_at == [0, 2]:
            return "UTF-16BE"
        elif nulls_at == [1, 2, 3]:
            return "UTF-32LE"
        elif nulls_at == [1, 3]:
            return "UTF-16LE"
        else:
            return "UTF-8"

    @classmethod
    def json(cls, res, *args, **kwargs):
        """Parses JSON from a response."""
        # if an encoding is already set then use the provided encoding
        if res.encoding is None:
            res.encoding = cls.determine_json_encoding(res.content[:4])
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
                    headers=headers,
                    params=params,
                    timeout=timeout,
                    proxies=proxies,
                    *args,
                    **kwargs
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


class TLSSecLevel1Adapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


__all__ = ["HTTPSession", "TLSSecLevel1Adapter"]
