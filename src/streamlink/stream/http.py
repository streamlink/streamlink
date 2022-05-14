from streamlink.exceptions import StreamError
from streamlink.stream.stream import Stream
from streamlink.stream.wrappers import StreamIOIterWrapper, StreamIOThreadWrapper


class HTTPStream(Stream):
    """A HTTP stream using the requests library.

    *Attributes:*

    - :attr:`url`  The URL to the stream, prepared by requests.
    - :attr:`args` A :class:`dict` containing keyword arguments passed
      to :meth:`requests.request`, such as headers and cookies.

    """

    __shortname__ = "http"

    def __init__(self, session_, url, buffered=True, **args):
        Stream.__init__(self, session_)

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
    def url(self):
        """
        The URL to the stream, prepared by :mod:`requests` with parameters read from :attr:`args`.
        """

        return self.session.http.prepare_new_request(**self.args).url

    def open(self):
        reqargs = self.session.http.valid_request_args(**self.args)
        reqargs.setdefault("method", "GET")
        timeout = self.session.options.get("stream-timeout")
        res = self.session.http.request(
            stream=True,
            exception=StreamError,
            timeout=timeout,
            **reqargs
        )

        fd = StreamIOIterWrapper(res.iter_content(8192))
        if self.buffered:
            fd = StreamIOThreadWrapper(self.session, fd, timeout=timeout)

        return fd
