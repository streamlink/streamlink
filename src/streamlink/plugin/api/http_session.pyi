from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from typing import Any, Union

from _typeshed import SupportsItems, SupportsRead
from requests import PreparedRequest, Response, Session
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase
from requests.cookies import RequestsCookieJar
from typing_extensions import TypeAlias

from streamlink.plugin.api.validate import Schema
from streamlink.session import Streamlink


# START: borrowed from typeshed / types-requests
# https://github.com/python/typeshed/blob/b3db49abbd563a8543783fcd2b4d6765b32812b0/stubs/requests/requests/sessions.pyi

_Data: TypeAlias = (
    # used in requests.models.PreparedRequest.prepare_body
    #
    # case: is_stream
    # see requests.adapters.HTTPAdapter.send
    # will be sent directly to http.HTTPConnection.send(...) (through urllib3)
    Iterable[bytes]
    # case: not is_stream
    # will be modified before being sent to urllib3.HTTPConnectionPool.urlopen(body=...)
    # see requests.models.RequestEncodingMixin._encode_params
    # see requests.models.RequestEncodingMixin._encode_files
    # note that keys&values are converted from Any to str by urllib.parse.urlencode
    | str
    | bytes
    | SupportsRead[str | bytes]
    | list[tuple[Any, Any]]
    | tuple[tuple[Any, Any], ...]
    | Mapping[Any, Any]
)
_Auth: TypeAlias = Union[tuple[str, str], AuthBase, Callable[[PreparedRequest], PreparedRequest]]
_Cert: TypeAlias = Union[str, tuple[str, str]]
_FileName: TypeAlias = str | None
_FileContent: TypeAlias = SupportsRead[str | bytes] | str | bytes
_FileContentType: TypeAlias = str
_FileCustomHeaders: TypeAlias = Mapping[str, str]
_FileSpecTuple2: TypeAlias = tuple[_FileName, _FileContent]
_FileSpecTuple3: TypeAlias = tuple[_FileName, _FileContent, _FileContentType]
_FileSpecTuple4: TypeAlias = tuple[_FileName, _FileContent, _FileContentType, _FileCustomHeaders]
_FileSpec: TypeAlias = _FileContent | _FileSpecTuple2 | _FileSpecTuple3 | _FileSpecTuple4
_Files: TypeAlias = Mapping[str, _FileSpec] | Iterable[tuple[str, _FileSpec]]
_Hook: TypeAlias = Callable[[Response], Any]
_HooksInput: TypeAlias = Mapping[str, Iterable[_Hook] | _Hook]

_ParamsMappingKeyType: TypeAlias = str | bytes | float
_ParamsMappingValueType: TypeAlias = str | bytes | float | Iterable[str | bytes | float] | None
_Params: TypeAlias = Union[
    SupportsItems[_ParamsMappingKeyType, _ParamsMappingValueType],
    tuple[_ParamsMappingKeyType, _ParamsMappingValueType],
    Iterable[tuple[_ParamsMappingKeyType, _ParamsMappingValueType]],
    str | bytes,
]
_TextMapping: TypeAlias = MutableMapping[str, str]
_HeadersUpdateMapping: TypeAlias = Mapping[str, str | bytes | None]
_Timeout: TypeAlias = Union[float, tuple[float, float], tuple[float, None]]
_Verify: TypeAlias = bool | str

# END: borrowed from typeshed / types-requests


_AcceptableStatus: TypeAlias = Sequence[int]
_Exception: TypeAlias = type[Exception]


# ----


class TLSSecLevel1Adapter(HTTPAdapter):
    ...


