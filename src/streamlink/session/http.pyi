import socket
import ssl
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypedDict

# noinspection PyProtectedMember
import requests._types as _requeststypes  # noqa: PLC2701
from requests import PreparedRequest, Response, Session
from requests.adapters import HTTPAdapter
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
    schema: Schema
    session: HTTPSession

class _RequestKwargs(_requeststypes.RequestKwargs, _StreamlinkKwargs):
    pass

class _GetKwargs(_requeststypes.GetKwargs, _StreamlinkKwargs):
    pass

class _PostKwargs(_requeststypes.PostKwargs, _StreamlinkKwargs):
    pass

class _DataKwargs(_requeststypes.DataKwargs, _StreamlinkKwargs):
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
    def request(
        self,
        method: str,
        url: _requeststypes.UriType,
        *args,
        **kwargs: Unpack[_RequestKwargs],
    ) -> Any: ...
    def get(
        self,
        url: _requeststypes.UriType,
        params: _requeststypes.ParamsType | None = None,
        **kwargs: Unpack[_GetKwargs],
    ) -> Any: ...
    def options(
        self,
        url: _requeststypes.UriType,
        **kwargs: Unpack[_RequestKwargs],
    ) -> Any: ...
    def head(
        self,
        url: _requeststypes.UriType,
        **kwargs: Unpack[_RequestKwargs],
    ) -> Any: ...
    def post(
        self,
        url: _requeststypes.UriType,
        data: _requeststypes.DataType = None,
        json: _requeststypes.JsonType = None,
        **kwargs: Unpack[_PostKwargs],
    ) -> Any: ...
    def put(
        self,
        url: _requeststypes.UriType,
        data: _requeststypes.DataType = None,
        **kwargs: Unpack[_DataKwargs],
    ) -> Any: ...
    def patch(
        self,
        url: _requeststypes.UriType,
        data: _requeststypes.DataType = None,
        **kwargs: Unpack[_DataKwargs],
    ) -> Any: ...
    def delete(
        self,
        url: _requeststypes.UriType,
        **kwargs: Unpack[_RequestKwargs],
    ) -> Any: ...
