from typing import Dict

from streamlink.exceptions import StreamError
from streamlink.stream.stream import Stream
from streamlink.stream.wrappers import StreamIOIterWrapper, StreamIOThreadWrapper


class HTTPStream(Stream):
    """
    An HTTP stream using the :mod:`requests` library.
    """

    __shortname__ = "http"

    args: Dict
    """A dict of keyword arguments passed to :meth:`requests.Session.request`, such as method, headers, cookies, etc."""

    def __init__(
        self,
        session_,
        url: str,
        buffered: bool = True,
        **args
    ):
        """
        :param streamlink.Streamlink session_: Streamlink session instance
        :param url: The URL of the HTTP stream
        :param buffered: Wrap stream output in an additional reader-thread
        :param args: Additional keyword arguments passed to :meth:`requests.Session.request`
        """

        super().__init__(session_)
        self.args = dict(url=url, **args)
        self.buffered = buffered

    def __json__(self):
        req = self.session.http.prepare_new_request(**self.args)

        return dict(
            type=self.shortname(),
            method=req.method,
            url=req.url,
            headers=dict(req.headers),
            body=req.body,
        )

    def to_url(self):
        return self.url

    @property
    def url(self) -> str:
        """
        The URL to the stream, prepared by :mod:`requests` with parameters read from :attr:`args`.
        """

        return self.session.http.prepare_new_request(**self.args).url  # type: ignore[return-value]

    def open(self):
        reqargs = self.session.http.valid_request_args(**self.args)
        reqargs.setdefault("method", "GET")
        timeout = self.session.options.get("stream-timeout")
        res = self.session.http.request(
            stream=True,
            exception=StreamError,
            timeout=timeout,
            **reqargs,
        )

        fd = StreamIOIterWrapper(res.iter_content(8192))
        if self.buffered:
            fd = StreamIOThreadWrapper(self.session, fd, timeout=timeout)

        return fd
