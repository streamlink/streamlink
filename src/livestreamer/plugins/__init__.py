from livestreamer.options import Options

class Plugin(object):
    options = Options()

    def __init__(self, url):
        self.url = url
        self.logger = self.session.logger.new_module("plugin." + self.module)

    @classmethod
    def can_handle_url(cls, url):
       raise NotImplementedError

    @classmethod
    def set_option(cls, key, value):
        cls.options.set(key, value)

    @classmethod
    def get_option(cls, key):
        return cls.options.get(key)

    def get_streams(self):
        ranking = ["iphonelow", "iphonehigh", "240p", "320k", "360p", "850k",
                   "480p", "1400k", "720p", "2400k", "hd", "1080p", "live"]
        streams = self._get_streams()
        for rank in reversed(ranking):
            if rank in streams:
                streams["best"] = streams[rank]
                break

        return streams

    def _get_streams(self):
        raise NotImplementedError

class PluginError(Exception):
    pass

class NoStreamsError(PluginError):
    def __init__(self, url):
        PluginError.__init__(self, ("No streams found on this URL: {0}").format(url))

class NoPluginError(PluginError):
    pass

__all__ = ["Plugin", "PluginError", "NoStreamsError", "NoPluginError"]