class HTTPSession(Session):
    params: dict
    timeout: float

    @classmethod
    def determine_json_encoding(cls, sample: bytes) -> str:
        ...

    @classmethod
    def json(
        cls,
        res: Response,
        name: str | None = ...,
        exception: _Exception | None = ...,
        schema: Schema | None = ...,
        *args,
        **kwargs,
    ) -> Any:
        ...

    @classmethod
    def xml(
        cls,
        res: Response,
        ignore_ns: bool | None = ...,
        invalid_char_entities: bool | None = ...,
        name: str | None = ...,
        exception: _Exception | None = ...,
        schema: Schema | None = ...,
        *args,
        **kwargs,
    ) -> Any:
        ...

    def resolve_url(self, url: str) -> str:
        ...

    @staticmethod
    def valid_request_args(**req_keywords) -> dict[str, Any]:
        ...

    def prepare_new_request(self, **req_keywords) -> PreparedRequest:
        ...

    def request(
        self,
        method: str | bytes,
        url: str | bytes,
        params: _Params | None = ...,
        data: _Data | None = ...,
        headers: _HeadersUpdateMapping | None = ...,
        cookies: RequestsCookieJar | _TextMapping | None = ...,
        files: _Files | None = ...,
        auth: _Auth | None = ...,
        timeout: _Timeout | None = ...,
        allow_redirects: bool = ...,
        proxies: _TextMapping | None = ...,
        hooks: _HooksInput | None = ...,
        stream: bool | None = ...,
        verify: _Verify | None = ...,
        cert: _Cert | None = ...,
        json: Any | None = ...,

        acceptable_status: _AcceptableStatus | None = ...,
        exception: _Exception | None = ...,
        raise_for_status: bool | None = ...,
        session: Streamlink | None = ...,
        schema: Schema | None = ...,
        retries: float | None = ...,
        retry_backoff: float | None = ...,
        retry_max_backoff: float | None = ...,
    ) -> Any:
        ...

    def get(
        self,
        url: str | bytes,
        *,
        params: _Params | None = ...,
        data: _Data | None = ...,
        headers: _HeadersUpdateMapping | None = ...,
        cookies: RequestsCookieJar | _TextMapping | None = ...,
        files: _Files | None = ...,
        auth: _Auth | None = ...,
        timeout: _Timeout | None = ...,
        allow_redirects: bool = ...,
        proxies: _TextMapping | None = ...,
        hooks: _HooksInput | None = ...,
        stream: bool | None = ...,
        verify: _Verify | None = ...,
        cert: _Cert | None = ...,
        json: Any | None = ...,

        acceptable_status: _AcceptableStatus | None = ...,
        exception: _Exception | None = ...,
        raise_for_status: bool | None = ...,
        session: Streamlink | None = ...,
        schema: Schema | None = ...,
        retries: float | None = ...,
        retry_backoff: float | None = ...,
        retry_max_backoff: float | None = ...,
    ) -> Any:
        ...

    def options(
        self,
        url: str | bytes,
        *,
        params: _Params | None = ...,
        data: _Data | None = ...,
        headers: _HeadersUpdateMapping | None = ...,
        cookies: RequestsCookieJar | _TextMapping | None = ...,
        files: _Files | None = ...,
        auth: _Auth | None = ...,
        timeout: _Timeout | None = ...,
        allow_redirects: bool = ...,
        proxies: _TextMapping | None = ...,
        hooks: _HooksInput | None = ...,
        stream: bool | None = ...,
        verify: _Verify | None = ...,
        cert: _Cert | None = ...,
        json: Any | None = ...,

        acceptable_status: _AcceptableStatus | None = ...,
        exception: _Exception | None = ...,
        raise_for_status: bool | None = ...,
        session: Streamlink | None = ...,
        schema: Schema | None = ...,
        retries: float | None = ...,
        retry_backoff: float | None = ...,
        retry_max_backoff: float | None = ...,
    ) -> Any:
        ...

    def head(
        self,
        url: str | bytes,
        *,
        params: _Params | None = ...,
        data: _Data | None = ...,
        headers: _HeadersUpdateMapping | None = ...,
        cookies: RequestsCookieJar | _TextMapping | None = ...,
        files: _Files | None = ...,
        auth: _Auth | None = ...,
        timeout: _Timeout | None = ...,
        allow_redirects: bool = ...,
        proxies: _TextMapping | None = ...,
        hooks: _HooksInput | None = ...,
        stream: bool | None = ...,
        verify: _Verify | None = ...,
        cert: _Cert | None = ...,
        json: Any | None = ...,

        acceptable_status: _AcceptableStatus | None = ...,
        exception: _Exception | None = ...,
        raise_for_status: bool | None = ...,
        session: Streamlink | None = ...,
        schema: Schema | None = ...,
        retries: float | None = ...,
        retry_backoff: float | None = ...,
        retry_max_backoff: float | None = ...,
    ) -> Any:
        ...

    def post(
        self,
        url: str | bytes,
        data: _Data | None = ...,
        json: Any | None = ...,
        *,
        params: _Params | None = ...,
        headers: _HeadersUpdateMapping | None = ...,
        cookies: RequestsCookieJar | _TextMapping | None = ...,
        files: _Files | None = ...,
        auth: _Auth | None = ...,
        timeout: _Timeout | None = ...,
        allow_redirects: bool = ...,
        proxies: _TextMapping | None = ...,
        hooks: _HooksInput | None = ...,
        stream: bool | None = ...,
        verify: _Verify | None = ...,
        cert: _Cert | None = ...,

        acceptable_status: _AcceptableStatus | None = ...,
        exception: _Exception | None = ...,
        raise_for_status: bool | None = ...,
        session: Streamlink | None = ...,
        schema: Schema | None = ...,
        retries: float | None = ...,
        retry_backoff: float | None = ...,
        retry_max_backoff: float | None = ...,
    ) -> Any:
        ...

    def put(
        self,
        url: str | bytes,
        data: _Data | None = ...,
        *,
        params: _Params | None = ...,
        headers: _HeadersUpdateMapping | None = ...,
        cookies: RequestsCookieJar | _TextMapping | None = ...,
        files: _Files | None = ...,
        auth: _Auth | None = ...,
        timeout: _Timeout | None = ...,
        allow_redirects: bool = ...,
        proxies: _TextMapping | None = ...,
        hooks: _HooksInput | None = ...,
        stream: bool | None = ...,
        verify: _Verify | None = ...,
        cert: _Cert | None = ...,
        json: Any | None = ...,

        acceptable_status: _AcceptableStatus | None = ...,
        exception: _Exception | None = ...,
        raise_for_status: bool | None = ...,
        session: Streamlink | None = ...,
        schema: Schema | None = ...,
        retries: float | None = ...,
        retry_backoff: float | None = ...,
        retry_max_backoff: float | None = ...,
    ) -> Any:
        ...

    def patch(
        self,
        url: str | bytes,
        data: _Data | None = ...,
        *,
        params: _Params | None = ...,
        headers: _HeadersUpdateMapping | None = ...,
        cookies: RequestsCookieJar | _TextMapping | None = ...,
        files: _Files | None = ...,
        auth: _Auth | None = ...,
        timeout: _Timeout | None = ...,
        allow_redirects: bool = ...,
        proxies: _TextMapping | None = ...,
        hooks: _HooksInput | None = ...,
        stream: bool | None = ...,
        verify: _Verify | None = ...,
        cert: _Cert | None = ...,
        json: Any | None = ...,

        acceptable_status: _AcceptableStatus | None = ...,
        exception: _Exception | None = ...,
        raise_for_status: bool | None = ...,
        session: Streamlink | None = ...,
        schema: Schema | None = ...,
        retries: float | None = ...,
        retry_backoff: float | None = ...,
        retry_max_backoff: float | None = ...,
    ) -> Any:
        ...

    def delete(
        self,
        url: str | bytes,
        *,
        params: _Params | None = ...,
        data: _Data | None = ...,
        headers: _HeadersUpdateMapping | None = ...,
        cookies: RequestsCookieJar | _TextMapping | None = ...,
        files: _Files | None = ...,
        auth: _Auth | None = ...,
        timeout: _Timeout | None = ...,
        allow_redirects: bool = ...,
        proxies: _TextMapping | None = ...,
        hooks: _HooksInput | None = ...,
        stream: bool | None = ...,
        verify: _Verify | None = ...,
        cert: _Cert | None = ...,
        json: Any | None = ...,

        acceptable_status: _AcceptableStatus | None = ...,
        exception: _Exception | None = ...,
        raise_for_status: bool | None = ...,
        session: Streamlink | None = ...,
        schema: Schema | None = ...,
        retries: float | None = ...,
        retry_backoff: float | None = ...,
        retry_max_backoff: float | None = ...,
    ) -> Any:
        ...
