from livestreamer.options import Options

import re

SpecialQualityWeights = {
    "live": 1080,
    "hd": 1080,
    "hq": 576,
    "hqtest": 576,
    "sd": 576,
    "sq": 360,
    "sqtest": 240,
    "iphonehigh": 240,
    "iphonelow": 180,
}

def qualityweight(quality):
    if quality in SpecialQualityWeights:
        return SpecialQualityWeights[quality]

    match = re.match("^(\d+)([k]|[p])$", quality)

    if match:
        if match.group(2) == "k":
            bitrate = int(match.group(1))

            # These calculations are very rough
            if bitrate > 2000:
                return bitrate / 3.4
            elif bitrate > 1000:
                return bitrate / 2.6
            else:
                return bitrate / 1.7

        elif match.group(2) == "p":
            return int(match.group(1))


    return 1

class Plugin(object):
    """
        A plugin can retrieve stream information from the *url* specified.
    """

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
        """
            Retrieves and returns a :class:`dict` containing the streams.

            The key is the name of the stream, most commonly the quality.
            The value is a :class:`Stream` object.

            The stream with key *best* is a reference to the stream most likely
            to be of highest quality.
        """

        streams = self._get_streams()

        best = (0, None)
        for name, stream in streams.items():
            weight = qualityweight(name)

            if weight > best[0]:
                best = (weight, stream)

        if best[1] is not None:
            streams["best"] = best[1]

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
