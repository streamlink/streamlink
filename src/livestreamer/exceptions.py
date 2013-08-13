class PluginError(Exception):
    """Plugin related error."""


class NoStreamsError(Exception):
    def __init__(self, url):
        self.url = url

        Exception.__init__(self, "No streams found on this "
                                 "URL: {0}".format(url))


class NoPluginError(PluginError):
    """No relevant plugin has been loaded.

    This exception is raised by :meth:`Livestreamer.resolve_url`,
    when no relevant plugin can be found.

    Inherits :exc:`PluginError`.

    """


class StreamError(Exception):
    """Stream related error."""


__all__ = ["PluginError", "NoPluginError", "NoStreamsError", "StreamError"]
