class StreamlinkError(Exception):
    """
    Any error caused by Streamlink will be caught with this exception.
    """


# TODO: don't use PluginError for failed HTTP requests or validation schema failures
class PluginError(StreamlinkError):
    """
    Plugin related error.
    """


class FatalPluginError(PluginError):
    """
    Plugin related error that cannot be recovered from.

    Plugins should use this ``Exception`` when errors that can
    never be recovered from are encountered. For example, when
    a user's input is required and none can be given.
    """


class NoPluginError(StreamlinkError):
    """
    Error raised by :py:meth:`Streamlink.resolve_url() <streamlink.Streamlink.resolve_url()>`
    and :py:meth:`Streamlink.resolve_url_no_redirect() <streamlink.Streamlink.resolve_url_no_redirect()>`
    when no plugin could be found for the given input URL.
    """


class NoStreamsError(StreamlinkError):
    """
    Plugins should use this ``Exception`` in :py:meth:`Plugin._get_streams() <streamlink.plugin.Plugin._get_streams()>`
    when returning ``None`` or an empty ``dict`` is not possible, e.g. in nested function calls.
    """


class StreamError(StreamlinkError):
    """
    Stream related error.
    """


# https://stackoverflow.com/a/49797717
class _StreamlinkWarningMeta(type):
    def __new__(mcs, name, bases, namespace, **kw):
        name = namespace.get("__name__", name)
        return super().__new__(mcs, name, bases, namespace, **kw)


class StreamlinkWarning(UserWarning, metaclass=_StreamlinkWarningMeta):
    pass


class StreamlinkDeprecationWarning(StreamlinkWarning):
    __name__ = "StreamlinkDeprecation"


__all__ = [
    "StreamlinkError",
    "PluginError",
    "FatalPluginError",
    "NoPluginError",
    "NoStreamsError",
    "StreamError",
    "StreamlinkWarning",
    "StreamlinkDeprecationWarning",
]
