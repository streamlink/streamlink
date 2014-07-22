from .session import Livestreamer

def streams(url, **params):
    """Attempts to find a plugin and extract streams from the *url*.

    *params* are passed to :func:`Plugin.streams`.

    Raises :exc:`NoPluginError` if no plugin is found.
    """

    session = Livestreamer()
    return session.streams(url, **params)
