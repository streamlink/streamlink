from streamlink.session import Streamlink


def streams(url: str, **params):
    """
    Initializes an empty Streamlink session, attempts to find a plugin and extracts streams from the URL if a plugin was found.

    :param url: a URL to match against loaded plugins
    :param params: Additional keyword arguments passed to :meth:`streamlink.Streamlink.streams`
    :raises NoPluginError: on plugin resolve failure
    :returns: A :class:`dict` of stream names and :class:`streamlink.stream.Stream` instances
    """

    session = Streamlink()

    return session.streams(url, **params)
