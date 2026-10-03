from __future__ import annotations

import io
from contextlib import suppress
from typing import TYPE_CHECKING, Callable

import pytest

from streamlink.stream.stream import Stream


if TYPE_CHECKING:
    from streamlink.options import Options
    from streamlink.session import Streamlink


class PluginTest:
    @pytest.fixture()
    def session(self, session: Streamlink) -> Streamlink:
        session.options.set("no-plugin-cache", True)
        session.options.set("webbrowser-headless", True)
        return session

    def test_remotes(self, session: Streamlink, remote: str):
        url: str
        options: Options | None = None

        method: Callable[[Streamlink], str | tuple[str, Options]] = getattr(self, remote)
        assert callable(method)

        result = method(session)
        if isinstance(result, tuple):
            url, options = result
        else:
            url = result

        session.plugins.load_builtin()
        pluginname, pluginclass, url = session.resolve_url(url)
        assert pluginname
        plugin = pluginclass(session, url, options)

        streams = plugin.streams()
        assert streams
        assert all(isinstance(stream, Stream) for stream in streams.values())
        assert "best" in streams

        stream = streams["best"]
        fd: io.IOBase | None = None
        try:
            fd = stream.open()
            assert isinstance(fd, io.IOBase)
            assert fd.read(8192)
        finally:
            if fd is not None:  # pragma: no branch
                with suppress(OSError):
                    fd.close()
