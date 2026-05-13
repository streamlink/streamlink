import socket
import ssl
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict, overload

# noinspection PyProtectedMember
import requests._types as _requeststypes  # noqa: PLC2701
from requests import PreparedRequest, Response, Session
from requests.adapters import HTTPAdapter
from requests.cookies import CookieJar, RequestsCookieJar
from typing_extensions import Unpack

from streamlink.plugin.api.validate import Schema

class _StreamlinkKwargs(TypedDict, total=False):
    acceptable_status: Sequence[int] | None
    encoding: str | None
    exception: type[Exception]
    raise_for_status: bool
    retries: float
    retry_backoff: float
    retry_max_backoff: float
    session: HTTPSession

class _SchemaKwargs(TypedDict):
    schema: Schema

class _RequestKwargs(_requeststypes.RequestKwargs, _StreamlinkKwargs):
    pass

class _RequestKwargsWithSchema(_requeststypes.RequestKwargs, _StreamlinkKwargs, _SchemaKwargs):
    pass

class _GetKwargs(_requeststypes.GetKwargs, _StreamlinkKwargs):
    pass

class _GetKwargsWithSchema(_requeststypes.GetKwargs, _StreamlinkKwargs, _SchemaKwargs):
    pass

class _PostKwargs(_requeststypes.PostKwargs, _StreamlinkKwargs):
    pass

class _PostKwargsWithSchema(_requeststypes.PostKwargs, _StreamlinkKwargs, _SchemaKwargs):
    pass

class _DataKwargs(_requeststypes.DataKwargs, _StreamlinkKwargs):
    pass

class _DataKwargsWithSchema(_requeststypes.DataKwargs, _StreamlinkKwargs, _SchemaKwargs):
    pass

# ----

def urllib3_set_socket_options(sock: socket.socket, options: list[tuple[int, int, int | bytes]] | None) -> None: ...

class SSLContextAdapter(HTTPAdapter):
    def get_ssl_context(self) -> ssl.SSLContext: ...

class TLSNoDHAdapter(SSLContextAdapter): ...
class TLSSecLevel1Adapter(SSLContextAdapter): ...

