class LivestreamerError(Exception):
    """Any error caused by Livestreamer will be caught
       with this exception."""


class PluginError(LivestreamerError):
    """Plugin related error."""


class NoStreamsError(LivestreamerError):
    def __init__(self, url):
        self.url = url
        err = "No streams found on this URL: {0}".format(url)
        Exception.__init__(self, err)


class NoPluginError(PluginError):
    """No relevant plugin has been loaded."""


class StreamError(LivestreamerError):
    """Stream related error."""


__all__ = ["LivestreamerError", "PluginError", "NoPluginError",
           "NoStreamsError", "StreamError"]
