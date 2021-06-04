import time

import requests.adapters
import urllib3
from requests import Session

from streamlink.exceptions import PluginError
from streamlink.packages.requests_file import FileAdapter
from streamlink.plugin.api import useragents
from streamlink.utils import parse_json, parse_xml


try:
    # We tell urllib3 to disable warnings about unverified HTTPS requests,
    # because in some plugins we have to do unverified requests intentionally.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except AttributeError:
    pass


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
        kwargs.update({"enforce_content_length": True})
        super().__init__(*args, **kwargs)


# override all urllib3.response.HTTPResponse references in requests.adapters.HTTPAdapter.send
urllib3.connectionpool.HTTPConnectionPool.ResponseCls = _HTTPResponse
requests.adapters.HTTPResponse = _HTTPResponse


def _parse_keyvalue_list(val):
    for keyvalue in val.split(";"):
        try:
            key, value = keyvalue.split("=", 1)
            yield key.strip(), value.strip()
        except ValueError:
            continue


class HTTPSession(Session):
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

    def parse_cookies(self, cookies, **kwargs):
        """Parses a semi-colon delimited list of cookies.

        Example: foo=bar;baz=qux
        """
        for name, value in _parse_keyvalue_list(cookies):
            self.cookies.set(name, value, **kwargs)

    def parse_headers(self, headers):
        """Parses a semi-colon delimited list of headers.

        Example: foo=bar;baz=qux
        """
        for name, value in _parse_keyvalue_list(headers):
            self.headers[name] = value

    def parse_query_params(self, cookies, **kwargs):
        """Parses a semi-colon delimited list of query parameters.

        Example: foo=bar;baz=qux
        """
        for name, value in _parse_keyvalue_list(cookies):
            self.params[name] = value

    def resolve_url(self, url):
        """Resolves any redirects and returns the final URL."""
        return self.get(url, stream=True).url

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


__all__ = ["HTTPSession"]