class HTTPSession(Session):
    params: dict
    timeout: float

    @classmethod
    def determine_json_encoding(cls, sample: bytes) -> str: ...
    @classmethod
    def json(
        cls,
        res: Response,
        name: str | None = ...,
        exception: type[Exception] | None = ...,
        schema: Schema | None = ...,
        *args,
        **kwargs,
    ) -> Any: ...
    @classmethod
    def xml(
        cls,
        res: Response,
        ignore_ns: bool | None = ...,
        invalid_char_entities: bool | None = ...,
        name: str | None = ...,
        exception: type[Exception] | None = ...,
        schema: Schema | None = ...,
        *args,
        **kwargs,
    ) -> Any: ...
    def set_interface(self, interface: str | None) -> None: ...
    def set_address_family(self, family: socket.AddressFamily | None = None) -> None: ...
    def disable_dh(self, disable: bool = True) -> None: ...
    def set_cookies_from_file(self, path: Path | str) -> None: ...
    def resolve_url(self, url: str) -> str: ...
    @staticmethod
    def valid_request_args(**req_keywords) -> dict[str, Any]: ...
    def prepare_new_request(self, **req_keywords) -> PreparedRequest: ...
    @overload
    def request(
        self,
        method: str,
        url: _requeststypes.UriType,
        params: _requeststypes.ParamsType = None,
        data: _requeststypes.DataType = None,
        headers: Mapping[str, str | bytes] | None = None,
        cookies: RequestsCookieJar | CookieJar | dict[str, str] | None = None,
        files: _requeststypes.FilesType = None,
        auth: _requeststypes.AuthType = None,
        timeout: _requeststypes.TimeoutType = None,
        allow_redirects: bool = True,
        proxies: dict[str, str] | None = None,
        hooks: _requeststypes.HooksInputType | None = None,
        stream: bool | None = None,
        verify: _requeststypes.VerifyType | None = None,
        cert: _requeststypes.CertType = None,
        json: _requeststypes.JsonType = None,
        # streamlink options
        acceptable_status: Sequence[int] | None = None,
        encoding: str | None = None,
        exception: type[Exception] | None = None,
        raise_for_status: bool = True,
        retries: int = 0,
        retry_backoff: float = 0.3,
        retry_max_backoff: float = 10.0,
        schema: Schema | None = None,
        session: HTTPSession | None = None,
    ) -> Any: ...
    @overload
    def request(
        self,
        url: _requeststypes.UriType,
        params: _requeststypes.ParamsType = None,
        data: _requeststypes.DataType = None,
        headers: Mapping[str, str | bytes] | None = None,
        cookies: RequestsCookieJar | CookieJar | dict[str, str] | None = None,
        files: _requeststypes.FilesType = None,
        auth: _requeststypes.AuthType = None,
        timeout: _requeststypes.TimeoutType = None,
        allow_redirects: bool = True,
        proxies: dict[str, str] | None = None,
        hooks: _requeststypes.HooksInputType | None = None,
        stream: bool | None = None,
        verify: _requeststypes.VerifyType | None = None,
        cert: _requeststypes.CertType = None,
        json: _requeststypes.JsonType = None,
        # streamlink options
        acceptable_status: Sequence[int] | None = None,
        encoding: str | None = None,
        exception: type[Exception] | None = None,
        raise_for_status: bool = True,
        retries: int = 0,
        retry_backoff: float = 0.3,
        retry_max_backoff: float = 10.0,
        session: HTTPSession | None = None,
    ) -> Response: ...
    @overload
    def get(
        self,
        url: _requeststypes.UriType,
        params: _requeststypes.ParamsType | None = None,
        **kwargs: Unpack[_GetKwargsWithSchema],
    ) -> Any: ...
    @overload
    def get(
        self,
        url: _requeststypes.UriType,
        params: _requeststypes.ParamsType | None = None,
        **kwargs: Unpack[_GetKwargs],
    ) -> Response: ...
    @overload
    def options(
        self,
        url: _requeststypes.UriType,
        **kwargs: Unpack[_RequestKwargsWithSchema],
    ) -> Any: ...
    @overload
    def options(
        self,
        url: _requeststypes.UriType,
        **kwargs: Unpack[_RequestKwargs],
    ) -> Response: ...
    @overload
    def head(
        self,
        url: _requeststypes.UriType,
        **kwargs: Unpack[_RequestKwargsWithSchema],
    ) -> Any: ...
    @overload
    def head(
        self,
        url: _requeststypes.UriType,
        **kwargs: Unpack[_RequestKwargs],
    ) -> Response: ...
    @overload
    def post(
        self,
        url: _requeststypes.UriType,
        data: _requeststypes.DataType = None,
        json: _requeststypes.JsonType = None,
        **kwargs: Unpack[_PostKwargsWithSchema],
    ) -> Any: ...
    @overload
    def post(
        self,
        url: _requeststypes.UriType,
        data: _requeststypes.DataType = None,
        json: _requeststypes.JsonType = None,
        **kwargs: Unpack[_PostKwargs],
    ) -> Response: ...
    @overload
    def put(
        self,
        url: _requeststypes.UriType,
        data: _requeststypes.DataType = None,
        **kwargs: Unpack[_DataKwargsWithSchema],
    ) -> Any: ...
    @overload
    def put(
        self,
        url: _requeststypes.UriType,
        data: _requeststypes.DataType = None,
        **kwargs: Unpack[_DataKwargs],
    ) -> Response: ...
    @overload
    def patch(
        self,
        url: _requeststypes.UriType,
        data: _requeststypes.DataType = None,
        **kwargs: Unpack[_DataKwargsWithSchema],
    ) -> Any: ...
    @overload
    def patch(
        self,
        url: _requeststypes.UriType,
        data: _requeststypes.DataType = None,
        **kwargs: Unpack[_DataKwargs],
    ) -> Response: ...
    @overload
    def delete(
        self,
        url: _requeststypes.UriType,
        **kwargs: Unpack[_RequestKwargsWithSchema],
    ) -> Any: ...
    @overload
    def delete(
        self,
        url: _requeststypes.UriType,
        **kwargs: Unpack[_RequestKwargs],
    ) -> Response: ...
