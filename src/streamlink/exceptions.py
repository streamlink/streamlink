class StreamlinkError(Exception):
    """Any error caused by Streamlink will be caught
       with this exception."""


class PluginError(StreamlinkError):
    """Plugin related error."""


class FatalPluginError(PluginError):
    """
    Plugin related error that cannot be recovered from

    Plugin's should use this Exception when errors that can
    never be recovered from are encountered. For example, when
    a user's input is required an none can be given.
    """


class NoStreamsError(StreamlinkError):
    def __init__(self, url):
        self.url = url
        err = "No streams found on this URL: {0}".format(url)
        Exception.__init__(self, err)


class NoPluginError(PluginError):
    """No relevant plugin has been loaded."""


class StreamError(StreamlinkError):
    """Stream related error."""


__all__ = ["StreamlinkError", "PluginError", "NoPluginError",
           "NoStreamsError", "StreamError"]
