import requests

from .stream import Stream
from .wrappers import StreamIOWrapper
from ..exceptions import StreamError


class HTTPStream(Stream):
    """A HTTP stream using the requests library.

    *Attributes:*

    - :attr:`url`  The URL to the stream, prepared by requests.
    - :attr:`args` A :class:`dict` containing keyword arguments passed
                   to :meth:`requests.request`, such as headers and
                   cookies.

    """

    __shortname__ = "http"

    def __init__(self, session, url, **args):
        Stream.__init__(self, session)

        self.args = dict(url=url, method=args.pop("method", "GET"),
                         **args)

    def __repr__(self):
        return "<HTTPStream({0!r})>".format(self.url)

    def __json__(self):
        req = requests.Request(**self.args).prepare()

        return dict(type=HTTPStream.shortname(),
                    url=req.url, headers=dict(req.headers),
                    body=req.body, method=req.method)

    @property
    def url(self):
        return requests.Request(**self.args).prepare().url

    def open(self):
        try:
            res = requests.request(stream=True, **self.args)
            res.raise_for_status()
        except (requests.exceptions.RequestException, IOError) as err:
            raise StreamError("Unable to open URL: {0} ({1})".format(self.url,
                                                                     err))

        return StreamIOWrapper(res.raw)

