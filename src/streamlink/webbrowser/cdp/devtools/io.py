# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all modules.
#
# CDP version: v0.0.1156692
# CDP domain: IO

from __future__ import annotations

import enum  # noqa
import typing
from dataclasses import dataclass  # noqa

import streamlink.webbrowser.cdp.devtools.runtime as runtime
from streamlink.webbrowser.cdp.devtools.util import T_JSON_DICT, event_class  # noqa


class StreamHandle(str):
    """
    This is either obtained from another method or specified as ``blob:&lt;uuid&gt;`` where
    ``&lt;uuid&gt`` is an UUID of a Blob.
    """
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> StreamHandle:
        return cls(json)

    def __repr__(self):
        return f"StreamHandle({super().__repr__()})"


def close(
    handle: StreamHandle,
) -> typing.Generator[T_JSON_DICT, T_JSON_DICT, None]:
    """
    Close the stream, discard any temporary backing storage.

    :param handle: Handle of the stream to close.
    """
    params: T_JSON_DICT = {}
    params["handle"] = handle.to_json()
    cmd_dict: T_JSON_DICT = {
        "method": "IO.close",
        "params": params,
    }
    yield cmd_dict


def read(
    handle: StreamHandle,
    offset: typing.Optional[int] = None,
    size: typing.Optional[int] = None,
) -> typing.Generator[T_JSON_DICT, T_JSON_DICT, typing.Tuple[typing.Optional[bool], str, bool]]:
    """
    Read a chunk of the stream

    :param handle: Handle of the stream to read.
    :param offset: *(Optional)* Seek to the specified offset before reading (if not specified, proceed with offset following the last read). Some types of streams may only support sequential reads.
    :param size: *(Optional)* Maximum number of bytes to read (left upon the agent discretion if not specified).
    :returns: A tuple with the following items:

        0. **base64Encoded** - *(Optional)* Set if the data is base64-encoded
        1. **data** - Data that were read.
        2. **eof** - Set if the end-of-file condition occurred while reading.
    """
    params: T_JSON_DICT = {}
    params["handle"] = handle.to_json()
    if offset is not None:
        params["offset"] = offset
    if size is not None:
        params["size"] = size
    cmd_dict: T_JSON_DICT = {
        "method": "IO.read",
        "params": params,
    }
    json = yield cmd_dict
    return (
        bool(json["base64Encoded"]) if "base64Encoded" in json else None,
        str(json["data"]),
        bool(json["eof"]),
    )


def resolve_blob(
    object_id: runtime.RemoteObjectId,
) -> typing.Generator[T_JSON_DICT, T_JSON_DICT, str]:
    """
    Return UUID of Blob object specified by a remote object id.

    :param object_id: Object id of a Blob object wrapper.
    :returns: UUID of the specified Blob.
    """
    params: T_JSON_DICT = {}
    params["objectId"] = object_id.to_json()
    cmd_dict: T_JSON_DICT = {
        "method": "IO.resolveBlob",
        "params": params,
    }
    json = yield cmd_dict
    return str(json["uuid"])
